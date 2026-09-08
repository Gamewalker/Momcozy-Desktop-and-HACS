# Desktop binaries: Windows, Linux and macOS

Download the archive for your machine from
[GitHub Releases](https://github.com/Gamewalker/momcozy-desktop/releases/latest).
The executable starts the camera bridges and opens one VLC window per camera.
Playback needs **VLC and your private camera configuration**; Python and Go are
not required on the viewing machine. This is a command-line application with VLC
windows, not an installer or a graphical account setup wizard.

| Machine | Release archive |
| --- | --- |
| Windows 64-bit Intel/AMD | `windows-amd64.zip` |
| Linux Intel/AMD 64-bit | `linux-amd64.tar.gz` |
| Linux ARM64, including 64-bit Raspberry Pi OS | `linux-arm64.tar.gz` |
| macOS Intel | `darwin-amd64.tar.gz` |
| macOS Apple Silicon | `darwin-arm64.tar.gz` |

Windows ARM64 and 32-bit systems are not provided in this release. macOS binaries
are currently unsigned and not notarized; macOS may require approval in Privacy
& Security. Windows may display an unknown-publisher prompt. Obtain the archive
from this repository and verify its SHA256SUMS entry before running it.

## 1. Prepare private configuration once

The executable does not contain vendor SDK keys, credentials or camera IDs.
Use the source checkout's [setup and account preparation instructions](https://github.com/Gamewalker/momcozy-desktop/blob/main/docs/DESKTOP-DE.md)
to extract SDK parameters from **your installed Android APK** and configure your
account. That initial step requires Python and the listed preparation tools.
Afterward, playback uses only the downloaded binary and VLC. No Android proxy is
needed.

Already configured on another computer? Transfer `bridge-*.private.json` and,
if present, `cameras.private.json` **privately** to:

- Windows: `%USERPROFILE%\.momcozy-desktop\`
- Linux/macOS: `~/.momcozy-desktop/`

These files grant camera access. Do not attach them or bridge logs to GitHub
issues. On Linux/macOS run `chmod 700 ~/.momcozy-desktop` and
`chmod 600 ~/.momcozy-desktop/*.private.json`. On Windows use your own user-profile
directory, with access limited to your Windows account. For a custom location use
`--data-dir` or the `MOMCOZY_DATA_DIR` environment variable. The manifest is a JSON
array of configuration basenames and takes precedence over file discovery.

## 2. Start on Windows

Install [VLC](https://www.videolan.org/vlc/), extract the ZIP, open PowerShell in
the extracted directory and run:

```powershell
.\momcozy-desktop.exe desktop
```

Double-clicking the executable also starts desktop mode. Keep its console open.
To use the configuration from a different directory:

```powershell
.\momcozy-desktop.exe desktop --data-dir "C:\Users\YOURNAME\.momcozy-desktop"
```

Stop with **Ctrl+C** in the console. Close the VLC windows when finished.

## 3. Start on Linux or macOS

Install VLC, extract the matching archive and open a terminal in that directory:

```bash
./momcozy-desktop desktop
```

On macOS, VLC is detected at `/Applications/VLC.app`; elsewhere it can be on
`PATH`. Linux needs a graphical desktop for automatic VLC playback.

```bash
./momcozy-desktop desktop --data-dir "$HOME/.momcozy-desktop"
```

Stop with **Ctrl+C**. No root privileges are needed.

## Serve without opening a player

For Home Assistant audio, version 0.1.1 adds optional per-camera
`"audio-format": "aac"` and `"ffmpeg-path"` settings. This requires a separate
FFmpeg installation on the bridge computer. See [HA audio configuration](HOME_ASSISTANT.md#optional-audio-conversion-for-home-assistant).
The default `copy` mode continues to work without FFmpeg.

```bash
./momcozy-desktop desktop --no-player
```

The console prints local RTSP URLs such as `rtsp://127.0.0.1:18554/bm04_1`.
Open these in VLC using Media → Open Network Stream. An RTSP listener becoming
ready does not itself confirm that video is already flowing: the camera cloud
connection begins when a player requests the stream.

Desktop configurations listen only on loopback by default. Configurations with
RTSP authentication or a LAN listener must use `--no-player`; enter credentials
directly into the player rather than putting a password on the process command
line. For wildcard listeners the printed loopback address is for local testing;
remote clients use the bridge computer's LAN address. See the Home Assistant
instructions for authenticated LAN access.

Use `--seconds 30 --no-player` to stop after 30 seconds once all listeners are
ready. The supervisor stops only the bridge processes it started. It leaves VLC
windows open so another unrelated VLC instance is never terminated. Normal
Ctrl+C termination cleans up; forcibly killing the supervisor or shutting its
console abruptly can leave children, so prefer Ctrl+C. On Windows child bridge
shutdown uses process termination; on Unix SIGTERM is attempted before a bounded
forced stop.

## Troubleshooting

- **No configuration:** complete preparation above or choose `--data-dir`.
- **Port already in use:** stop the older viewer before launching another copy.
- **VLC missing:** install VLC in its default location or use `--no-player`.
- **Bridge exits / session expired:** renew configuration with the source
  checkout's `client/configure.py`; this release does not renew login sessions
  automatically. Do not run old and new copies with the same camera session
  concurrently.
- **No image:** wait for cloud connection, then inspect private
  `<data-dir>/runtime/bm04_N/bridge.log`. Logs are overwritten on each start and
  may contain device metadata. Runtime directories are limited to the current
  user (Unix permissions or Windows ACL).
- **Audio/video codecs:** the BM04 stream uses H.265 video. VLC handles this;
  browser compatibility depends on browser and platform.

## Verify and build releases

Compare the downloaded archive against its published `SHA256SUMS` entry:

```powershell
Get-FileHash .\momcozy-desktop-v0.1.0-windows-amd64.zip -Algorithm SHA256
```

```bash
sha256sum -c SHA256SUMS --ignore-missing   # Linux
shasum -a 256 momcozy-desktop-v0.1.0-darwin-arm64.tar.gz  # macOS
```

Maintainers can create all five archives with Go and Python installed:

```bash
python scripts/release.py --version v0.1.0 --output /tmp/momcozy-release
```

Archives use a strict source-only allowlist: executable, this guide, project and
upstream licenses, notices, and dependency license files. Private configuration,
APK files and runtime logs are never included. Builds use `CGO_ENABLED=0` and
`-trimpath`; generated archives have an accompanying SHA256SUMS file. Cross-build
success does not replace playback testing on the target operating system.
