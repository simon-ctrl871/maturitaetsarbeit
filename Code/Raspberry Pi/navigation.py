#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# >>> ZIEL & MODUS (nur hier ändern) <<<
USE_GPS = True                        # True = GPS verwenden, False = feste Koordinaten
START = "47.228984,8.675313"              # Startkoordinaten im Format "lat,lon" (nur bei USE_GPS = False)
DST   = "47.240252,8.639224"          # Zielkoordinaten im Format "lat,lon"
EXCLUDE_TOLLS = True                  # Maut vermeiden

import sys
DEBUG = "--debug" in sys.argv

import json, subprocess, time, threading, os, re
import RPi.GPIO as GPIO
import serial

# --- Koordinaten verarbeiten ---
def _parse_latlon(s, label):
    try:
        lat_str, lon_str = [x.strip() for x in s.split(",")]
        return round(float(lat_str), 4), round(float(lon_str), 4)
    except Exception:
        print(f"Fehler beim Parsen der {label}-Koordinaten. Bitte Format 'lat,lon' verwenden.")
        sys.exit(1)

DST_LAT, DST_LON = _parse_latlon(DST, "DST")
START_LAT, START_LON = _parse_latlon(START, "START")

# Hardware/Timing
BTN_SHUTDOWN = 18           
SERIAL_DEV = "/dev/serial/by-id/usb-Arduino__www.arduino.cc__0043_75834303538351904181-if00"

BAUD = 115200
INTERVAL = 3
VALHALLA_URL = "http://localhost:8002/route"

_running = False
_stop = False

ICON_STRAIGHT   = 0
ICON_TURN_LEFT  = 1
ICON_KEEP_LEFT  = 2
ICON_TURN_RIGHT = 3
ICON_KEEP_RIGHT = 4
ICON_ROUNDABOUT = 5
ICON_ALL_BLACK  = 6

# ---------------- Umlaute ersetzen ----------------
def normalize_text(text):
    replacements = {
        "ä": "ae", "ö": "oe", "ü": "ue",
        "Ä": "Ae", "Ö": "Oe", "Ü": "Ue",
        "ß": "ss"
    }
    for src, target in replacements.items():
        text = text.replace(src, target)
    return text

def bearing_to_cardinal(bearing):
    directions = ["Norden", "Nordosten", "Osten", "Südosten",
                  "Süden", "Südwesten", "Westen", "Nordwesten"]
    ix = round(bearing / 45) % 8
    return directions[ix]

