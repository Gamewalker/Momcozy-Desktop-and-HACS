#!/bin/sh
set -eu

exec /usr/bin/chromium \
  --no-sandbox \
  --disable-dev-shm-usage \
  --disable-gpu \
  --disable-extensions \
  --disable-background-networking \
  --disable-component-update \
  --disable-default-apps \
  --disable-sync \
  --renderer-process-limit=1 \
  --window-size=1024,640 \
  --disable-features=Translate \
  "$@"
