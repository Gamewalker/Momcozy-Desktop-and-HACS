"""Protocol tests against real loopback TCP servers; no HA installation needed."""

import asyncio
import base64
import importlib.util
import unittest
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "momcozy_rtsp",
    Path(__file__).resolve().parents[2] / "custom_components/momcozy/rtsp.py",
)
rtsp = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(rtsp)
DATA = {
    "host": "127.0.0.1",
    "port": 18554,
    "path": "bm04_1",
    "name": "Nursery",
    "username": "",
    "password": "",
}
SDP = b"v=0\r\nm=video 0 RTP/AVP 96\r\na=rtpmap:96 H265/90000\r\n"


class ConfigTests(unittest.TestCase):
    def test_normalizes_endpoint_and_preserves_password(self):
        data = rtsp.normalize_config(
            {
                **DATA,
                "host": "BRIDGE.local.",
                "path": "/bm04_1/",
                "username": "user",
                "password": " space ",
            }
        )
        self.assertEqual(rtsp.endpoint_id(data), "bridge.local:18554/bm04_1")
        self.assertEqual(data["password"], " space ")

    def test_ipv6_and_escaping(self):
        data = rtsp.normalize_config(
            {**DATA, "host": "[::1]", "username": "user@host", "password": "a:b/@?#"}
        )
        self.assertEqual(
            rtsp.stream_url(data),
            "rtsp://user%40host:a%3Ab%2F%40%3F%23@[::1]:18554/bm04_1",
        )
        self.assertEqual(
            rtsp.stream_url(data, credentials=False), "rtsp://[::1]:18554/bm04_1"
        )

    def test_reject_invalid_fields(self):
        for field, value in [
            ("host", "rtsp://host"),
            ("host", "host\r\nheader"),
            ("path", "x\r\ny"),
            ("path", ""),
            ("port", 0),
            ("username", "alone"),
            ("name", " "),
        ]:
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                rtsp.normalize_config({**DATA, field: value})


class ProbeTests(unittest.IsolatedAsyncioTestCase):
    async def probe(self, responses, data=None, timeout=1):
        requests = []

        async def handle(reader, writer):
            try:
                for response in responses:
                    requests.append(await reader.readuntil(b"\r\n\r\n"))
                    writer.write(response)
                    await writer.drain()
            finally:
                writer.close()
                await writer.wait_closed()

        server = await asyncio.start_server(handle, "127.0.0.1", 0)
        async with server:
            config = {
                **DATA,
                **(data or {}),
                "port": server.sockets[0].getsockname()[1],
            }
            await rtsp.async_validate_endpoint(config, timeout)
        return requests

    def ok(self, body=SDP):
        return (
            b"RTSP/1.0 200 OK\r\nContent-Length: "
            + str(len(body)).encode()
            + b"\r\n\r\n"
            + body
        )

    async def test_video_description(self):
        requests = await self.probe([self.ok()])
        self.assertIn(b"DESCRIBE rtsp://", requests[0])
        self.assertNotIn(b"Authorization", requests[0])

    async def test_basic_challenge(self):
        requests = await self.probe(
            [
                b'RTSP/1.0 401 Unauthorized\r\nWWW-Authenticate: Basic realm="Momcozy"\r\n\r\n',
                self.ok(),
            ],
            {"username": "viewer", "password": "secret"},
        )
        self.assertNotIn(b"Authorization", requests[0])
        self.assertIn(
            b"Authorization: Basic " + base64.b64encode(b"viewer:secret"), requests[1]
        )
        self.assertNotIn(b"viewer:secret@", requests[1])

    async def test_missing_credentials(self):
        with self.assertRaises(rtsp.InvalidAuth):
            await self.probe(
                [
                    b'RTSP/1.0 401 Unauthorized\r\nWWW-Authenticate: Basic realm="Momcozy"\r\n\r\n'
                ]
            )

    async def test_wrong_credentials(self):
        response = b'RTSP/1.0 401 Unauthorized\r\nWWW-Authenticate: Basic realm="Momcozy"\r\n\r\n'
        with self.assertRaises(rtsp.InvalidAuth):
            await self.probe(
                [response, response], {"username": "viewer", "password": "wrong"}
            )

    async def test_reject_non_video_and_http(self):
        for response in [
            self.ok(b"v=0\r\nm=audio 0 RTP/AVP 0\r\n"),
            b"HTTP/1.1 200 OK\r\n\r\n",
            b"RTSP/1.0 404 Not Found\r\n\r\n",
            b"RTSP/1.0 200 OK\r\nContent-Length: 99999999\r\n\r\n",
        ]:
            with self.subTest(response=response), self.assertRaises(rtsp.CannotConnect):
                await self.probe([response])

    async def test_silent_server_timeout_closes_connection(self):
        closed = asyncio.Event()

        async def handle(reader, writer):
            await reader.read()
            writer.close()
            await writer.wait_closed()
            closed.set()

        server = await asyncio.start_server(handle, "127.0.0.1", 0)
        async with server:
            with self.assertRaises(rtsp.CannotConnect):
                await rtsp.async_validate_endpoint(
                    {**DATA, "port": server.sockets[0].getsockname()[1]}, timeout=0.05
                )
            await asyncio.wait_for(closed.wait(), 1)


if __name__ == "__main__":
    unittest.main()
