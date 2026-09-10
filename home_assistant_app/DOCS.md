# Momcozy Bridge for Home Assistant

This app runs the Momcozy bridge on Home Assistant OS or a supervised Home Assistant installation. No permanently running Windows, Linux or macOS bridge computer is required.

## Install

1. Add the Momcozy app repository:

   [![Open your Home Assistant instance and show the add app repository dialog with a specific repository URL pre-filled.](https://my.home-assistant.io/badges/supervisor_add_addon_repository.svg)](https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2FGamewalker%2FMomcozy-Desktop-and-HACS)

2. Open **Momcozy Bridge**, install it, enable automatic startup and start it:

   [![Open your Home Assistant instance and show the dashboard of an app.](https://my.home-assistant.io/badges/supervisor_addon.svg)](https://my.home-assistant.io/redirect/supervisor_addon/?addon=4bb1db59_momcozy_bridge&repository_url=https%3A%2F%2Fgithub.com%2FGamewalker%2FMomcozy-Desktop-and-HACS)

3. Open its web UI and complete the camera setup:

   [![Open your Home Assistant instance and open the ingress URL of an app.](https://my.home-assistant.io/badges/supervisor_ingress.svg)](https://my.home-assistant.io/redirect/supervisor_ingress/?addon=4bb1db59_momcozy_bridge)

4. Open this repository in HACS and download the **Momcozy Bridge** integration. Restart Home Assistant afterward:

   [![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Gamewalker&repository=Momcozy-Desktop-and-HACS&category=integration)

5. Add one integration entry per camera and copy the bridge host, port, path, RTSP username and password shown in the app web UI:

   [![Open your Home Assistant instance and start setting up a new integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=momcozy)

If a direct link does not work, add `https://github.com/Gamewalker/Momcozy-Desktop-and-HACS` manually under **Settings → Apps → App store → Repositories** and follow the same sequence from the app store.

The default RTSP ports are `19554` through `19563`. If you change an external port on the app's Network page, enter that changed port in the HACS integration.

## First-time setup

The setup has two app sources:

- **Google Play:** click **App vorbereiten** and sign in directly to Google in the isolated browser shown inside the app. The temporary browser profile, cookies and internally exchanged credentials are discarded after the download.
- **Own APK files:** select and upload both the base APK and the matching ARM64 split APK. The files are streamed through Home Assistant, validated locally and removed from the temporary upload afterward.

The **Bridge-Host** field defaults to `127.0.0.1`, which connects the integration to the app on the same Home Assistant system. It remains editable for a different network layout.

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
