#!/bin/sh
set -eu

umask 077
mkdir -p /data/momcozy

exec /usr/local/bin/momcozy-bridge app \
  --data-dir /data/momcozy \
  --helper /usr/local/lib/momcozy/setup-helper \
  --listen 0.0.0.0:8099
