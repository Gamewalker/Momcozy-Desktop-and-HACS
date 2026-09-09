# Momcozy Bridge for Home Assistant

This app runs the Momcozy bridge on Home Assistant OS or a supervised Home Assistant installation. No permanently running Windows, Linux or macOS bridge computer is required.

## Install

1. Add `https://github.com/Gamewalker/Momcozy-Desktop-and-HACS` as an app repository in **Settings → Apps → App store → Repositories**.
2. Install **Momcozy Bridge**, enable automatic startup and start it.
3. Open its web UI and complete the camera setup.
4. Install this repository's **Momcozy Bridge** integration through HACS.
5. Add one integration entry per camera. Use the Home Assistant machine's LAN IP and copy the port, path, RTSP username and password shown in the app web UI.

The default RTSP ports are `19554` through `19563`. If you change an external port on the app's Network page, enter that changed port in the HACS integration.

## First-time setup

The simplest source is an Android phone connected by USB to the Home Assistant machine. Enable USB debugging, approve the Home Assistant host on the phone and leave the Momcozy app installed. ADB and FFmpeg are already included in the app image.

Other supported sources:

- Place your own base and ARM64 APK files in this app's configuration folder and use paths such as `/config/base.apk` and `/config/split_config.arm64_v8a.apk`.
- Place an existing private desktop configuration below `/config/import` and select **Vorhandene Kamerakonfiguration übernehmen**.
- Use Google Play with your own AAS token. Browser-based Google login cannot open a desktop browser from inside the Home Assistant container.

Momcozy sign-in requires an email address and password set directly on the Momcozy account. Google or Facebook sign-in is not supported.

## Security and backups

The setup page is reachable only through authenticated Home Assistant Ingress. Momcozy/Tuya session data and RTSP passwords are stored in the app's private `/data` volume and are included in Home Assistant app backups. The public `/config` mount is only used for files you deliberately import.

RTSP ports are exposed on the local Home Assistant host and protected with a generated username and password. Do not forward them to the internet.

## Limits

- Home Assistant OS or a supervised installation is required; Home Assistant Container and Core do not support apps.
- Up to ten cameras are exposed by the default network configuration.
- The app currently supports `amd64` and `aarch64` systems.
- Internet access remains necessary for Momcozy/Tuya authentication and stream negotiation.
