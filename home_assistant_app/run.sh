#!/bin/sh
set -eu

umask 077
mkdir -p /data/momcozy

export DISPLAY=:99
export GOOPDL_BROWSER=/usr/local/bin/momcozy-oauth-browser

Xvfb :99 -screen 0 1024x640x16 -nolisten tcp >/dev/null 2>&1 &
xvfb_pid=$!
x11vnc -loop -display :99 -forever -shared -nopw -localhost -rfbport 5900 >/dev/null 2>&1 &
vnc_pid=$!
websockify --web=/usr/share/novnc 127.0.0.1:6080 127.0.0.1:5900 >/dev/null 2>&1 &
websockify_pid=$!

cleanup() {
  if [ -n "${bridge_pid:-}" ]; then
    kill "$bridge_pid" 2>/dev/null || true
  fi
  kill "$websockify_pid" "$vnc_pid" "$xvfb_pid" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

/usr/local/bin/momcozy-bridge app \
  --data-dir /data/momcozy \
  --helper /usr/local/lib/momcozy/setup-helper \
  --listen 0.0.0.0:8099 &
bridge_pid=$!
wait "$bridge_pid"
