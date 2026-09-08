"""Bounded RTSP description probe; the bridge may initiate cloud signaling."""

from __future__ import annotations

import asyncio
import base64
import ipaddress
import re
from collections.abc import Mapping
from typing import Any
from urllib.parse import quote


class CannotConnect(Exception):
    """The endpoint did not return a valid RTSP video description."""


class InvalidAuth(CannotConnect):
    """The bridge rejected authentication."""


def normalize_config(data: Mapping[str, Any]) -> dict[str, Any]:
    """Validate separate fields, excluding URLs and RTSP header injection."""
    result = dict(data)
    host = str(data["host"]).strip().lower().strip("[]").rstrip(".")
    try:
        host = str(ipaddress.ip_address(host))
    except ValueError:
        if not re.fullmatch(r"[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?", host):
            raise ValueError("Invalid host") from None
    port = int(data["port"])
    if not 1 <= port <= 65535:
        raise ValueError("Invalid port")
    path = str(data["path"]).strip().strip("/")
    if not path or any(ord(char) < 32 for char in path) or "?" in path or "#" in path:
        raise ValueError("Invalid path")
    username = str(data.get("username", ""))
    password = str(data.get("password", ""))
    if bool(username) != bool(password) or ":" in username:
        raise ValueError("Supply both bridge credentials, or neither")
    name = str(data["name"]).strip()
    if not name:
        raise ValueError("Invalid name")
    result.update(
        host=host, port=port, path=path, name=name, username=username, password=password
    )
    return result


def endpoint_id(data: Mapping[str, Any]) -> str:
    """Identify the configured endpoint without including credentials."""
    return f"{data['host']}:{data['port']}/{data['path']}"


def stream_url(data: Mapping[str, Any], *, credentials: bool = True) -> str:
    """Construct a URL, escaping passwords and supporting IPv6."""
    host = str(data["host"])
    if ":" in host:
        host = f"[{host}]"
    auth = ""
    if credentials and data.get("username"):
        auth = f"{quote(data['username'], safe='')}:{quote(data['password'], safe='')}@"
    return f"rtsp://{auth}{host}:{data['port']}/{quote(data['path'], safe='/')}"


async def async_validate_endpoint(data: Mapping[str, Any], timeout: float = 8) -> None:
    """Require a video SDP, optionally retrying a Basic challenge once.

    The bridge implements Basic auth on a trusted LAN. No credentials are
    sent before a challenge, no redirects are followed, and no exception
    contains a request, response body or authenticated URL.
    """
    writer = None
    try:
        async with asyncio.timeout(timeout):
            reader, writer = await asyncio.open_connection(
                data["host"], data["port"], limit=16384
            )
            authorization = ""
            for sequence in (1, 2):
                request = (
                    f"DESCRIBE {stream_url(data, credentials=False)} RTSP/1.0\r\n"
                    f"CSeq: {sequence}\r\nAccept: application/sdp\r\n"
                    f"User-Agent: Momcozy-HomeAssistant\r\n{authorization}\r\n"
                )
                writer.write(request.encode("utf-8"))
                await writer.drain()
                raw_headers = await reader.readuntil(b"\r\n\r\n")
                lines = raw_headers.decode("latin-1").split("\r\n")
                match = re.fullmatch(r"RTSP/1\.0 (\d{3})(?: .*)?", lines[0])
                if not match:
                    raise CannotConnect
                status = int(match[1])
                headers = {}
                for line in lines[1:]:
                    if ":" in line:
                        key, value = line.split(":", 1)
                        headers[key.strip().lower()] = value.strip()
                size = int(headers.get("content-length", "0"))
                if not 0 <= size <= 65536:
                    raise CannotConnect
                body = await reader.readexactly(size)
                if status in (401, 403):
                    if (
                        sequence == 2
                        or not data.get("username")
                        or not headers.get("www-authenticate", "")
                        .lower()
                        .startswith("basic ")
                    ):
                        raise InvalidAuth
                    token = base64.b64encode(
                        f"{data['username']}:{data['password']}".encode()
                    ).decode()
                    authorization = f"Authorization: Basic {token}\r\n"
                    continue
                if status != 200 or not re.search(rb"(?:^|\n)m=video ", body):
                    raise CannotConnect
                return
    except InvalidAuth:
        raise
    except (
        OSError,
        TimeoutError,
        ValueError,
        asyncio.IncompleteReadError,
        asyncio.LimitOverrunError,
    ):
        raise CannotConnect from None
    finally:
        if writer is not None:
            writer.close()
            try:
                async with asyncio.timeout(1):
                    await writer.wait_closed()
            except (OSError, TimeoutError):
                pass
