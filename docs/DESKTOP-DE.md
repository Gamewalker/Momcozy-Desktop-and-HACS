# Desktop-Kurzanleitung

Die BM04 lässt sich über diese Bridge in VLC ansehen. Mit zwei Kameras wurden
unter Windows gleichzeitig Full-HD-Bild und Ton geprüft. Anmeldung und
Verbindungsvermittlung benötigen weiterhin die Momcozy-/Tuya-Cloud.

## Linux und macOS

Voraussetzungen: Python 3.11+, Go 1.26.2+ und VLC. Unter macOS VLC in
`/Applications` installieren; unter Linux muss `vlc` im Suchpfad liegen.

```sh
git clone https://github.com/Gamewalker/momcozy-desktop.git
cd momcozy-desktop
./scripts/setup.sh
```

Einmalig die eigenen APKs der Android-App 3.3.0 vorbereiten:

```sh
.venv/bin/python client/prepare_apk.py /pfad/base.apk /pfad/split_config.arm64_v8a.apk
```

Die private INI-Datei enthält `USERNAME=...` und `PASSWORD=...`. Sie gehört
außerhalb des Repositories. Dann:

```sh
chmod 600 /pfad/momcozy.txt
.venv/bin/python client/configure.py /pfad/momcozy.txt
./scripts/watch.sh
```

Der Starter öffnet je Kamera ein VLC-Fenster. Das Terminal offen lassen;
Strg+C beendet die gestarteten Kameraverbindungen. `--no-player` stellt nur die
lokalen RTSP-Streams bereit. Es wird kein Dienst oder Autostart installiert.

Private Daten liegen standardmäßig unter `~/.momcozy-desktop`; ein anderer
Ordner lässt sich über `MOMCOZY_DATA_DIR` angeben. Bereits vorhandene
`signing.private.json`, `bridge-N.private.json` und `cameras.private.json`
können privat dorthin übertragen werden. Bei abgelaufener Sitzung die Anmeldung
mit `configure.py` wiederholen. Keine dieser Dateien veröffentlichen.

Linux und macOS wurden für Intel und ARM erfolgreich kompiliert. Der Starter
wurde mit echten Kameras unter Windows geprüft; ein nativer Kameratest unter
Linux/macOS steht noch aus.

## Probleme

- **Port belegt:** andere laufende Instanz beenden; der Starter beendet keine
  fremden Prozesse.
- **Anmeldung abgelaufen:** `configure.py` erneut ausführen. Nur DE/EU ist
  bisher implementiert und getestet.
- **Kein VLC:** VLC installieren oder `--no-player` verwenden.
- **Private Diagnose:** `~/.momcozy-desktop/runtime/bm04_N/bridge.log` kann bei
  der Fehlersuche helfen, enthält aber möglicherweise Gerätekennungen. Nicht
  ungeprüft an ein öffentliches Issue hängen.

Die spätere Home-Assistant-Integration ist unter `custom_components/momcozy/`
vorbereitet. Aktuell ist das Repository noch nicht über HACS installierbar.