def _get_gps(timeout_s=6, verbose=False):
    if not USE_GPS:
        return START_LAT, START_LON

    p = subprocess.Popen(["gpspipe", "-w", "-n", "60"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    start = time.time()
    try:
        for raw in p.stdout:
            if time.time() - start > timeout_s:
                break
            try:
                o = json.loads(raw.decode("utf-8", "ignore"))
                if o.get("class") == "TPV":
                    if verbose and o.get("mode", 0) < 2:
                        print(f"[{time.strftime('%H:%M:%S')}] 📡 Noch kein GPS-Fix...")
                    if o.get("mode") in (2, 3):
                        lat, lon = o.get("lat"), o.get("lon")
                        if lat and lon:
                            if verbose:
                                print(f"[{time.strftime('%H:%M:%S')}] GPS-Fix gefunden: lat={lat}, lon={lon}")
                            return float(lat), float(lon)
            except Exception:
                continue
    finally:
        try:
            p.terminate()
        except Exception:
            pass
    return None

def _open_serial_blocking(dev, baud):
    while True:
        try:
            ser = serial.Serial(dev, baud, timeout=2)
            try:
                ser.setDTR(False)  # Auto-Reset vermeiden
            except Exception:
                pass
            time.sleep(2)          # Reset abwarten
            return ser
        except Exception:
            time.sleep(1)

def _get_valhalla_response(start_lat, start_lon):
    payload = {
        "locations": [{"lat": start_lat, "lon": start_lon}, {"lat": DST_LAT, "lon": DST_LON}],
        "costing": "auto",
        "directions_options": {"language": "de-DE", "units": "kilometers"}
    }
    if EXCLUDE_TOLLS:
        payload["costing_options"] = {"auto": {"exclude_tolls": True}}

    try:
        res = subprocess.run(
            ["curl", "-s", "-H", "Content-Type: application/json", "-X", "POST",
             VALHALLA_URL, "-d", json.dumps(payload)],
            capture_output=True, text=True, timeout=10
        )
        return json.loads(res.stdout)
    except Exception:
        return None

# === LOGIK: Nur neuer Straßenname in "b", "t" für Himmelsrichtung ===
def _extract_new_streetname_from_text(succinct):
    if not succinct:
        return ""
    m = re.search(r"\bauf(?: der| die| den)? ([^.,;]+)", succinct)
    if m:
        return m.group(1).strip()
    m = re.search(r"\bin(?: die| den| der)? ([^.,;]+)", succinct)
    if m:
        return m.group(1).strip()
    return ""

def _package_instruction(data):
    try:
        maneuvers = data["trip"]["legs"][0]["maneuvers"]
    except Exception:
        return ICON_ALL_BLACK, "", ""

    if not maneuvers:
        return ICON_ALL_BLACK, "", ""

    m = maneuvers[0]
    succinct   = m.get("verbal_succinct_transition_instruction", "")
    streetnames = m.get("street_names", [])
    multi_cue  = m.get("verbal_multi_cue", False)

    top = ""          # Zeile oben → Himmelsrichtung
    new_name = ""     # Zeile unten → neue Straße

    if multi_cue and len(maneuvers) > 1:
        next_m = maneuvers[1]
        t = next_m.get("type")
        names = next_m.get("street_names", [])

        if t in (24,25,26,27):      # Kreisverkehr
            icon = ICON_ROUNDABOUT
            new_name = names[0] if names else _extract_new_streetname_from_text(succinct)

        elif t in (9,15):           # Links
            icon = ICON_TURN_LEFT
            new_name = names[0] if names else _extract_new_streetname_from_text(succinct)

        elif t == 10:               # Rechts
            icon = ICON_TURN_RIGHT
            new_name = names[0] if names else _extract_new_streetname_from_text(succinct)

        else:                       # Geradeaus
            icon = ICON_STRAIGHT
            top = bearing_to_cardinal(next_m.get("bearing_after", m.get("bearing_after", 0)))
            new_name = names[0] if names else (streetnames[0] if streetnames else "")

    else:
        t = m.get("type")

        if t in (1,2,3):            # Start / Geradeaus
            icon = ICON_STRAIGHT
            top = bearing_to_cardinal(m.get("bearing_after", 0))
            new_name = streetnames[0] if streetnames else _extract_new_streetname_from_text(succinct)

        elif t in (9,15):           # Links
            icon = ICON_TURN_LEFT
            new_name = streetnames[0] if streetnames else _extract_new_streetname_from_text(succinct)

        elif t == 10:               # Rechts
            icon = ICON_TURN_RIGHT
            new_name = streetnames[0] if streetnames else _extract_new_streetname_from_text(succinct)

        elif t in (24,25,26,27):    # Kreisverkehr
            icon = ICON_ROUNDABOUT
            new_name = streetnames[0] if streetnames else _extract_new_streetname_from_text(succinct)

        else:
            icon = ICON_ALL_BLACK
            new_name = streetnames[0] if streetnames else _extract_new_streetname_from_text(succinct)

    return icon, top, new_name or ""

def _nav_loop():
    global _running, _stop
    ser = _open_serial_blocking(SERIAL_DEV, BAUD)
    print("Navigation gestartet.")

    interval = INTERVAL
    next_tick = time.time()

    try:
        while not _stop:
            if USE_GPS:
                subprocess.run(["sudo", "systemctl", "restart", "gpsd"],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            fix = _get_gps(timeout_s=6)

            if fix:
                data = _get_valhalla_response(*fix)
                icon, top, bot = _package_instruction(data) if data else (ICON_ALL_BLACK, "", "")
            else:
                icon, top, bot = ICON_ALL_BLACK, "", ""

            pkg = {
                "i": icon,
                "t": normalize_text(top),
                "b": normalize_text(bot)
            }

            try:
                ser.write((json.dumps(pkg) + "\n").encode("utf-8"))
                ser.flush()
                if DEBUG:
                    now = time.strftime("%H:%M:%S")
                    print(f"[{now}] [SEND] {json.dumps(pkg, ensure_ascii=False)}")
            except Exception:
                try:
                    ser.close()
                except Exception:
                    pass
                ser = _open_serial_blocking(SERIAL_DEV, BAUD)

            now = time.time()
            next_tick += interval
            delay = next_tick - now
            if delay > 0:
                time.sleep(delay)
            else:
                next_tick = now

    finally:
        try:
            ser.close()
        except Exception:
            pass
        _running = False
        _stop = False

        print("Navigation beendet.")

def _start_nav():
    global _running, _stop
    if _running:
        return
    _stop = False
    _running = True
    threading.Thread(target=_nav_loop, daemon=True).start()

def _shutdown_button_watcher():
    last = GPIO.input(BTN_SHUTDOWN)
    while True:
        cur = GPIO.input(BTN_SHUTDOWN)
        if last == GPIO.HIGH and cur == GPIO.LOW:
            time.sleep(0.05)
            if GPIO.input(BTN_SHUTDOWN) == GPIO.LOW:
                print("⏻ Shutdown-Button gedrückt → Raspberry Pi wird heruntergefahren.")
                subprocess.run(["sudo", "shutdown", "-h", "now"])
                while GPIO.input(BTN_SHUTDOWN) == GPIO.LOW:
                    time.sleep(0.02)
        last = cur
        time.sleep(0.02)

def main():
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(BTN_SHUTDOWN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    threading.Thread(target=_shutdown_button_watcher, daemon=True).start()

    print("Warte auf GPS-Fix zum Starten der Navigation...")

    while True:
        fix = _get_gps(timeout_s=6, verbose=True)
        if fix:
            print("GPS-Fix verfügbar → starte Navigation.")
            break
        time.sleep(3)

    _start_nav()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nAbbruch mit Ctrl+C erkannt. Beende Navigation...")
        global _stop
        _stop = True
        time.sleep(1)
        GPIO.cleanup()
        print("Beendet. GPIO freigegeben.")

if __name__ == "__main__":
    main()
