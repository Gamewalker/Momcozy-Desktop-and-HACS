> Archived guide. [Current setup](../SETUP.md).

# Setup without a connected Android phone

Research checked on 2026-09-08. Scope: the existing BM04 implementation and
public vendor documentation. Update: Google Play acquisition without Android
hardware is now verified; see [the 3.4.0 live test](GOOGLE_PLAY.md). No cameras were reset, re-paired, or moved to
another account during this investigation.

**A connected phone is not technically required for every installation.**
Existing private configuration or the user's own compatible APK files can
replace the USB extraction step. A fresh installation with only a Momcozy
email/password, no APK material and no previous configuration does **not** yet
have a verified end-to-end playback route.

## What actually needs Android material

There are two distinct authentication steps:

1. [Momcozy login](../../client/momcozy_login.py) runs directly on the desktop.
   It hashes the password and calls the Momcozy account API, then obtains an
   OEM Tuya UID/token. This script does not read an APK or signing file.
2. [Tuya login](../../client/tuya_login.py) calls the signed mobile API through
   [tuya_mobile.py](../../client/tuya_mobile.py). That code needs the OEM app key
   and signing configuration to obtain the camera session and RTC metadata.

The current extractor derives that configuration from the package identity,
APK certificate, manifest metadata, security image and ARM64 native library.
Version 0.3.0 attempts newer `com.lute.momcozy` builds, validates SDK extraction
and camera authentication, and retains a local working fallback. Both 3.3.0
and 3.4.0 have been tested. Android hardware is not an inherent requirement
of this client. See [protocol evidence](PROTOCOL.md).

The phone has supplied the app files; it does not relay desktop video. Once
configured, the bridge performs cloud authentication/signaling itself. Cloud
access remains necessary in the verified implementation.

## Routes and current evidence

The 0.3.0 setup assistant now implements direct Google Play acquisition
through goopdl with desktop browser authentication. See
[Google Play setup](GOOGLE_PLAY.md) for availability and validation status.
It eliminates Android hardware from acquisition while still using APK material.

| Route | Connected phone needed? | Status and remaining constraint |
| --- | --- | --- |
| Import own existing bridge configuration | No | Existing playback route. Import the camera manifest and its private bridge files; session expiry can still require login again. |
| Import own `signing.private.json`, then log in | No | Supported by the Python configuration pipeline. This permits a new account session without extracting the APK again. |
| Import own base and ARM64 APK files | No | Supported by `prepare_apk.py`; a compatible standalone APK can supply both inputs if it contains the ARM64 library. The 0.2.0 helper bundles the extraction runtime. |
| Automatically pull installed APKs over ADB | Once | Automates the proven acquisition route. USB authorization still requires the user's device confirmation. |
| Enter Momcozy email/password alone | No | Momcozy login exists; obtaining the subsequent signed Tuya session without app configuration is unresolved. |
| Tuya/Smart Life QR login | Normally yes, for scanning | Generic upstream code exists, but successful access to a Momcozy OEM account and BM04 has not been established. |
| Tuya Cloud OpenAPI/OAuth | Potentially | Official APIs exist, but authorization to this OEM account/device is not established. A new developer project alone is insufficient evidence. |
| First camera pairing entirely on desktop | Potentially | Not implemented or tested. Do not reset working cameras to try it during ordinary setup. |

Private configuration imports carry credentials and session tokens. They must
remain local and must not be attached to public issues or release archives.
Importing a configuration does not guarantee that its session is still valid.

## Live test: account credentials only (2026-09-08)

A fresh, isolated state directory was used with the account email/password.
No APK, extracted signing configuration, prior Tuya session, or existing bridge
configuration was supplied. Public protocol constants already present in the
client were retained; this tests an APK-free installation, not a protocol
implementation developed without prior reverse engineering.

| Step | Observed result |
| --- | --- |
| Fresh Momcozy login | Successful |
| Momcozy camera discovery | Two cameras returned |
| OEM account handoff | Returned `region`, `uid` and `token`; no SDK signing configuration |
| Tuya username-token request without SDK client ID/signature | Rejected with `ILLEGAL_CLIENT_ID` |
| Same request using the `appKey` returned by Momcozy camera discovery | Also rejected with `ILLEGAL_CLIENT_ID` |
| New Tuya camera session / decoded stream | Not reached |

The discovery response's `appKey` is therefore not an accepted substitute for
the SDK client ID in this tested request. Its name alone must not be treated
as proof that it replaces the extracted SDK parameters. Responses and account
material were kept private; the test did not reset or re-pair any camera and
did not change the working desktop or HA configurations.

This is a negative result for the tested direct mobile-API route, not proof
that every possible APK-free route is impossible. An alternative Momcozy token
exchange or authorized cloud integration remains unverified. Playback and
session-renewal tests require such an exchange to succeed first.

## Official alternatives examined

### Momcozy pairing and web access

