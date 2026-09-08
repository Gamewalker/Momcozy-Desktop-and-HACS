"""Opt-in live RTSP handshake smoke check, without printing private config."""

import asyncio
import importlib.util
import json
import sys
from pathlib import Path


def main():
    if len(sys.argv) != 2:
        raise SystemExit(
            "Usage: python tests/home_assistant/probe_bridge.py PRIVATE_BRIDGE_CONFIG.json"
        )
    spec = importlib.util.spec_from_file_location(
        "momcozy_rtsp",
        Path(__file__).resolve().parents[2] / "custom_components/momcozy/rtsp.py",
    )
    rtsp = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(rtsp)
    private = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8-sig"))
    host = private.get("listen-host", "127.0.0.1")
    if host in ("0.0.0.0", "::"):
        host = "127.0.0.1" if host == "0.0.0.0" else "::1"
    config = rtsp.normalize_config(
        {
            "host": host,
            "port": int(private["port"]),
            "path": private["camera-name"],
            "name": "Live probe",
            "username": private.get("rtsp-user", ""),
            "password": private.get("rtsp-password", ""),
        }
    )
    try:
        asyncio.run(rtsp.async_validate_endpoint(config))
    except rtsp.InvalidAuth:
        raise SystemExit("RTSP authentication rejected") from None
    except rtsp.CannotConnect:
        raise SystemExit("RTSP video description unavailable") from None
    print("PASS: valid RTSP video SDP received (media decoding not tested)")


if __name__ == "__main__":
    main()
