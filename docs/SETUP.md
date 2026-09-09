# Set up your cameras

## Before you start

- Pair the BM04 cameras with your Momcozy account in the official app.
- Have your Momcozy DE/EU login and Google account ready.
- Install Chrome, Edge, Chromium or Brave. For desktop playback, install [VLC](https://www.videolan.org/vlc/).
- [Download](https://github.com/Gamewalker/Momcozy-Desktop-and-HACS/releases/latest) and extract the complete package, including `setup-helper/`.

**Momcozy sign-in requires an email address and a password set for the Momcozy account. Google or Facebook sign-in is not supported.** The separate Google sign-in is used to download the app from Google Play.

## Setup assistant

1. Start `momcozy-desktop.exe` on Windows or `./momcozy-desktop` on Linux/macOS.
2. Select **Über Google Play anmelden und laden**.
3. Keep the default archive and fallback settings. Click **App vorbereiten** and complete the Google sign-in in the browser window.
4. Enter the email address and password of your Momcozy account.
5. Select **Auf diesem Desktop mit VLC** and **Kamera-Originalton · für VLC**. For HA, follow [Home Assistant](HOME_ASSISTANT.md).
6. Click **Kameras einrichten**, then **Kameras jetzt starten**.

Keep the program window open. Later, starting the executable opens your configured cameras.

## Reopen setup

Run from the extracted package folder:

- Windows: `.\momcozy-desktop.exe setup`
- Linux/macOS: `./momcozy-desktop setup`

For a separate installation, choose an empty **Privater Zielordner**. As an alternative to Google Play, the assistant can upload a matching base APK and ARM64 APK directly.

## Quick fixes

| Problem | Action |
| --- | --- |
| Google sign-in fails | Retry **App vorbereiten** and finish signing in within four minutes. |
| Setup helper missing | Extract the complete download again. |
| VLC does not open | Install VLC and restart the desktop program. |
| Session expired | Reopen setup, create a fresh configuration in an empty target folder and start it. |

[Start and update](BINARIES.md) · [Archive](archive/README.md)
