# Maturitätsarbeit Simon R.
In meiner Maturitätsarbeit entwickelte ich ein Offline-Navigationssytem. Auf einem Raspberry Pi läuft die eigentliche Routenberechnung mithilfe der OpenSource Routing-Engine Valhalla, die aus OpenStreetMap-Daten schriftliche Fahranweisungen generieren kann. Diese werden anschliessend umgewandelt in Datenpakete, welche an ein Arduino gesendet werden und dort auf dem verbundenen Display anschaulich dargestellt werden. Dazu werden eigene Piktogramme und zwei Infolines verwendet. Mit einem Smartphone kann auf das Raspberry Pi zugegriffen werden und so das Routenziel geändert werden. Über denselben Weg kann gewählt werden, ob Mautstrassen vermieden werden sollen. Zur Positionsbestimmung wurde ein externer GPS-Empfänger angeschlossen und ein Taster dient als Shutdown-Knopf

Demonstrationsvideo:

Wer meine schriftliche Arbeit gelesen hat, sucht sicherlich nach dem Demonstrationsvideo. Da die Datei zu gross ist, um sie auf GitHub hochzuladen, ist hier ein Link der zum Demonstrationsvideo in Google Drive führt: https://drive.google.com/file/d/1LstXG9QNH3jJEgkffdLUCX2IxxNUCkCr/view?usp=sharing

Zum Zeitpunkt der Aufnahme hat die Distanzanzeige vor dem Abbiegen nicht korrekt funktioniert. Seither habe ich dieses Problem behoben und den hochgeladenen Code aktualisiert.

Im Ordner "Code" befindet sich der finale Code, der auf dem Raspberry Pi und auf dem Arduino ausgeführt wird.

Ich habe hier ebenso ein Arbeitsjournal hochgeladen, sowie jegliche Konversationen mit ChatGPT, die mir während der Entwicklungsphase geholfen haben. 
Hier ist eine Hilfestellung, um zu einem bestimmten Kapitel oder Abschnitt der schriftlichen Arbeit die zugehörige Konversation zu finden. Dabei ist zu beachten, dass diese Konversationen sehr lange sind und sich oft nur ein Ausschnitt auf den angegebenen Abschnitt bezieht.

- Kompatibilitätstest -> Arduino Raspberry Pi Zusammenarbeit, Bluetooth Steuerung für Spotify
- Valhalla Routing-Engine -> Bluetooth Steuerung für Spotify
- OpenStreetMap -> Valhalla Installation Raspberry Pi
- GPS-Empfänger -> USB GPS am Raspberry Pi
- Navigation mit Piktogrammen -> Valhalla Installation Raspberry Pi
- Display Optimierung -> Valhalla Installation Raspberry Pi, Navigationssystem Zusammenfassung
- Automatisierter Navigationsstart -> Valhalla Navigation Raspberry Pi, Navigationssystem Zusammenfassung
- Steuerung über das Smartphone -> WLan mit Hotspot verbinden



