# Momcozy BM04 Desktop

[Deutsche Kurzanleitung](docs/DESKTOP-DE.md) · [Planned HACS integration](docs/HOME_ASSISTANT.md)

An experimental desktop viewer for your own Momcozy BM04 cameras. It signs in
with your Momcozy account, negotiates Tuya WebRTC, and exposes one **loopback-only
RTSP stream per camera** for VLC. No phone proxy, root, modified app or Tuya
developer account is required for normal playback.

**Verified:** two BM04 cameras, firmware 25.01.08, Android app 3.3.0, EU account,
Windows desktop; simultaneous 1920×1080 H.265 video and G.711 A-law audio.
The cloud is still required for authentication and signaling. This is not an
offline RTSP firmware replacement or an official Momcozy product.

## Contents

- `bridge/`: Go WebRTC-to-RTSP bridge, adapted from aventproxy.
- `client/`: local APK preparation, account login and camera discovery.
- `scripts/`: Linux/macOS setup and playback entry points.
- `custom_components/momcozy/`: reserved location for the future HACS integration.
- `tests/client/` and `tests/home_assistant/`: separate desktop and future HA tests.
- `docs/PROTOCOL.md`: observed authentication and media protocol.
- `docs/SECURITY.md`: private state, reporting and publication boundaries.

## Prepare your own configuration

Use Python 3.11+ and Go 1.26.2+. Install VLC from
[VideoLAN](https://www.videolan.org/vlc/). Go is available from
[go.dev](https://go.dev/dl/), Python from [python.org](https://www.python.org/downloads/).
Dependency versions are pinned in `requirements.txt` and `bridge/go.mod`/`go.sum`.

Create a virtual environment and install the client dependencies:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

On Windows use `python` and `.venv\Scripts\python.exe` instead.

You need your own **3.3.0** base APK and ARM64 split APK. With your Android phone
connected and USB debugging enabled, `adb shell pm path com.lute.momcozy` lists
the installed APK paths. Copy the listed base and ARM64 paths with `adb pull`.
Do not download an arbitrary APK from this project: no proprietary APK or
embedded application secret is distributed here.

```sh
.venv/bin/python client/prepare_apk.py /path/to/base.apk /path/to/split_config.arm64_v8a.apk
```

Create a private file **outside the repository**:

```ini
USERNAME=your-account@example.com
PASSWORD=your-password
```

Then authenticate and discover your cameras:

```sh
chmod 600 /path/to/momcozy.txt
.venv/bin/python client/configure.py /path/to/momcozy.txt
```

Only the DE/EU account flow is currently implemented and tested. Do not change
the API host at random for other account regions. A failed login is not retried
automatically. Rerun `configure.py` manually when your session expires.

Private state defaults to `~/.momcozy-desktop`. Set `MOMCOZY_DATA_DIR` to an
absolute path to use another private folder. Unix state is created with a
restrictive umask; on Windows use a directory protected by your user profile's
ACLs. Account passwords are read from your file, not CLI arguments. Session
tokens, application keys and device IDs in the state directory remain sensitive.

## Linux and macOS playback

Install Python, Go and VLC, then:

```sh
git clone https://github.com/Gamewalker/momcozy-desktop.git
cd momcozy-desktop
./scripts/setup.sh
```

Prepare your own APK and credentials using the commands above. Then run:

```sh
./scripts/watch.sh
```

One VLC instance opens per camera. Keep the terminal open. **Ctrl+C** stops the
bridges started by this invocation; close VLC windows separately. To serve only
local RTSP, use `./scripts/watch.sh --no-player`. The script never opens ports
on other network interfaces, installs system services or changes phone settings.

On macOS the launcher finds `/Applications/VLC.app/Contents/MacOS/VLC`; on Linux
it uses `vlc` from PATH. Intel and ARM builds are supported. If VLC is installed
only through Flatpak, install a native VLC package or use `--no-player` and open
the local RTSP addresses in your player manually.

An existing installation can be transferred privately: copy
`signing.private.json`, `bridge-N.private.json` and, if present,
`cameras.private.json` into the new private state directory. These are sensitive
files; do not place them in Git. Saved sessions may expire, in which case rerun
`client/configure.py` with your own credentials file.

## Windows playback

```powershell
New-Item -ItemType Directory -Force bin
go -C bridge build -o ../bin/momcozy-bridge.exe .
.venv\Scripts\python.exe client\watch.py
```

The same Python launcher manages the two bridge processes and VLC windows.
For manual use, pass a `bridge-N.private.json` path as the executable's only
argument and use a separate private working directory per camera instance.

The first camera is `rtsp://127.0.0.1:18554/bm04_1`, the second
`rtsp://127.0.0.1:18555/bm04_2`. Cameras are numbered in discovery order; these
numbers are not a mapping to fixed LAN addresses. No firewall opening is needed.

## Testing and limitations

```sh
cd bridge
go test ./...
```

Client tests: `python -m unittest discover -s tests/client -v`.

Windows live-camera decoding and the new Python launcher are verified. Linux
amd64/arm64 and macOS amd64/arm64 cross-builds passed. Bash syntax and launcher
configuration tests passed; native live-camera playback on Linux/macOS has not
been performed on this Windows host. A cross-build alone does not establish
live-camera compatibility.
Long-duration reliability, network-outage recovery, automatic session refresh
and non-EU accounts remain unverified. Home Assistant has a
[reserved structure and implementation plan](docs/HOME_ASSISTANT.md), but no
installable HACS integration yet. Talkback is off by default.

## Attribution

The Go bridge is derived from
[thekoma/aventproxy](https://github.com/thekoma/aventproxy/tree/d15a3117fdf8d0059f59cf451c9d8c0470e8a68a/avent-webrtc-bridge),
snapshot `d15a3117fdf8d0059f59cf451c9d8c0470e8a68a`. Preserve both the root
`LICENSE` and `bridge/LICENSE` when redistributing. See `NOTICE.md` for the
BM04-specific changes. The app, APK assets and native libraries belong to their
respective owners and are not included.
