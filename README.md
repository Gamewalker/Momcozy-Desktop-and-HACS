# Momcozy Desktop and HACS

Watch your Momcozy BM04 cameras with video and sound on Windows, Linux, macOS or Home Assistant.

**[Download](https://github.com/Gamewalker/Momcozy-Desktop-and-HACS/releases/latest)** · [Deutsch](docs/DESKTOP-DE.md) · [Home Assistant](docs/HOME_ASSISTANT.md)

## Get started

You need a BM04 already paired in the Momcozy app, your Momcozy DE/EU login, a Google account, [VLC](https://www.videolan.org/vlc/) and Chrome, Edge, Chromium or Brave.

1. Download the package for your computer and extract the entire archive.
2. **Windows:** double-click `momcozy-desktop.exe`. **Linux/macOS:** run `./momcozy-desktop` in the extracted folder.
3. In the setup assistant, select **Von Google Play herunterladen · ohne Android-Gerät**. Click **App vorbereiten** and sign in to Google.
4. Enter your Momcozy login. Choose **Auf diesem Desktop mit VLC**, then **Kameras einrichten**.
5. Click **Kameras jetzt starten**. Keep the program window open during playback.

Use **Originalton beibehalten** for desktop sound. The assistant saves a working app version locally for automatic fallback.

## Home Assistant

Choose **In Home Assistant** during setup, enable AAC and install the integration through HACS. Follow the [short HACS guide](docs/HOME_ASSISTANT.md).

The bridge computer stays running during playback. An internet connection is required for camera login and connection setup.

[Setup details](docs/SETUP.md) · [Start and update](docs/BINARIES.md) · [Archive](docs/archive/README.md) · [Contributing](CONTRIBUTING.md) · [Licenses](NOTICE.md)
