# Planned Home Assistant / HACS integration

**Status: structure reserved; no installable integration yet.**

The repository reserves exactly one integration directory:
`custom_components/momcozy/`. When implemented, its manifest, config flow,
camera platform, translations and all runtime integration code belong there.
The root `hacs.json` will be added with the first functional integration release.
This follows the [HACS integration repository requirements](https://www.hacs.xyz/docs/publish/integration/).

## Boundaries

| Path | Responsibility |
|---|---|
| `bridge/` | Go MQTT/WebRTC transport and RTSP output |
| `client/` | Desktop account preparation and playback supervision |
| `scripts/` | Desktop installation and launch entry points |
| `custom_components/momcozy/` | Future Home Assistant integration only |
| `tests/client/` | Desktop client tests |
| `tests/home_assistant/` | Future config-flow/entity tests |
| `docs/` | Protocol, desktop operation and integration design |

HACS installs the integration directory, not the root desktop client or Go
toolchain. The integration must not import Python files from `client/` or expect
`scripts/` to exist in a Home Assistant installation.

The proposed first integration connects to a separately running bridge and
exposes camera entities. Packaging the bridge as a Home Assistant add-on would
be a separate deliverable. A shared authentication library, if needed, should
become a versioned dependency rather than importing desktop scripts or copying
credentials into source files.

## Next implementation work

1. Define bridge lifecycle, authenticated access and camera discovery API.
2. Decide where the bridge runs. Today's desktop RTSP endpoints bind only to
   loopback and cannot be reached by another host. Remote exposure requires a
   deliberate authentication and transport design before changing that default.
3. Implement config flow, config-entry unload/reload, stable camera identifiers,
   availability and stream source handling without blocking Home Assistant's loop.
4. Store account/session data in appropriate private Home Assistant storage;
   redact diagnostics and avoid logging credentials or media signaling.
5. Add manifest, translations, integration tests, HACS metadata and validation.
6. Verify H.265 playback compatibility with the intended frontend and decide
   whether an optional transcoding service is needed.

No `manifest.json` or dummy component is supplied now: the reserved directory
must not be mistaken for a working Home Assistant integration.
