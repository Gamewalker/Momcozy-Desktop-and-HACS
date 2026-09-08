# Google Play download and local fallback (0.3.0)

Choose **Von Google Play herunterladen · ohne Android-Gerät** in the setup
assistant. The complete package bundles [goopdl 1.2.1](https://github.com/Villoh/goopdl)
as a library. No Android phone, emulator or separate downloader installation is
required. Google authentication and APK delivery remain unofficial interfaces
and may change or reject a particular account.

## Verified on 2026-09-08

- Desktop browser Google login and direct Play access succeeded.
- The current catalog offered **Momcozy 3.4.0, build 30402**. The base APK and
  ARM64 split were downloaded from Google and passed size/checksum checks.
- Local SDK extraction and fresh Momcozy/Tuya login succeeded. Both BM04 cameras
  produced decoded **1920x1080 video and audio** through the Windows bridge.
- A separate request for **3.3.0, build 30300** also downloaded that older app.
  The actual APK manifest confirmed 30300, and SDK preparation and camera
  configuration succeeded. Google's delivery metadata still reported 30402;
  the adapter therefore checks the downloaded manifest, not that unreliable
  protobuf field.
- Automated tests cover fallback selection, preservation of a working snapshot,
  checksum failures and retrying the SDK steps without repeating Momcozy login.

This proves historical delivery for that build/account at the test date. It is
not a promise that Google will keep serving older builds. Linux/macOS packages
receive build/runtime checks; real camera playback was tested on Windows.

## Setup

1. Open `momcozy-desktop setup` (Windows: the setup shortcut) and select the
   Google Play option. Choose a new private camera configuration folder.
2. Leave **In einem separaten Browserfenster anmelden** selected and click
   **App vorbereiten**. Chrome, Edge, Chromium or Brave must be installed.
3. Sign in directly on Google's page in the temporary browser profile and
   complete Google's consent within four minutes. Prefer a separate Google
   account. The helper registers a simulated ARM64 device for Play downloads.
4. The helper obtains the Google tokens, downloads the latest Momcozy base/ARM64
   APKs, validates them and attempts local SDK extraction. New app versions are
   not excluded by a fixed allowlist. An incompatible SDK must still fail.
5. Enter your **Momcozy** account in step 2 and finish desktop or HA bridge setup.
   Cameras must already be paired to that account in the official app; this may
   have been done on iPhone. Google login does not pair or move your cameras.

Advanced users may instead supply a Google email and AAS token. The token field
is not for a Google password. To request an older release, expand the build
option and enter its numeric version code, such as `30300`. Leave it empty for
latest. An unavailable or mismatched build is rejected.

## Saved working version

**Privates App-Archiv** defaults to `app-cache` inside the initial configuration
folder. It stores local APKs, SDK signing data and SHA-256 checksums. Use the
**same archive path** when creating a new camera configuration in another
folder. Existing camera configurations are not overwritten by setup.

A prepared app is initially a candidate. Only after successful Tuya login,
camera metadata retrieval and configuration validation is it recorded as the
working snapshot. This automatic check validates authentication/configuration;
it does not itself decode a live stream. The 3.4.0 live test above additionally
verified video and audio.

With fallback enabled, a failed Play download/extraction or subsequent SDK
login/metadata step uses the saved working signing data. SDK fallback reuses
the already successful Momcozy login and assigns a fresh device identity so
another running bridge is not displaced. Momcozy password failures are not
retried as SDK failures. The UI reports when a fallback was used.

Choose **Gespeicherte funktionierende App-Version** to use the archive directly
without Google login. Fallback is available only after a successful version has
been saved; it cannot create a backup on a first failed installation. New
candidates do not replace the known-good pointer until validation succeeds.
Snapshots are retained locally, including the previous working pointer, and
are never included in GitHub releases. The archive can occupy several hundred
megabytes per attempt; it is not an automatic background updater.

## Data handling

Google credentials/tokens are used in memory for one normal helper invocation,
never returned to the UI or stored in camera configuration. No shared token
service or goopdl account cache is used. The temporary browser profile is separate
from your normal browser and removed after ordinary completion/cancellation.
For development tests only, the owner explicitly authorized a short-lived Play
token cache in a protected local test directory; that facility is not bundled.

HTTPS download hosts and redirects are checked, including Google's `gvt1.com`
CDN. Cross-host redirects drop delivery cookies. APK bytes must match Google's
declared size and SHA-256 (or SHA-1 if SHA-256 is absent). Base/split package,
version code and certificate identities must agree, and the ARM64 library must
be present. Certificate identity matching is not an independent APK-signature
verification implementation.

The native library is interpreted with a bounded ARM64 emulator, not installed
or loaded as host code. Unsupported SDK layouts fail. The bridge uses the app
version recorded with its signing data, retaining 3.3.0 as the compatibility
default for old configuration files without version metadata.

Google login is only needed to download an app again; normal camera operation
uses Momcozy/Tuya. Keep APK archives, signing files and all tokens private.
