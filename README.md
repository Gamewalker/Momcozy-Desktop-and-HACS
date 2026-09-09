# Momcozy Desktop and HACS

Watch your Momcozy BM04 cameras with video and sound on Windows, Linux, macOS or Home Assistant.

**[Download](https://github.com/Gamewalker/Momcozy-Desktop-and-HACS/releases/latest)** · [Deutsch](docs/DESKTOP-DE.md) · [Home Assistant](docs/HOME_ASSISTANT.md)

## Get started

You need a BM04 already paired in the Momcozy app, your Momcozy DE/EU login, a Google account, [VLC](https://www.videolan.org/vlc/) and Chrome, Edge, Chromium or Brave.

**Momcozy sign-in requires an email address and a password set for the Momcozy account. Google or Facebook sign-in is not supported.** The separate Google sign-in is used to download the app from Google Play.

1. Download the package for your computer and extract the entire archive.
2. **Windows:** double-click `momcozy-desktop.exe`. **Linux/macOS:** run `./momcozy-desktop` in the extracted folder.
3. In the setup assistant, select **Von Google Play herunterladen · ohne Android-Gerät**. Click **App vorbereiten** and sign in to Google.
4. Enter your Momcozy login. Choose **Auf diesem Desktop mit VLC**, then **Kameras einrichten**.
5. Click **Kameras jetzt starten**. Keep the program window open during playback.

Use **Originalton beibehalten** for desktop sound. The assistant saves a working app version locally for automatic fallback.

## Home Assistant

Install the **Momcozy Bridge** app from this repository, complete setup in its Home Assistant web UI and install the camera integration through HACS. The bridge then runs directly on the Home Assistant system; no additional always-on computer is needed. Follow the [Home Assistant guide](docs/HOME_ASSISTANT.md).

An internet connection is required for camera login and connection setup.

[Setup details](docs/SETUP.md) · [Start and update](docs/BINARIES.md) · [Archive](docs/archive/README.md) · [Contributing](CONTRIBUTING.md) · [Licenses](NOTICE.md)
