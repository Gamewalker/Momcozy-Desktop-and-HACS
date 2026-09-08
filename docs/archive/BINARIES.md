> Archived guide. [Current setup](../SETUP.md).

# Desktop binaries: Windows, Linux and macOS

Download the archive for your machine from
[GitHub Releases](https://github.com/Gamewalker/Momcozy-Desktop-and-HACS/releases/latest).
The executable starts the camera bridges and opens one VLC window per camera.
Playback needs **VLC and your private camera configuration**; Python and Go are
not required on the viewing machine. **0.2.0 adds a local browser setup assistant**
with its own bundled helper runtime. Older 0.1.x releases still require source
tools for first-time account preparation. Native helper packages are undergoing
validation; building a package is not proof of live-camera playback on that OS.

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

Extract the **entire archive**, including `setup-helper/` and its `_internal/`
directory. Do not copy just the executable. In a 0.2.0 complete package, starting
without existing cameras opens the [setup assistant](SETUP.md); use
`momcozy-desktop setup` to open it explicitly. It imports your own configuration,
signing file or APKs, or reads the installed app from an authorized Android
phone. It then performs account login and configuration locally.

The executable contains no vendor SDK keys, credentials or camera IDs. No
Android proxy is needed. The [source preparation instructions](DESKTOP-DE.md)
remain available for 0.1.x packages and developers.

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

With **version 0.1.3 or newer**, double-clicking the executable starts the
program. Version 0.2.0 opens setup when no private camera configuration exists;
otherwise it starts playback. Older releases accidentally retained Cobra's Explorer-start guard and
could display "This is a command line tool" instead of opening the cameras.
No manually opened terminal or command entry is needed. A console window still
appears because this is a console application; keep it open during playback.
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

For Home Assistant audio, use version 0.1.2 or newer with per-camera
`"audio-format": "aac"` and `"ffmpeg-path"` settings. This requires a separate
FFmpeg installation on the bridge computer. See [HA audio configuration](HOME_ASSISTANT.md#optional-audio-conversion-for-home-assistant).
For VLC, use **0.3.1 or newer** with `"audio-format": "copy"` to play original
BM04 audio without FFmpeg. Version 0.3.1 fixes the sample-rate/timestamp mismatch
that could leave VLC silent in earlier versions. Existing private configurations
remain compatible; replace the package and restart the bridge and VLC.
AAC remains available and is the supported choice for Home Assistant.

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
Get-FileHash .\momcozy-desktop-v0.2.0-windows-amd64.zip -Algorithm SHA256
```

```bash
sha256sum -c SHA256SUMS --ignore-missing   # Linux
shasum -a 256 momcozy-desktop-v0.2.0-darwin-arm64.tar.gz  # macOS
```

Maintainers build complete setup packages **natively on each target OS and
architecture**. The [Native setup helpers workflow](../../.github/workflows/setup-helper-builds.yml)
installs the build dependencies, builds the helper and verifies the extracted
archive. Windows additionally rebuilds the helper bootloader for Unicorn;
see the workflow and `scripts/build_setup_helper.py`.

```bash
python -m pip install -r requirements-setup-build.txt
python scripts/build_setup_helper.py --output /tmp/momcozy-setup-helper
python scripts/release.py --version v0.2.0 --target linux/amd64 \
  --setup-helper /tmp/momcozy-setup-helper --verify-native --output /tmp/momcozy-release
```

Use the matching `--target` for your native build machine. Omitting
`--setup-helper` creates a playback-only package; omitting `--target` cross-builds
all five playback binaries. Those packages do not contain the setup runtime.

Archives include the bridge executable, documentation, public helper sources
and runtime dependencies when selected, and license notices. APKs and private
configuration are excluded. Go builds use `CGO_ENABLED=0` and `-trimpath`;
each archive has an accompanying SHA256SUMS entry. Native startup tests do not
replace playback testing on the target operating system.
