#!/usr/bin/env bash
set -euo pipefail
umask 077
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ ! -x "$ROOT/.venv/bin/python" || ! -x "$ROOT/bin/momcozy-bridge" ]]; then
  echo 'Run scripts/setup.sh first.' >&2
  exit 1
fi
exec "$ROOT/.venv/bin/python" "$ROOT/client/watch.py" "$@"
