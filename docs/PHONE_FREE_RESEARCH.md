# Setup without a connected Android phone

Research checked on 2026-09-08. Scope: the existing BM04 implementation and
public vendor documentation. No cameras were reset, re-paired, or moved to
another account during this investigation.

**A connected phone is not technically required for every installation.**
Existing private configuration or the user's own compatible APK files can
replace the USB extraction step. A fresh installation with only a Momcozy
email/password, no APK material and no previous configuration does **not** yet
have a verified end-to-end playback route.

## What actually needs Android material

There are two distinct authentication steps:

1. [Momcozy login](../client/momcozy_login.py) runs directly on the desktop.
   It hashes the password and calls the Momcozy account API, then obtains an
   OEM Tuya UID/token. This script does not read an APK or signing file.
2. [Tuya login](../client/tuya_login.py) calls the signed mobile API through
   [tuya_mobile.py](../client/tuya_mobile.py). That code needs the OEM app key
   and signing configuration to obtain the camera session and RTC metadata.

The current extractor derives that configuration from the package identity,
APK certificate, manifest metadata, security image and ARM64 native library.
It accepts the verified `com.lute.momcozy` version **3.3.0** only. This is a
constraint of this implementation, not proof that Android hardware is an
inherent requirement of the camera protocol. See [protocol evidence](PROTOCOL.md).

The phone has supplied the app files; it does not relay desktop video. Once
configured, the bridge performs cloud authentication/signaling itself. Cloud
access remains necessary in the verified implementation.

## Routes and current evidence

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

The official app listing identifies the Android distribution. This research
did not establish a vendor-hosted direct download of the exact base/ARM64 APK
pair supported by the extractor. An APK import therefore means files the user
already possesses; it is not an automatic promise to fetch them from an
unverified mirror.
[Momcozy on Google Play](https://play.google.com/store/apps/details?id=com.lute.momcozy)

These are bounded search findings, not a claim that no other vendor interface
can exist.

### Tuya QR login and account boundaries

The inherited [auth command](../bridge/cmd/auth/auth.go) advertises Tuya Smart /
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
