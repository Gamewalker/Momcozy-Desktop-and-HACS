> Archived guide. [Current setup](../SETUP.md).

# Desktop-Kurzanleitung

Die BM04 lässt sich über diese Bridge in VLC ansehen. Mit zwei Kameras wurden
unter Windows gleichzeitig Full-HD-Bild und Ton geprüft. Anmeldung und
Verbindungsvermittlung benötigen weiterhin die Momcozy-/Tuya-Cloud.

## Windows

### Fertige EXE herunterladen

Unter [GitHub Releases](https://github.com/Gamewalker/Momcozy-Desktop-and-HACS/releases/latest) das Windows-amd64-ZIP herunterladen, **vollständig entpacken** und `momcozy-desktop.exe` starten. Für die Wiedergabe wird VLC benötigt; Python und Go sind dafür nicht nötig.

**Neu für 0.2.0:** Ohne vorhandene Kamerakonfiguration öffnet sich ein lokaler
[Einrichtungsassistent](SETUP.md). Der komplette Download enthält dessen
Hilfsprogramm und Python-Laufzeit. Der Assistent kann ein angeschlossenes
Android-Telefon, eigene APK-Dateien oder vorhandene private Konfigurationen
verwenden. Manuelle Python-, ADB- und JSON-Schritte entfallen. Mit
`momcozy-desktop.exe setup` lässt er sich erneut öffnen. Die nativen Pakete
befinden sich noch in der Prüfung; Versionen 0.1.x enthalten diesen Assistenten
nicht. Details einschließlich `--data-dir` stehen in der [Binary-Anleitung](BINARIES.md).

Die folgenden Schritte beschreiben die Einrichtung aus dem Quellcode.

### Voraussetzungen

Installiere Python 3.11+, Go 1.26.2+, Git und VLC. Python, Go und Git müssen
in PowerShell über `python`, `go` und `git` erreichbar sein; nach der
Installation gegebenenfalls ein neues PowerShell-Fenster öffnen. Der Starter
findet VLC unter `C:\Program Files\VideoLAN\VLC\vlc.exe` oder über den Suchpfad.

Für die einmalige APK-Aufbereitung werden zusätzlich Android Platform Tools
(`adb`) und die eigenen APKs der Momcozy-App **3.3.0** benötigt. Wer bereits eine
private Konfiguration besitzt, kann stattdessen den Abschnitt „Vorhandene
Konfiguration übernehmen“ verwenden.

### Repository und Werkzeuge einrichten

Die folgenden Befehle in **PowerShell** ausführen:

```powershell
git clone https://github.com/Gamewalker/Momcozy-Desktop-and-HACS.git
cd Momcozy-Desktop-and-HACS
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
New-Item -ItemType Directory -Force bin | Out-Null
go -C bridge build -o ../bin/momcozy-bridge.exe .
```

Jeder Schritt muss erfolgreich abschließen, bevor der nächste ausgeführt wird.
Die virtuelle Umgebung wird direkt angesprochen; `Activate.ps1` und eine
Änderung der PowerShell-Ausführungsrichtlinie sind dafür nicht erforderlich.
Alternativ zur fertigen EXE erzeugt der Build-Befehl eine lokale Version unter
`bin\momcozy-bridge.exe`.

### Einmalig APKs und Konto vorbereiten

Das Android-Telefon anschließen, USB-Debugging aktivieren und die angezeigte
ADB-Verbindung am Telefon bestätigen:

```powershell
adb devices
adb shell pm path com.lute.momcozy
```

Die zweite Ausgabe enthält die installierten APK-Pfade. Den Pfad für `base.apk`
und den ARM64-Split übernehmen; das Präfix `package:` nicht mitkopieren. Mit
`adb pull "ANDROID-PFAD" "LOKALER-PFAD"` beide Dateien in einen privaten Ordner
außerhalb des Repositories kopieren. Die Platzhalter im folgenden Beispiel
durch die tatsächlich ausgegebenen Android-Pfade ersetzen:

```powershell
$private = Join-Path $env:USERPROFILE 'Momcozy-Privat'
New-Item -ItemType Directory -Force $private | Out-Null
adb pull "/data/app/PLATZHALTER/base.apk" "$private\base.apk"
adb pull "/data/app/PLATZHALTER/split_config.arm64_v8a.apk" "$private\split_config.arm64_v8a.apk"
.\.venv\Scripts\python.exe client\prepare_apk.py "$private\base.apk" "$private\split_config.arm64_v8a.apk"
```

Im privaten Ordner eine Datei `momcozy.txt` anlegen, beispielsweise mit Editor:

```powershell
notepad "$private\momcozy.txt"
```

Inhalt der Datei:

```ini
USERNAME=deine-kontoadresse@example.com
PASSWORD=dein-passwort
```

Die Datei speichern und die Anmeldung ausführen:

```powershell
.\.venv\Scripts\python.exe client\configure.py "$private\momcozy.txt"
```

Die Zugangsdaten gehören nicht ins Repository. Nur der DE/EU-Anmeldeweg ist
bisher implementiert und getestet. Für spätere Wiedergabe wird das Telefon
nicht benötigt; die Cloud-Verbindung bleibt erforderlich.

### Kameras ansehen und stoppen

Aus dem Repository-Ordner starten:

```powershell
.\.venv\Scripts\python.exe client\watch.py
```

Pro Kamera öffnet sich ein VLC-Fenster mit Bild und Ton. PowerShell offen
lassen; **Strg+C** beendet die von diesem Starter gestarteten
Kameraverbindungen. Die VLC-Fenster separat schließen.

Nur die lokalen Streams bereitstellen, ohne VLC automatisch zu öffnen:

```powershell
.\.venv\Scripts\python.exe client\watch.py --no-player
```

Die erste Kamera ist über `rtsp://127.0.0.1:18554/bm04_1`, die zweite über
`rtsp://127.0.0.1:18555/bm04_2` erreichbar. Die Nummerierung entspricht der
Geräteabfrage. Der automatische Starter verwendet RTSP über TCP. Die Streams
sind nur auf diesem PC erreichbar; eine Firewall-Freigabe ist nicht nötig.

### Vorhandene Konfiguration übernehmen

Die Repository-Version verwendet standardmäßig
`$env:USERPROFILE\.momcozy-desktop`. Bereits erzeugte Dateien
`signing.private.json`, `bridge-N.private.json` und – falls vorhanden –
`cameras.private.json` privat dorthin kopieren. Alternativ in derselben
PowerShell-Sitzung vor Anmeldung und Start einen bestehenden privaten
Konfigurationsordner auswählen:

```powershell
$env:MOMCOZY_DATA_DIR = 'C:\Pfad\zur\privaten\Konfiguration'
.\.venv\Scripts\python.exe client\watch.py
```

Eine bereits laufende Instanz vorher beenden, damit die Kamera-Ports frei sind.
Bei abgelaufener Sitzung `client\configure.py` mit dem Pfad zur eigenen
Zugangsdaten-Datei erneut ausführen. Das ausgewählte Datenverzeichnis dabei
beibehalten.

Bei der zuvor individuell eingerichteten Windows-Testinstallation heißen die
Desktop-Verknüpfungen **Momcozy Kameras** und **Momcozy stoppen**. Sie starten
bzw. beenden deren Hintergrundverbindungen; `Anmeldung erneuern.cmd` liegt im
zugehörigen `outputs`-Ordner. Diese Verknüpfungen gehören zur lokalen
Testinstallation und werden durch einen Git-Clone nicht automatisch angelegt.
Die Repository-Version wird wie oben über `client\watch.py` bedient.

Windows-Diagnoseprotokolle liegen standardmäßig unter
`$env:USERPROFILE\.momcozy-desktop\runtime\bm04_N\bridge.log`. Bei Verwendung
von `MOMCOZY_DATA_DIR` liegen sie entsprechend unter diesem Ordner. Protokolle
können Gerätekennungen enthalten und gehören nicht ungeprüft in öffentliche
Issues.

## Linux und macOS

Voraussetzungen: Python 3.11+, Go 1.26.2+ und VLC. Unter macOS VLC in
`/Applications` installieren; unter Linux muss `vlc` im Suchpfad liegen.

```sh
git clone https://github.com/Gamewalker/Momcozy-Desktop-and-HACS.git
cd Momcozy-Desktop-and-HACS
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

## Home Assistant und Ton

Die Integration ist über HACS als benutzerdefiniertes Repository installierbar;
siehe [Home-Assistant-Anleitung](HOME_ASSISTANT.md). Die Bridge läuft separat.

Ab Bridge-Version **0.1.2** lässt sich der Ton pro Kamera für HA nach AAC
umwandeln. FFmpeg auf dem Bridge-Rechner installieren und diese Schlüssel in die
bestehende `bridge-N.private.json` ergänzen (andere Einträge beibehalten):

```json
"audio-format": "aac",
"ffmpeg-path": "C:\\Tools\\ffmpeg\\bin\\ffmpeg.exe"
```

Unter Linux/macOS den absoluten Pfad aus `command -v ffmpeg` einsetzen.
Bridge neu starten, HA-Liveansicht schließen und erneut öffnen; im Player den
Ton einschalten. Adresse und Zugangsdaten in HA bleiben gleich. Zurückstellen
mit `"audio-format": "copy"` und anschließendem Neustart. `copy` ist der Standard
und benötigt kein FFmpeg. Nur Audio wird umgewandelt, das Video bleibt unverändert.
