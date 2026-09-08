> Archived guide. [Current setup](../SETUP.md).

# Home Assistant / HACS

The **Momcozy Bridge** custom integration exposes one camera entity per bridge
stream. It includes UI setup, reconfiguration, TCP RTSP streaming, JPEG stills,
connection validation and English/German translations. Home Assistant **2025.6.0
or newer** is required.

The camera connection still needs the Momcozy/Tuya cloud. Home Assistant talks
only to your local bridge. HACS installs the Python integration; it does **not**
install or start the Go bridge, log into Momcozy, or extract Android app keys.
This is not a Supervisor add-on. Keep the bridge running on a separate Windows,
Linux or macOS computer; that computer must remain awake.

## 1. Prepare a reachable bridge

Complete the [desktop setup](DESKTOP-DE.md) first and confirm playback in VLC.
Use the [GitHub release](https://github.com/Gamewalker/Momcozy-Desktop-and-HACS/releases)
for your bridge computer. A bridge listening only on `127.0.0.1` is inaccessible
to Home Assistant on another machine or container.

For each camera's private bridge JSON configuration, add these keys:

```json
{
  "listen-host": "192.168.1.50",
  "rtsp-user": "homeassistant",
  "rtsp-password": "REPLACE-WITH-A-LONG-RANDOM-PASSWORD"
}
```

These keys are **added to the existing private camera configuration**, which
already contains cloud session and camera values. This snippet is not a complete
configuration. Replace the host with the bridge computer's LAN IP. Use a unique
RTSP password of at least 16 characters; this is separate from your Momcozy
password. Restart the bridge after changing its configuration. Use a reserved
DHCP address so the host remains stable. The release's bridge executable accepts
the full private JSON file as its argument.

Allow inbound TCP from Home Assistant's LAN IP to the camera's RTSP port in the
bridge computer's firewall (normally `18554` for `bm04_1`, `18555` for `bm04_2`).
No UDP media ports are needed. Non-loopback bridge listeners require credentials.
RTSP Basic authentication and media are unencrypted: use a trusted private LAN
or VPN, and do not forward these ports to the public Internet.

For HA OS, use the LAN IP of the separate bridge computer. For HA Container,
`localhost` means the container itself, not its Docker host. Home Assistant's
public HTTPS address is not the address of the bridge.

Start the configured bridge without VLC (use your actual private folder):

```powershell
# Windows
.\momcozy-desktop.exe desktop --no-player --data-dir "C:\Private\Momcozy"
```

```sh
# Linux / macOS
./momcozy-desktop desktop --no-player --data-dir "$HOME/.momcozy-desktop"
```

For HA sound, enable [AAC conversion](#optional-audio-conversion-for-home-assistant)
before starting. Keep the process running; closing it disconnects HA cameras.

## 2. Install with HACS

1. Open **HACS → three-dot menu → Custom repositories**.
2. Add `https://github.com/Gamewalker/Momcozy-Desktop-and-HACS`, category **Integration**.
3. Find **Momcozy Desktop and HACS** in HACS and download it.
4. Restart Home Assistant.
5. Go to **Settings → Devices & services → Add integration → Momcozy Bridge**.

Manual installation is also supported: copy only
`custom_components/momcozy/` into `/config/custom_components/momcozy/`, then
restart Home Assistant. The component contains all its runtime code; repository
root Python modules and the desktop tooling do not belong in `/config`.

## Repository rename

The GitHub repository is now `Gamewalker/Momcozy-Desktop-and-HACS`.
For a new HACS installation, use the new URL above. Existing camera entries,
entity IDs, RTSP credentials and private bridge configuration do not need to
be recreated. The integration still appears as **Momcozy Bridge** in Home
Assistant; the HACS repository name is **Momcozy Desktop and HACS**.

For an existing source checkout, update its remote:

```sh
git remote set-url origin https://github.com/Gamewalker/Momcozy-Desktop-and-HACS.git
git pull
```

If HACS still lists the old repository name or an update fails, refresh HACS
and check its custom repository URL. Use the new URL for repository registration;
do not delete your working camera entries. Existing release executables and
private directory names remain `momcozy-desktop`.

## 3. Add each camera

| UI field | Example | Meaning |
|---|---|---|
| Name | Nursery | Display name |
| Bridge host | `192.168.1.50` | Computer running the bridge, without `rtsp://` |
| RTSP port | `18554` | Port in that camera's bridge configuration |
| Stream path | `bm04_1` | Exact `camera-name`, without host or port |
| RTSP username | `homeassistant` | Bridge `rtsp-user` |
| RTSP password | Your random password | Bridge `rtsp-password` |

Add the integration again for camera two, using its own port/path. Duplicate
host/port/path combinations are rejected. For an intentionally unauthenticated
loopback endpoint, leave **both** credential fields empty.

Setup performs an RTSP `DESCRIBE` handshake and checks for a video SDP. This
can initiate cloud signaling and a camera connection in the bridge, but does
not prove that frames are received. The initial connection can take several
seconds. The integration does not poll the endpoint repeatedly, avoiding
background camera reconnections when nobody is watching.

Open the camera entity's more-info dialog to view it, or add a Picture Entity
card to a dashboard. Example (use your actual entity ID):

```yaml
type: picture-entity
entity: camera.nursery
camera_view: live
show_name: true
show_state: false
```

The stream uses TCP. JPEG previews use Home Assistant's FFmpeg helper. FFmpeg is
included with HA OS and official Container images; custom Core installations
must provide it themselves. HA's stream component manages playback and shuts
streams down when the integration is unloaded.

## Reconfigure, remove and troubleshoot

Use the integration entry's **Reconfigure** menu to change host, port, path,
name or RTSP credentials. The existing entity identifier is preserved. Removing
the entry unloads its camera; it does not stop the external bridge or change the
camera/cloud account.

* **Cannot connect:** test from the HA network, check the bridge process, LAN
  binding, firewall and exact port/path. A reachable TCP port alone is not
  sufficient: it must return an RTSP video description.
* **Authentication failed:** use the bridge's RTSP credentials, not your
  Momcozy email/password. This integration's setup probe supports Basic auth,
  matching this repository's bridge. Arbitrary Digest-only servers are not
  supported by the probe.
* **Bridge goes offline:** HA retries setup when the initial connection fails.
  After setup, entity availability means the configuration is loaded, not that
  live camera health is confirmed. Playback errors appear in the media player.
  No continuous availability polling runs; reload the integration to repeat
  connection validation.
* **JPEG works, browser video does not:** BM04 commonly supplies H.265/HEVC.
  Frontend playback depends on browser/device codec support. This integration
  does not transcode HEVC to H.264. A separate compatible transcoder is needed
  for clients that cannot play the source codec. Do not interpret a successful
  configuration handshake as proof of browser playback or audio compatibility.
* **Expired cloud session:** refresh the session with the desktop tooling and
  restart the bridge. HACS cannot refresh Momcozy credentials.

Integration diagnostics contain only the entry version, TCP transport and a
boolean indicating whether authentication is configured. They omit connection
details, camera images and credentials. Home Assistant stores RTSP credentials
in its config entry; protect HA backups. FFmpeg/stream debug logs may include
authenticated source URLs, so redact them before sharing.

## Optional audio conversion for Home Assistant

BM04 cameras supply G.711 audio. Home Assistant's standard
[stream player accepts AAC/MP3, not G.711](https://www.home-assistant.io/integrations/stream/).
With bridge version **0.1.2 or newer**, enable AAC separately for each camera by
adding these keys to its existing `bridge-N.private.json` on the bridge computer:

```json
{
  "audio-format": "aac",
  "ffmpeg-path": "C:\\Tools\\ffmpeg\\bin\\ffmpeg.exe"
}
```

Use **0.1.2 or newer** for BM04: it corrects the distinction between the
camera's 16 kHz audio samples and its 8 kHz RTP clock. Version 0.1.1 could
discard valid audio packets and cause clicking. Conversion does not remove
background noise already present at the microphone.

Merge these two keys into the existing object; do not replace the camera's
credentials or other settings. Use an absolute executable path, especially when
running the desktop supervisor, whose child working directory is private runtime
storage. On Linux/macOS use e.g. `/usr/bin/ffmpeg` or the absolute path reported by
`command -v ffmpeg`. Install FFmpeg separately on the **bridge computer**, not HA:
Windows builds are linked from [FFmpeg downloads](https://ffmpeg.org/download.html);
Ubuntu/Debian: `sudo apt install ffmpeg`; macOS with Homebrew: `brew install ffmpeg`.
FFmpeg is optional and is not bundled or automatically downloaded by the bridge.

Restart the bridge, then close and reopen the HA live view (or reload its Momcozy
entry if it retains the old stream). The RTSP address and HA configuration stay
the same. Unmute the HA player; browsers commonly start playback muted.

| Setting | Behavior |
| --- | --- |
| `"audio-format": "copy"` (default, also when omitted) | Original G.711 audio, suitable for VLC; no FFmpeg process |
| `"audio-format": "aac"` | G.711 PCMA/PCMU → AAC-LC, 16 kHz mono, 32 kbit/s for HA |
| `"ffmpeg-path"` | FFmpeg executable; defaults to `ffmpeg` on PATH |

Direct CLI use also accepts `--audio-format aac --ffmpeg-path /absolute/path/ffmpeg`.
Only camera audio is converted: H.264/H.265 video passes through unchanged, and
talkback retains its original codec. One FFmpeg subprocess runs per active
camera stream/resolution. Media is piped through memory without recordings;
FFmpeg receives no account or RTSP credentials. Missing FFmpeg or an unsupported
audio codec produces an error instead of silently claiming AAC support. Encoder
failure triggers the normal camera reconnection path. The conversion adds audio
buffering/CPU use and does not improve the source microphone quality.

Both cameras have been verified with live video and audible AAC in Home
Assistant using bridge 0.1.2. The HACS component remains version 0.1.0:
bridge releases and the Python integration have independent versions.

This setting belongs to the bridge configuration because encoding runs on that
computer. Updating HACS alone does not update the bridge executable.

## Implementation and verification

Runtime code is entirely under `custom_components/momcozy/`; no cloud SDK,
native library or executable is downloaded by the integration. The
[camera API](https://developers.home-assistant.io/docs/core/entity/camera/),
[config-flow API](https://developers.home-assistant.io/docs/core/integration/config_flow/)
and [HACS repository layout](https://hacs.xyz/docs/publish/integration/) are used.

Tests in `tests/home_assistant/` cover actual loopback RTSP handshakes, challenged
authentication, malformed/non-video responses, timeouts, config flow errors,
duplicate prevention, reconfiguration, setup/unload, TCP stream options and
diagnostic redaction. The HA harness mocks network/media calls; those tests do
not validate physical camera playback. `probe_bridge.py PRIVATE_CONFIG.json`
can check a running bridge without printing credentials, but also does not
decode video. End-to-end HA frontend validation must be recorded separately
from these protocol and lifecycle checks.

Run the protocol checks without installing HA:

```sh
python -m unittest discover -s tests/home_assistant -p test_rtsp.py -v
```

Run the HA tests on Linux with Python 3.14:

```sh
sudo apt-get install libturbojpeg ffmpeg
python -m pip install -r tests/home_assistant/requirements.txt
python -m pytest -o asyncio_mode=auto tests/home_assistant/test_integration.py
```

That harness pins Home Assistant 2026.9.1. The declared minimum follows the APIs
used by the component; a passing current-version test run is not a test of every
intervening HA release.
