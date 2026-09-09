#!/bin/sh
set -eu

exec python3 /opt/momcozy/client/setup_wizard.py "$@"
