# Desktop: download, start and update

[Download the latest package](https://github.com/Gamewalker/Momcozy-Desktop-and-HACS/releases/latest) and extract the entire archive.

| Computer | Package name ends in |
| --- | --- |
| Windows Intel/AMD 64-bit | `windows-amd64.zip` |
| Linux Intel/AMD 64-bit | `linux-amd64.tar.gz` |
| Linux ARM64 | `linux-arm64.tar.gz` |
| macOS Intel | `darwin-amd64.tar.gz` |
| macOS Apple Silicon | `darwin-arm64.tar.gz` |

## First start

Install [VLC](https://www.videolan.org/vlc/) and Chrome, Edge, Chromium or Brave. Have your Google account and Momcozy DE/EU login ready; cameras must already be paired in the Momcozy app.

**Momcozy sign-in requires an email address and a password set for the Momcozy account. Google or Facebook sign-in is not supported.** The separate Google sign-in is used to download the app from Google Play.

- **Windows:** double-click `momcozy-desktop.exe`.
- **Linux/macOS:** open a terminal in the extracted folder and run `./momcozy-desktop`.

In the [setup assistant](SETUP.md), select **Über Google Play anmelden und laden**, sign in to Google, then enter your Momcozy login. Choose desktop playback and click **Kameras einrichten → Kameras jetzt starten**.

On macOS, allow the downloaded app under **System Settings → Privacy & Security** if prompted.

## Daily use

Start the executable again to open your cameras in VLC. Use **Kamera-Originalton · für VLC** for sound. Keep the program window open; **Ctrl+C** stops the bridge.

Default configuration folder: `%USERPROFILE%\.momcozy-desktop` on Windows; `~/.momcozy-desktop` on Linux/macOS.

For a custom folder:

```powershell
# Windows
.\momcozy-desktop.exe desktop --data-dir "C:\Private\Momcozy"
```

```sh
# Linux/macOS
./momcozy-desktop desktop --data-dir "$HOME/Private/Momcozy"
```

## Update

1. Stop the running bridge with **Ctrl+C** and close VLC.
2. Download and extract the complete new package into a new folder.
3. Start the new executable. Keep using your existing configuration folder; update any shortcut to the new executable.

[Home Assistant](HOME_ASSISTANT.md) · [Deutsch](DESKTOP-DE.md) · [Archive](archive/README.md)
