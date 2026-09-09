# Home Assistant app and HACS

Add each BM04 as a camera in Home Assistant, with live video and sound.

**You need:** Home Assistant 2025.6+ on Home Assistant OS or a supervised installation, plus HACS. The bridge runs as a Home Assistant app, so no additional always-on computer is required.

Momcozy setup requires an email address and a password set for your Momcozy account. Google or Facebook sign-in is not supported.

## 1. Install the Home Assistant app

1. Open **Settings → Apps → App store → Repositories**.
2. Add `https://github.com/Gamewalker/Momcozy-Desktop-and-HACS`.
3. Install **Momcozy Bridge**, enable automatic startup and start it.
4. Open the app web UI and complete the camera setup. FFmpeg and ADB are included.
5. Enter the LAN IP of the Home Assistant machine when requested, then click **Kameras einrichten → Bridge jetzt starten**.

The result lists each camera's host, port, stream path and generated RTSP credentials. These local credentials are shown through authenticated Home Assistant Ingress; Momcozy/Tuya cloud secrets are not displayed.

For initial app preparation, connect an Android phone by USB to the Home Assistant machine and approve USB debugging. Alternatively, put your own APKs or an existing private configuration in the app configuration folder and use `/config/...` paths in the setup UI. Google Play setup inside the container requires your own AAS token because it cannot open a desktop browser.

## 2. Install through HACS

1. Open **HACS → ⋮ → Custom repositories**.
2. Add `https://github.com/Gamewalker/Momcozy-Desktop-and-HACS`, category **Integration**.
3. Download **Momcozy Desktop and HACS**, then restart Home Assistant.
4. Open **Settings → Devices & services → Add integration → Momcozy Bridge**.
5. Enter the connection details from the bridge setup:

| Field | Value |
| --- | --- |
| Name | A name for this camera |
| Bridge host | LAN IP of the Home Assistant machine |
| RTSP port | This camera's port, e.g. `19554` |
| Stream path | This camera's path, e.g. `bm04_1` |
| RTSP username / password | Values shown for this camera in the app web UI |

Repeat **Add integration** for each camera. Open the camera entity and unmute the player.

The app restarts the bridge automatically after a Home Assistant reboot. Reopen its web UI at any time to review the local RTSP connection details. The default exposed ports are `19554` through `19563`; changed external ports must also be changed in the integration entry.

## Existing external bridge

The previous Windows/Linux/macOS bridge setup remains supported. If you intentionally keep it, add the HACS integration using that computer's LAN IP and the details from its private configuration files. New Home Assistant OS or supervised installations should use the app above.

## Quick fixes

- **Connection fails:** check the app log, Home Assistant LAN IP, app Network port and stream path.
- **Login rejected:** reopen the app web UI and copy that camera's RTSP credentials again.
- **No sound:** restart the app and unmute the HA player; the app configures AAC and includes FFmpeg.
- **Still image but no live video:** use a browser/device with HEVC playback support.

Home Assistant Container and Core installations cannot run apps. In that case, continue using the external bridge instructions in [setup](SETUP.md).

[Bridge updates](BINARIES.md#update) · [Archive](archive/README.md)
