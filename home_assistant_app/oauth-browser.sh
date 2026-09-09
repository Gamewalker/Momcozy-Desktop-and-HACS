#!/bin/sh
set -eu

exec /usr/bin/chromium \
  --no-sandbox \
  --disable-dev-shm-usage \
  --disable-features=Translate \
  "$@"