Momcozy documents pairing the BM04 through its mobile app using a camera-scanned
QR code or AP mode. That QR code configures the camera's network/account; it is
not evidence of a browser login QR flow. The reviewed instructions do not
document a consumer desktop account API or desktop live-view login.
[BM04 pairing instructions](https://support.momcozy.com/article/48240293498393)

The official computer-transfer instructions concern files on a microSD card,
not live playback.
[Computer transfer instructions](https://support.momcozy.com/article/48235538327193)

### Manufacturer download: a route without Android hardware

Further inspection found a manufacturer-linked APK source. The
[Momcozy app page](https://momcozy.com/pages/app) links to `app.cozyinnov.com`.
That site's public JavaScript includes a
[download page](https://app.cozyinnov.com/app/download/zh?s=inner) and an
[international APK download](https://lute-public-prod.oss-cn-shenzhen.aliyuncs.com/software/app-package/momcozy-release-oversea.apk).
The international URL is present in the download page's public component
`/_nuxt/CgnUxJ6d.js` as `apkOversea`; it was not guessed or obtained from a
third-party APK mirror.

This is a promising acquisition route for people who have never owned an
Android phone. It still uses Android app material locally on the computer;
it would not require installing Android or running an emulator. The existing
setup assistant can accept one standalone APK in both APK fields **if** it is
version 3.3.0 and contains the required ARM64 library.

**Not yet verified end to end:** the storage host resolved, but HTTPS download
attempts from the test computer timed out before receiving a response on
2026-09-08. No APK was downloaded. Its version, signing certificate, ARM64
contents and successful session creation therefore remain unverified. The URL
is mutable and must not be advertised as a verified 3.3.0 package. Keep the
extractor's compatibility checks; do not change a version label to bypass them.
Automatic manufacturer download is not included in release 0.2.0.

Momcozy also distributes an
[iPhone app](https://apps.apple.com/us/app/momcozy/id6473000053), but this project
has not implemented an iOS app-data extraction or iOS-based desktop login path.
Existing camera pairing through iOS and acquiring desktop signing parameters
are separate questions.

These are bounded search findings, not a claim that no other vendor interface
can exist.

### Additional APK-free web-session test

Using only the fresh Momcozy-issued OEM UID/token, the EU Tuya web endpoint
`POST /api/login/token` accepted `isUid: true` and returned a login token and
RSA public-key fields without mobile SDK signing parameters. A subsequent
request to the existing bridge's `/api/private/phone/login` endpoint using the
OEM UID and RSA-encrypted MD5 of the OEM token failed with
`LOGIN_TOKEN_FAILED`. Fetching a fresh token and submitting the login within
the same cookie session produced the same result.

This establishes token issuance, **not** an authenticated camera session. The
phone login endpoint may not support the Momcozy OEM UID flow. The public
website's JavaScript also uses `/api/password/login` with an interactive
verification result; that flow was not completed. `/api/login/exchange` in
the same JavaScript generates a QR image, so its name is not evidence of an
OEM-token exchange API. No new stream or session-renewal success is claimed.

### Tuya QR login and account boundaries

The inherited [auth command](../../bridge/cmd/auth/auth.go) advertises Tuya Smart /
Smart Life QR authentication against `protect-*.ismartlife.me`. Its existence
does not verify Momcozy compatibility. Momcozy's current working route obtains
an OEM UID/token from its own backend rather than passing the Momcozy email and
password directly to that web service.

Tuya's documented **Link Tuya App Account** procedure uses the SmartLife app to
scan and approve a QR code. **Link My App** covers an OEM/SDK app created by the
developer; Tuya additionally documents that the app and cloud project must
belong to the same IoT account. These flows do not establish that an ordinary
Momcozy customer can link the vendor's app to a new personal cloud project.
[Link Devices](https://developer.tuya.com/en/docs/iot/link-devices?id=Ka471nu1sfmkl),
[Cloud project prerequisites](https://developer.tuya.com/en/docs/im-project-services/Cloud-self-development?id=Kb3o4z4ll4v9d)

Consequently, do not recommend SmartLife migration or QR login as a working
shortcut until device access is demonstrated without disrupting the existing
Momcozy pairing.

### Official cloud streaming

Tuya documents cloud RTSP allocation at
`POST /v1.0/users/{uid}/devices/{device_id}/stream/actions/allocate`, including
cloud project credentials and an OAuth authorization option. This is a
potential replacement for the mobile API only after the project is authorized
for the actual camera and successful playback is verified. Documentation of
the endpoint alone does not establish BM04 availability, entitlement, pricing,
or Momcozy account compatibility.
[Tuya RTSP API](https://developer.tuya.com/en/docs/iot/rtsp?id=Kacsdjcqllyql)

## Implementation direction

The setup assistant offers **existing private configuration**, **own APK
files**, and **connected Android device** as acquisition choices. It reuses the
same desktop login/discovery path after app parameters are available. This
removes manual commands without depending on an unproven account migration.

A fully APK-free route needs a separate proof: documented vendor authorization
or a verified desktop token exchange that obtains usable RTC/MQTT credentials
for an already paired BM04. Success means account login, camera discovery and
decoded video/audio, followed by a session-renewal check. A successful login or
device list alone is insufficient.

No evidence from this investigation justifies shipping extracted SDK material
as a universal solution. The technical issue is that it is tied to the OEM app
identity/version and can change; this document makes no legal determination
about redistribution. No extracted keys or customer credentials are included.
