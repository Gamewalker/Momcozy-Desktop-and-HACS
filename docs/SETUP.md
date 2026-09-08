# Setup assistant (0.2.0)

The assistant configures the desktop bridge through a browser page on your
computer. The complete package includes `setup-helper/` and its Python runtime;
you do not install Python or run the preparation scripts manually. This feature
is new for 0.2.0 and is not included in 0.1.x releases. Native helper packages
for five platforms are undergoing build and runtime validation.

## First start

1. Download the package for your operating system and architecture. Extract
   every file, including `setup-helper/` and `_internal/`; keep them together.
2. Install VLC for desktop viewing. Install FFmpeg separately if you want AAC
   audio conversion, including sound through Home Assistant.
3. On Windows, double-click `momcozy-desktop.exe`. With no camera configuration,
   the local setup page opens. On Linux/macOS run `./momcozy-desktop` from the
   extracted directory. To open setup explicitly, run `momcozy-desktop setup`
   (or `./momcozy-desktop setup` on Linux/macOS).
4. Select how to supply your own app parameters or camera configuration.
5. For a new session, enter your Momcozy account details and let the assistant
   discover the cameras already paired to that account.
6. Choose desktop playback or Home Assistant, complete configuration, then
   start the bridge.

The page uses localhost and a temporary access token. Keep its address private.
Credentials go to the local helper and the respective Momcozy/Tuya login
services, not to GitHub. The assistant does not create a new Momcozy account or
pair a factory-new camera; do that in the official app first. The verified
account flow currently covers DE/EU accounts.

## Choose an input

| Input | What to provide |
| --- | --- |
| Connected Android phone | Momcozy app 3.3.0 installed, USB debugging enabled and the computer authorized on the phone. Use the assistant's official Android Platform Tools download option if ADB is missing. |
| Own APK files | Base APK and ARM64 split for `com.lute.momcozy` 3.3.0. A standalone APK containing the ARM64 library may serve as both files. No phone connection needed. |
| Own signing configuration | `signing.private.json` from your previous preparation, followed by account login. No APK extraction needed. |
| Own camera configuration | The private camera configuration from your existing installation. No fresh login is needed while the stored session remains valid. |

APK extraction is local and version-specific. The package contains no APKs or
extracted OEM keys. It does not download APKs from third-party mirrors. There is
no proxy or Android root requirement. Existing-camera import does not make
expired sessions valid again.

## Desktop and Home Assistant

Desktop mode prepares loopback RTSP endpoints and opens VLC. Home Assistant mode
needs an address of the bridge computer reachable from HA, separate RTSP
credentials and an appropriate firewall rule. The assistant prepares bridge
configuration; HACS installation and adding the cameras in HA remain separate
steps. See [Home Assistant instructions](HOME_ASSISTANT.md).

Select AAC for HA sound and supply the FFmpeg executable path. FFmpeg is not
bundled; video is passed through unchanged. Original audio (`copy`) needs no
FFmpeg but is not the supported HA audio path. The bridge computer must remain
running and awake. Setup does not install an automatic service.

## If setup cannot complete

- Missing helper: extract the whole complete package again, or use the source
  instructions below. Copying the main executable alone is insufficient.
- Android authorization: unlock the phone and accept its USB debugging prompt.
- Unsupported app version: only 3.3.0 is verified; use your own compatible files
  or a previous private signing configuration.
- Existing configuration: use another private data directory for an independent
  installation; do not overwrite a working HA bridge accidentally.
- Native runtime failure: use the source workflow and report the platform and
  error message without credentials, APKs, private JSON or camera images.

The existing [source setup guide](DESKTOP-DE.md) remains available. For the
difference between using no connected phone and having no app material at all,
see [phone-free research](PHONE_FREE_RESEARCH.md). A fully APK-free
email/password-only camera session is not yet verified.
