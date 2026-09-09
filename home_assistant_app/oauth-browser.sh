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
  --single-process \
  --no-zygote \
  --js-flags=--max-old-space-size=64 \
  --mute-audio \
  --window-size=1024,640 \
  --disable-features=Translate \
  --app=https://accounts.google.com/EmbeddedSetup \
  "$@"
