# Google Play download without an Android device

The development version adds **Von Google Play herunterladen · ohne
Android-Gerät** to the local setup assistant. This is not included in the
published 0.2.0 packages. It uses [goopdl 1.2.1](https://github.com/Villoh/goopdl)
as a Python library, included in newly built complete native packages.

This route is experimental until a real Google login, APK download and camera
session have all been verified. Automated tests cover the adapter and failures;
they do not establish Google account acceptance. Google may reject unofficial
clients, limit requests or offer an unsupported app version.

## Setup

1. Start the development package's setup assistant and choose the Google Play
   option in step 1. Choose a new private configuration folder.
2. Leave **In einem separaten Browserfenster anmelden** selected and click
   **App vorbereiten**. Chrome, Edge, Chromium or Brave must be installed.
3. Sign in directly on Google's page in the newly opened temporary browser
   profile and complete Google's consent. Prefer a separate Google account.
   This registers a simulated ARM64 Play device for downloading; no Android
   installation or phone is needed. The sign-in window allows four minutes.
4. The helper takes the one-time Google OAuth token from that temporary profile,
   exchanges it for an AAS token and authenticates directly to Google Play.
   It requests `com.lute.momcozy`, then downloads the base APK and ARM64 split
   (or uses the base alone when it already contains the native library).
5. After successful local preparation, enter your **Momcozy** account in step 2
   and finish desktop or Home Assistant bridge setup normally.

The Google account and Momcozy account serve different purposes. This does not
pair new cameras or move an existing camera to Google. Cameras must already be
paired to the Momcozy account through the official app, including its iOS app
for iPhone owners.

Advanced users can select **Eigenes AAS-Token verwenden** and enter their Google
email and existing AAS token. This field is not for a Google password. Do not
post the token in issues, chats or shell commands.

## Data handling and validation

- Google authentication material is passed through private JSON stdin and used
  in memory for one helper invocation. It is not returned to the browser UI,
  written into camera configuration, or printed by goopdl's CLI.
- The temporary Google browser profile is separate from existing browser
  profiles and is removed after ordinary completion or cancellation. No
  shared account/token dispenser is used, and no `~/.config/goopdl` cache is
  created. The adapter ignores inherited `GOOPDL_ACCOUNT_EMAIL` / token values.
- Downloads use HTTPS Google hosts, including validation on redirects. Cookies
  are stripped on cross-host redirects. Downloaded bytes must match Play's
  declared size and SHA-256 (or SHA-1 when SHA-256 is absent).
- The base package and version must match **com.lute.momcozy 3.3.0**, and the
  ARM64 split must match its version code and contain the required native
  library. This is transport/digest and manifest validation, not an independent
  cryptographic APK-signature verifier.
- Downloaded files live in a protected temporary setup directory and are
  removed after processing. Only the private signing configuration is retained
  for the subsequent Momcozy login. Existing camera configurations are refused
  as a download-setup destination.

## Troubleshooting

If Google refuses the browser, authentication or a device profile, this version
reports the failure; it does not bypass a challenge or silently use somebody
else's account. You can retry later, provide your own AAS token, or use the
existing APK import option.

The adapter requests the previously verified version **3.3.0 / version code
30300**, even if the catalog advertises a newer release. Google may stop serving
that historical build. If it is unavailable or the delivered manifest differs,
setup stops. Do not rename an APK or disable the extractor's version check.

The normal camera bridge does not need the Google account after app preparation.
Google login is needed again only if you choose to download the app again.
