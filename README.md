# Momcozy Desktop and HACS

Watch your Momcozy BM04 cameras with video and sound on Windows, Linux, macOS or Home Assistant.

**[Download](https://github.com/Gamewalker/Momcozy-Desktop-and-HACS/releases/latest)** · [Deutsch](docs/DESKTOP-DE.md) · [Home Assistant](docs/HOME_ASSISTANT.md)

## Get started

You need a BM04 already paired in the Momcozy app, your Momcozy DE/EU login, a Google account, [VLC](https://www.videolan.org/vlc/) and Chrome, Edge, Chromium or Brave.

**Momcozy sign-in requires an email address and a password set for the Momcozy account. Google or Facebook sign-in is not supported.** The separate Google sign-in is used to download the app from Google Play.

1. Download the package for your computer and extract the entire archive.
2. **Windows:** double-click `momcozy-desktop.exe`. **Linux/macOS:** run `./momcozy-desktop` in the extracted folder.
3. In the setup assistant, select **Über Google Play anmelden und laden**. Click **App vorbereiten** and sign in to Google.
4. Enter your Momcozy login. Choose **Auf diesem Desktop mit VLC**, then **Kameras einrichten**.
5. Click **Kameras jetzt starten**. Keep the program window open during playback.

Use **Kamera-Originalton · für VLC** for desktop sound. Home Assistant uses AAC because it does not support the camera's original audio codec.

## Home Assistant

Install the **Momcozy Bridge** app from this repository, complete setup in its Home Assistant web UI and install the camera integration through HACS. The bridge then runs directly on the Home Assistant system; no additional always-on computer is needed. Use these links in order or follow the [Home Assistant guide](docs/HOME_ASSISTANT.md).

1. Add the Momcozy app repository:

   [![Open your Home Assistant instance and show the add app repository dialog with a specific repository URL pre-filled.](https://my.home-assistant.io/badges/supervisor_add_addon_repository.svg)](https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2FGamewalker%2FMomcozy-Desktop-and-HACS)

2. Install and open the Momcozy Bridge app:

   [![Open your Home Assistant instance and show the dashboard of an app.](https://my.home-assistant.io/badges/supervisor_addon.svg)](https://my.home-assistant.io/redirect/supervisor_addon/?addon=4bb1db59_momcozy_bridge&repository_url=https%3A%2F%2Fgithub.com%2FGamewalker%2FMomcozy-Desktop-and-HACS)

3. Start the app and open its setup wizard:

   [![Open your Home Assistant instance and open the ingress URL of an app.](https://my.home-assistant.io/badges/supervisor_ingress.svg)](https://my.home-assistant.io/redirect/supervisor_ingress/?addon=4bb1db59_momcozy_bridge)

4. Add the camera integration to HACS:

   [![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Gamewalker&repository=Momcozy-Desktop-and-HACS&category=integration)

5. After the HACS download and Home Assistant restart, add each camera:

   [![Open your Home Assistant instance and start setting up a new integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=momcozy)

An internet connection is required for camera login and connection setup.

[Setup details](docs/SETUP.md) · [Start and update](docs/BINARIES.md) · [Archive](docs/archive/README.md) · [Contributing](CONTRIBUTING.md) · [Licenses](NOTICE.md)
