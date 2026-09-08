# Home Assistant / HACS

Add each BM04 as a camera in Home Assistant, with live video and sound.

**You need:** Home Assistant 2025.6+, HACS and a Windows, Linux or macOS computer running the Momcozy bridge. Keep that computer running and awake.

## 1. Configure the bridge

1. Install [FFmpeg](https://ffmpeg.org/download.html) on the bridge computer and complete [setup](SETUP.md) through the Momcozy login step.
2. Select **In Home Assistant** and enter the **LAN-IP dieses Rechners**.
3. Keep **AAC für Home Assistant** selected. Enter the full FFmpeg executable path if it is not on PATH.
4. Click **Kameras einrichten → Kameras jetzt starten**.
5. Allow TCP access from Home Assistant to the displayed ports in the bridge computer's firewall. Defaults: `19554`, `19555`, …

The result lists each camera's host, port, stream path and private configuration file. The file contains `rtsp-user` and `rtsp-password` for the next step.

## 2. Install through HACS

1. Open **HACS → ⋮ → Custom repositories**.
2. Add `https://github.com/Gamewalker/Momcozy-Desktop-and-HACS`, category **Integration**.
3. Download **Momcozy Desktop and HACS**, then restart Home Assistant.
4. Open **Settings → Devices & services → Add integration → Momcozy Bridge**.
5. Enter the connection details from the bridge setup:

| Field | Value |
| --- | --- |
| Name | A name for this camera |
| Bridge host | LAN IP of the bridge computer |
| RTSP port | This camera's port, e.g. `19554` |
| Stream path | This camera's path, e.g. `bm04_1` |
| RTSP username / password | `rtsp-user` / `rtsp-password` from its private configuration file |

Repeat **Add integration** for each camera. Open the camera entity and unmute the player.

## Start again

Run from the extracted package folder, using the configuration folder chosen during setup:

```powershell
# Windows
.\momcozy-desktop.exe desktop --no-player --data-dir "C:\Private\Momcozy"
```

```sh
# Linux/macOS
./momcozy-desktop desktop --no-player --data-dir "$HOME/Private/Momcozy"
```

## Quick fixes

- **Connection fails:** check the running bridge, LAN IP, firewall, port and stream path.
- **Login rejected:** copy the RTSP credentials from that camera's private file.
- **No sound:** select AAC, check FFmpeg on the bridge computer, restart the bridge and unmute the HA player.
- **Still image but no live video:** use a browser/device with HEVC playback support.

[Bridge updates](BINARIES.md#update) · [Archive](archive/README.md)
