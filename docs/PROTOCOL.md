# Protocol reconstruction

Observed with Momcozy BM04, firmware 25.01.08, Android package
`com.lute.momcozy` version 3.3.0 (30300), and an EU account. These observations
are version-specific, not a vendor API guarantee.

## Authentication

1. The application sends `POST /api/app/user/login/v3` to
   `https://app-api.mcozycloud.com`. Password preparation uses Argon2id v19,
   two iterations, 4096 KiB, parallelism 1, a 32-byte output and Base64 encoding.
   The fixed application salt and request fields are in `client/momcozy_login.py`.
2. The returned bearer token authenticates `/api/app/third/tuya/user`, which
   supplies the OEM region, UID and password token. Device discovery uses
   `/api/app/device/queryDevices`.
3. The Tuya SDK signing configuration combines the package name, SHA-256 APK
   signing-certificate fingerprint, embedded SDK key and manifest app secret.
   The embedded key comes from `assets/t_s.bmp`. Its native decoder is emulated
   locally from the user's ARM64 library with Unicorn; no Android root or proxy
   is needed. Neither APKs nor extracted secrets are distributed here.
4. Mobile API fields are sorted and joined with `||`. `postData` is reduced to
   its MD5 hex digest, with eight-character blocks reordered B-A-D-C, then the
   canonical request is authenticated with HMAC-SHA256. The separate `chKey`
   is also required. See `client/tuya_mobile.py`.
5. `thing.m.user.username.token.get` v2.0 returns an RSA public key and token.
   `thing.m.user.uid.password.login.reg` uses RSA PKCS#1 v1.5 encryption of the
   lowercase MD5 hex digest of the OEM password token. Its session is used for
   `tuya.m.device.get` and `smartlife.m.rtc.config.get`.

## Media

The bridge uses authenticated MQTT signaling to negotiate WebRTC. On the
tested BM04, H.265 RTP arrives through the `fmp4Stream` data channel. A codec,
start/frame, recv, complete exchange identifies the media SSRCs. The bridge
forwards media to loopback RTSP: H.265 payload type 96 and G.711 A-law payload
type 8. The native video frame timestamps must remain shared across fragments.

The RTSP description must contain the camera's actual codecs before the player
sets up its tracks. Sending RTP before the RTSP PLAY response can break client
negotiation. These two problems were reproduced and corrected.

Cloud authentication and signaling remain required. Whether ICE chooses a
direct route or relay depends on connectivity; this project does not establish
that the cameras can operate offline. A discovered Tuya local key is not an
RTSP password. Talkback is disabled by default.

## Evidence and limits

Two cameras simultaneously decoded at 1920×1080 with audio on Windows using
PyAV/FFmpeg and were played through VLC. Regression tests cover codec SDP,
waiting for PLAY, RTP payload mapping and preservation of fragment timestamps.
Long-running sessions, outages and session expiry need further testing.
Linux/macOS status is reported separately in the README; cross-compilation is
not evidence of live-camera playback on those systems.
