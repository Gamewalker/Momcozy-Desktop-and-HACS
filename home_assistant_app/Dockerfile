# syntax=docker/dockerfile:1.7
FROM golang:1.26.2-bookworm@sha256:47ce5636e9936b2c5cbf708925578ef386b4f8872aec74a67bd13a627d242b19 AS bridge-builder

ARG TARGETARCH
WORKDIR /build/bridge
COPY bridge/go.mod bridge/go.sum ./
RUN go mod download
COPY bridge/ ./
RUN CGO_ENABLED=0 GOOS=linux GOARCH="${TARGETARCH:-amd64}" \
    go build -trimpath -ldflags="-s -w" -o /out/momcozy-bridge .

FROM python:3.12-slim-bookworm@sha256:782412e85d0f0984994c290652577d4018aff08145c85b262bb63dc0c7522254 AS novnc-assets

# noVNC is a static web client. Extract only its web files instead of installing
# the Debian meta package and its Node.js/NumPy service dependencies at runtime.
RUN apt-get update \
    && cd /tmp \
    && apt-get download novnc=1:1.3.0-1 \
    && mkdir -p /assets \
    && dpkg-deb --extract /tmp/novnc_*.deb /assets

FROM python:3.12-slim-bookworm@sha256:782412e85d0f0984994c290652577d4018aff08145c85b262bb63dc0c7522254

ARG BUILD_VERSION=dev
ARG BUILD_ARCH=aarch64|amd64
LABEL io.hass.version="${BUILD_VERSION}" \
      io.hass.type="app" \
      io.hass.arch="${BUILD_ARCH}" \
      org.opencontainers.image.title="Home Assistant App: Momcozy Bridge" \
      org.opencontainers.image.source="https://github.com/Gamewalker/Momcozy-Desktop-and-HACS" \
      org.opencontainers.image.licenses="MIT"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update \
    && apt-get install --no-install-recommends --yes \
       ca-certificates chromium ffmpeg fonts-liberation x11vnc xvfb \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /opt/momcozy/requirements.txt
RUN python -m pip install --no-cache-dir --requirement /opt/momcozy/requirements.txt
# Optional websockify integrations pull in large scientific/cloud stacks. The
# basic localhost VNC-to-WebSocket bridge used here needs only the core package.
RUN python -m pip install --no-cache-dir --no-deps websockify==0.13.0

COPY client/ /opt/momcozy/client/
COPY LICENSE /opt/momcozy/licenses/project-LICENSE
COPY bridge/LICENSE /opt/momcozy/licenses/bridge-LICENSE
COPY NOTICE.md /opt/momcozy/licenses/NOTICE.md
COPY home_assistant_app/run.sh /usr/local/bin/momcozy-app
COPY home_assistant_app/oauth-browser.sh /usr/local/bin/momcozy-oauth-browser
COPY home_assistant_app/setup-helper.sh /usr/local/lib/momcozy/setup-helper
COPY --from=bridge-builder /out/momcozy-bridge /usr/local/bin/momcozy-bridge
COPY --from=novnc-assets /assets/usr/share/novnc /usr/share/novnc
RUN chmod 0755 /usr/local/bin/momcozy-app /usr/local/bin/momcozy-bridge \
    /usr/local/bin/momcozy-oauth-browser /usr/local/lib/momcozy/setup-helper

EXPOSE 8099 19554 19555 19556 19557 19558 19559 19560 19561 19562 19563
CMD ["/usr/local/bin/momcozy-app"]
