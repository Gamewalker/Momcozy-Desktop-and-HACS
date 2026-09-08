# Contributing

Keep desktop launch code in `client/` and `scripts/`, media/signaling code in
`bridge/`, and the Home Assistant integration in
`custom_components/momcozy/`. Read `docs/HOME_ASSISTANT.md` before adding HACS
metadata or integration dependencies.

Run `go test ./...` from `bridge/` and
`python -m unittest discover -s tests/client -v` from the root. Check shell
syntax with `bash -n scripts/setup.sh` and `bash -n scripts/watch.sh`.

Use synthetic fixtures. Never commit APKs, vendor binaries, account credentials,
private JSON state, device identifiers, captured media or raw signaling logs.
Retain upstream MIT notices. Distinguish native execution from cross-builds in
test reports. HACS integration tests belong under `tests/home_assistant/` and run
in the Home Assistant integration test workflow. Run real loopback socket tests
separately from the HA test harness, which deliberately blocks network access.
