# Private state and reporting

This software provides access to your camera account. Keep the credentials
file and all files under `MOMCOZY_DATA_DIR` private. Do not attach state files,
APKs, signing parameters, MQTT/WebRTC messages, SDP or unredacted logs to issues.
The repository ignore rules are a guardrail, not encryption.

TLS verification remains enabled. Python requests do not use environment or
system proxies. The RTSP listener binds to 127.0.0.1; local processes can still
access the streams. There is no RTSP password because remote access is not
supported. Do not expose these ports to the Internet.

The launcher uses saved tokens; refresh is manual. A session file is a bearer
credential even if the account password does not appear in it. Playback may use
a Tuya relay depending on ICE connectivity. No claims of offline operation or
end-to-end exclusion of the cloud are made.

For a bug report include OS, Python/Go/VLC versions, camera/app firmware,
non-sensitive error codes and reproduction steps. Remove camera IDs, account
information, tokens, local keys and network addresses before publication.
