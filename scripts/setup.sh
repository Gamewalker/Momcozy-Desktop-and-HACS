#!/usr/bin/env bash
set -euo pipefail
umask 077
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
case "$(uname -s)" in
  Linux|Darwin) ;;
  *) echo 'This setup script supports Linux and macOS.' >&2; exit 1 ;;
esac
command -v python3 >/dev/null || { echo 'Install Python 3.11+ first.' >&2; exit 1; }
command -v go >/dev/null || { echo 'Install Go 1.26.2+ first.' >&2; exit 1; }
python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3,11) else "Python 3.11+ required")'
python3 -m venv "$ROOT/.venv"
"$ROOT/.venv/bin/python" -m pip install -r "$ROOT/requirements.txt"
mkdir -p "$ROOT/bin"
go -C "$ROOT/bridge" build -o "$ROOT/bin/momcozy-bridge" .
echo 'Build complete. Prepare your APK/account as described in README.md, then run scripts/watch.sh.'
