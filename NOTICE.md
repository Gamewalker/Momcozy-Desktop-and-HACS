# Source provenance

The `bridge/` directory is adapted from `thekoma/aventproxy`,
`avent-webrtc-bridge/`, snapshot d15a3117fdf8d0059f59cf451c9d8c0470e8a68a.
The original bridge includes the MIT notice copyright 2025 seydx; the upstream
repository's root MIT notice is also retained in this project's LICENSE.

BM04 adaptations:

- SDK app version and private JSON configuration input.
- Loopback-only RTSP listener and Windows/Unix socket handle separation.
- Load actual camera capabilities before generating SDP; select HD/SD correctly.
- Hold media until PLAY and remove invented RTP-Info values.
- Preserve camera video/audio timestamps and normalize RTP payload types.
- Skip H.264 parameter-set injection on H.265 streams.
- Process an incoming audio media track independently of video transport.
- Regression tests and local account/configuration scripts.

APK files, extracted SDK secrets, native vendor libraries, credentials, device
metadata and recordings are intentionally absent. Users prepare configuration
from their own installation. Python scripts implement the observed protocol;
they are not copied vendor application source.

Complete setup packages also include a Python runtime and open-source
preparation dependencies. Their notices and a version inventory are included
under `setup-helper/licenses/`; the Unicorn source archive corresponds to the
bundled, unmodified native library. These are separate from the proprietary
vendor libraries, which are read only from the user's own APK files.
