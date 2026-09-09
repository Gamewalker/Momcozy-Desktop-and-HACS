# Momcozy Bridge for Home Assistant

This app runs the Momcozy bridge on Home Assistant OS or a supervised Home Assistant installation. No permanently running Windows, Linux or macOS bridge computer is required.

## Install

1. Add `https://github.com/Gamewalker/Momcozy-Desktop-and-HACS` as an app repository in **Settings → Apps → App store → Repositories**.
2. Install **Momcozy Bridge**, enable automatic startup and start it.
3. Open its web UI and complete the camera setup.
4. Install this repository's **Momcozy Bridge** integration through HACS.
5. Add one integration entry per camera. Copy the Home Assistant host, port, path, RTSP username and password shown in the app web UI.

The default RTSP ports are `19554` through `19563`. If you change an external port on the app's Network page, enter that changed port in the HACS integration.

## First-time setup

The setup has two app sources:

- **Google Play:** click **App vorbereiten** and sign in directly to Google in the isolated browser shown inside the app. The temporary browser profile, cookies and internally exchanged credentials are discarded after the download.
- **Own APK files:** select and upload both the base APK and the matching ARM64 split APK. The files are validated locally and removed from the temporary upload afterward.

The Home Assistant IP or DNS name is prefilled from the address used to open the app. It remains editable, which is useful when Home Assistant was opened through an external URL.

Home Assistant does not support the camera's original audio codec. The app therefore selects AAC and uses its included FFmpeg to convert audio; video is passed through unchanged.

Momcozy sign-in requires an email address and password set directly on the Momcozy account. Google or Facebook sign-in is not supported.

## Security and backups

The setup page is reachable only through authenticated Home Assistant Ingress. Momcozy/Tuya session data and RTSP passwords are stored in the app's private `/data` volume and are included in Home Assistant app backups.

RTSP ports are exposed on the local Home Assistant host and protected with a generated username and password. Uploaded APKs are processed locally and are not retained as uploads. Do not forward RTSP ports to the internet.

## Limits

- Home Assistant OS or a supervised installation is required; Home Assistant Container and Core do not support apps.
- Up to ten cameras are exposed by the default network configuration.
- The app currently supports `amd64` and `aarch64` systems.
- Internet access remains necessary for Momcozy/Tuya authentication and stream negotiation.
