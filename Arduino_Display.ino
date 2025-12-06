#include <MCUFRIEND_kbv.h>
#include <Adafruit_GFX.h>
#include <U8g2_for_Adafruit_GFX.h>
#include "bitmaps.h"   // liefert epd_bitmap_allArray und *_LEN

// ================== Display & Layout ==================
MCUFRIEND_kbv tft;
U8G2_FOR_ADAFRUIT_GFX u8g2;

#define BLACK 0x0000
#define WHITE 0xFFFF

// Portrait
const int SCREEN_W = 240;
const int SCREEN_H = 320;

// Icon (64x64) auf 2x skalieren
const int ICON_SIZE = 64;
const int SCALE     = 2;
const int ICON_W    = ICON_SIZE * SCALE;  // 128
const int ICON_H    = ICON_SIZE * SCALE;  // 128
const int ICON_Y    = 40;                 // oberer Rand

// Text-Positionen
const int LINE1_Y   = ICON_Y + ICON_H + 26;  // erste Zeile
const int LINE2_Y   = LINE1_Y + 28;          // zweite Zeile

// ================== Bitmap-Scaler ==================
void drawBitmapScaled(int x, int y,
                      const unsigned char *bitmap,
                      int w, int h,
                      uint16_t color,
                      int scale) {
  for (int j = 0; j < h; j++) {
    for (int i = 0; i < w; i++) {
      int byteIndex = (j * (w / 8)) + (i / 8);
      uint8_t byteValue = pgm_read_byte(bitmap + byteIndex);
      if (byteValue & (0x80 >> (i & 7))) {
        tft.fillRect(x + i * scale, y + j * scale, scale, scale, color);
      }
    }
  }
}

// ================== Mini-JSON (ohne Library) ==================
static inline int _findKey(const String &s, const char *key) {
  String pat = "\"" + String(key) + "\"";
  return s.indexOf(pat);
}

static bool jsonGetInt(const String &s, const char *key, long &out) {
  int p = _findKey(s, key);
  if (p < 0) return false;
  p = s.indexOf(':', p);
  if (p < 0) return false;
  p++;
  while (p < (int)s.length() && s[p] == ' ') p++;
  bool neg = false;
  if (p < (int)s.length() && s[p] == '-') { neg = true; p++; }
  long val = 0; bool any = false;
  while (p < (int)s.length() && isDigit(s[p])) {
    val = val * 10 + (s[p] - '0'); any = true; p++;
  }
  if (!any) return false;
  out = neg ? -val : val;
  return true;
}

static bool jsonGetString(const String &s, const char *key, String &out) {
  int p = _findKey(s, key);
  if (p < 0) return false;
  p = s.indexOf(':', p);
  if (p < 0) return false;
  p++;
  while (p < (int)s.length() && s[p] == ' ') p++;
  if (p >= (int)s.length() || s[p] != '\"') return false;
  p++;
  String val;
  while (p < (int)s.length()) {
    char c = s[p++];
    if (c == '\\' && p < (int)s.length()) {
      val += s[p++];
      continue;
    }
    if (c == '\"') break;
    val += c;
  }
  out = val;
  return true;
}

// ================== Text-Helfer ==================
void drawCenteredUTF8(const String &txt, int y) {
  u8g2.setCursor((SCREEN_W - u8g2.getUTF8Width(txt.c_str())) / 2, y);
  u8g2.print(txt);
}

// ================== Anzeige ==================
int16_t currentIcon = -1;
String  currentTop  = "";
String  currentBot  = "";

void renderAll() {
  tft.fillScreen(BLACK);

  // Icon mittig anzeigen, oder 'all_black' wenn Index außerhalb gültigen Bereichs
  const unsigned char* bmp =
    (currentIcon >= 0 && currentIcon < epd_bitmap_allArray_LEN)
    ? epd_bitmap_allArray[currentIcon]
    : epd_bitmap_allArray[epd_bitmap_allArray_LEN - 1];  // letzter = all_black

  int iconX = (SCREEN_W - ICON_W) / 2;
  drawBitmapScaled(iconX, ICON_Y, bmp, ICON_SIZE, ICON_SIZE, WHITE, SCALE);

  u8g2.setForegroundColor(WHITE);
  u8g2.setBackgroundColor(BLACK);
  u8g2.setFont(u8g2_font_helvR18_tf);

  drawCenteredUTF8(currentTop, LINE1_Y);
  drawCenteredUTF8(currentBot, LINE2_Y);
}

// ================== Setup ==================
void setup() {
  Serial.begin(115200);

  uint16_t id = tft.readID();
  tft.begin(id);
  tft.setRotation(0);   // Portrait
  tft.fillScreen(BLACK);

  u8g2.begin(tft);
  u8g2.setForegroundColor(WHITE);
  u8g2.setBackgroundColor(BLACK);

  // Startbild
  currentIcon = epd_bitmap_allArray_LEN - 1;  // all_black
  currentTop  = "Warte auf";
  currentBot  = "GPS...";
  renderAll();
}

// ================== Loop ==================
void loop() {
  if (Serial.available()) {
    String line = Serial.readStringUntil('\n');
    line.trim();
    if (line.length() == 0) return;

    long idx = 0;
    String top, bot;

    bool okI = jsonGetInt(line, "i", idx);
    bool okT = jsonGetString(line, "t", top);
    bool okB = jsonGetString(line, "b", bot);

    if (!okI && !okT && !okB) return;

    if (!okI) idx = epd_bitmap_allArray_LEN - 1;
    if (!okT) top = "";
    if (!okB) bot = "";

    bool changed = false;
    if (idx != currentIcon)            { currentIcon = (int)idx; changed = true; }
    if (top != currentTop)             { currentTop  = top;      changed = true; }
    if (bot != currentBot)             { currentBot  = bot;      changed = true; }

    if (changed) renderAll();
  }
}
