# Schnellstart

BM04-Kameras mit Bild und Ton auf Windows, Linux, macOS oder in Home Assistant ansehen.

## Vorbereitung

- Kameras in der Momcozy-App mit deinem Konto koppeln.
- Momcozy-Zugangsdaten für DE/EU und ein Google-Konto bereithalten.
- [VLC](https://www.videolan.org/vlc/) und Chrome, Edge, Chromium oder Brave installieren.
- [Aktuelles Paket herunterladen](https://github.com/Gamewalker/Momcozy-Desktop-and-HACS/releases/latest) und vollständig entpacken.

## Einrichten

1. **Windows:** `momcozy-desktop.exe` doppelklicken. **Linux/macOS:** im entpackten Ordner `./momcozy-desktop` ausführen.
2. **Von Google Play herunterladen · ohne Android-Gerät** wählen.
3. **App vorbereiten** anklicken und im Browser bei Google anmelden.
4. Momcozy-E-Mail-Adresse und Passwort eingeben.
5. **Auf diesem Desktop mit VLC** und **Originalton beibehalten** wählen.
6. **Kameras einrichten → Kameras jetzt starten** anklicken.

Archiv- und Fallback-Einstellungen beibehalten. Eine funktionierende App-Version wird lokal gespeichert und bei Bedarf automatisch wiederverwendet.

## Danach

Die EXE beziehungsweise `./momcozy-desktop` startet deine eingerichteten Kameras. Das Programmfenster während der Wiedergabe geöffnet lassen; **Strg+C** beendet die Bridge.

Einrichtung erneut öffnen: `.\momcozy-desktop.exe setup` unter Windows, `./momcozy-desktop setup` unter Linux/macOS.

Zum Aktualisieren die Bridge beenden, das neue Paket vollständig entpacken und daraus starten. Den bisherigen Konfigurationsordner weiterverwenden.

Für Home Assistant im Assistenten **In Home Assistant** wählen und [dieser Anleitung](HOME_ASSISTANT.md) folgen. Dafür FFmpeg auf dem Bridge-Rechner installieren und AAC aktivieren.

[Paketauswahl und eigener Konfigurationsordner](BINARIES.md) · [Archiv](archive/README.md)
