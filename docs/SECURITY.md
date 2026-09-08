# Private state and reporting

This software provides access to your camera account. Keep the credentials
file and all files under `MOMCOZY_DATA_DIR` private. Do not attach state files,
APKs, signing parameters, MQTT/WebRTC messages, SDP or unredacted logs to issues.
The repository ignore rules are a guardrail, not encryption.

Cloud TLS verification remains enabled. Python requests do not use environment
or system proxies. RTSP defaults to 127.0.0.1; local processes can access the
streams. An explicit non-loopback `listen-host` requires separate `rtsp-user`
and `rtsp-password` fields, with a password of at least 16 characters. LAN mode
supports RTSP over TCP only. Restrict firewall access to the Home Assistant host.
RTSP Basic authentication and media are not encrypted; use a trusted private LAN
or VPN. Do not expose these ports to the Internet. Raw RTSP headers and URLs are
not logged by this bridge.

The launcher uses saved tokens; refresh is manual. A session file is a bearer
credential even if the account password does not appear in it. Playback may use
a Tuya relay depending on ICE connectivity. No claims of offline operation or
end-to-end exclusion of the cloud are made.

For a bug report include OS, Python/Go/VLC versions, camera/app firmware,
non-sensitive error codes and reproduction steps. Remove camera IDs, account
information, tokens, local keys and network addresses before publication.
