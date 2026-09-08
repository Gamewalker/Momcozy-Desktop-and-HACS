# Contributing

Keep desktop launch code in `client/` and `scripts/`, media/signaling code in
`bridge/`, and the future Home Assistant integration in
`custom_components/momcozy/`. Read `docs/HOME_ASSISTANT.md` before adding HACS
metadata or integration dependencies.

Run `go test ./...` from `bridge/` and
`python -m unittest discover -s tests/client -v` from the root. Check shell
syntax with `bash -n scripts/setup.sh` and `bash -n scripts/watch.sh`.

Use synthetic fixtures. Never commit APKs, vendor binaries, account credentials,
private JSON state, device identifiers, captured media or raw signaling logs.
Retain upstream MIT notices. Distinguish native execution from cross-builds in
test reports. Add HACS integration tests under `tests/home_assistant/` when that
component is implemented.
