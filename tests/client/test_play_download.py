import base64
import gzip
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import urllib.request
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "client"))
import play_download as play
import setup_wizard as wizard
from goopdl.api import AppDetails, DeliveryResult, SplitInfo


def item(data, **changes):
    values = dict(size=len(data), url="https://play.googleapis.com/file", gzipped_url="",
                  sha1="", sha256=base64.urlsafe_b64encode(hashlib.sha256(data).digest()).decode().rstrip("="))
    values.update(changes)
    return SimpleNamespace(**values)


class PlayDownloadTests(unittest.TestCase):
    def test_rejects_non_google_and_credential_urls(self):
        for url in ("http://play.googleapis.com/a", "https://googleapis.com.evil.test/a",
                    "https://evilgoogle.com/a", "https://u:p@play.googleapis.com/a",
                    "https://127.0.0.1/a", "https://play.googleapis.com:8443/a"):
            with self.subTest(url=url), self.assertRaises(wizard.SetupError):
                play.google_url(url)

    def test_redirect_validation_and_cookie_scope(self):
        handler = play.GoogleRedirect()
        request = urllib.request.Request("https://play.googleapis.com/a", headers={"Cookie": "secret"})
        with self.assertRaises(wizard.SetupError):
            handler.redirect_request(request, None, 302, "", {}, "https://example.org/a")
        redirected = handler.redirect_request(request, None, 302, "", {}, "https://other.google.com/a")
        self.assertFalse(redirected.has_header("Cookie"))

    def test_corrupt_truncated_and_oversize_downloads_are_removed(self):
        original = b"valid apk fixture"
        for raw in (b"x" * len(original), original[:-1], original + b"extra"):
            with self.subTest(raw=raw), tempfile.TemporaryDirectory() as temp:
                dest = Path(temp) / "base.apk"
                with patch.object(play.urllib.request, "build_opener") as opener:
                    opener.return_value.open.return_value = io.BytesIO(raw)
                    with self.assertRaises(wizard.SetupError):
                        play.download_file(item(original), dest)
                self.assertEqual(list(Path(temp).iterdir()), [])

    def test_plain_and_gzip_payloads_verified_before_publish(self):
        original = b"apk fixture" * 20
        for compressed in (False, True):
            with tempfile.TemporaryDirectory() as temp:
                dest = Path(temp) / "base.apk"
                spec = item(original)
                raw = original
                if compressed:
                    spec.url, spec.gzipped_url = "", spec.url
                    raw = gzip.compress(original)
                with patch.object(play.urllib.request, "build_opener") as opener:
                    opener.return_value.open.return_value = io.BytesIO(raw)
                    play.download_file(spec, dest)
                self.assertEqual(dest.read_bytes(), original)

    def test_rejects_missing_integrity_before_network(self):
        with patch.object(play.urllib.request, "build_opener") as opener:
            with self.assertRaises(wizard.SetupError):
                play.download_file(item(b"abc", sha256=""), Path("unused.apk"))
            opener.assert_not_called()

    def test_direct_auth_does_not_use_dispenser_cache_or_environment(self):
        with patch("goopdl.auth._direct_auth", return_value={"authToken": "fixture"}) as direct, \
                patch("goopdl.auth.fetch_token") as dispenser, patch("goopdl.auth.save_auth") as cache:
            play.authenticate({"playAuth": "token", "playEmail": "test@example.org", "playToken": "fake-aas"})
            self.assertEqual(direct.call_args.args, ("test@example.org", "fake-aas"))
            self.assertEqual(direct.call_args.kwargs["arch"], "arm64")
            dispenser.assert_not_called()
            cache.assert_not_called()

    def test_browser_token_is_used_in_memory(self):
        with patch("goopdl.browser_oauth.capture_oauth_credentials", return_value=("test@example.org", "oauth2_4/test")), \
                patch("goopdl.aastoken.fetch_aas_token", return_value="fake-aas") as exchange, \
                patch("goopdl.auth._direct_auth", return_value={"authToken": "fixture"}) as direct:
            play.authenticate({"playAuth": "browser"})
            exchange.assert_called_once_with("test@example.org", "oauth2_4/test")
            self.assertEqual(direct.call_args.args[1], "fake-aas")

    def test_wrong_package_stops_before_purchase_or_download(self):
        with patch.object(play, "authenticate", return_value={}), \
                patch("goopdl.api.get_details", return_value=AppDetails("wrong.package", version_string="9.9.9", version_code=999)), \
                patch("goopdl.api.purchase") as purchase:
            with self.assertRaises(wizard.SetupError) as caught:
                play.acquire({}, Path("unused"))
            self.assertEqual(caught.exception.code, "play_version")
            purchase.assert_not_called()

    def test_base_and_arm64_selection_ignores_remote_filenames(self):
        # Latest catalog version is requested and confirmed against the APK manifest.
        details = AppDetails(play.PACKAGE, version_string="3.4.0", version_code=30402)
        delivery = DeliveryResult(version_code=30402, splits=[SplitInfo("../../arm64"), SplitInfo("config.en")])
        def download(spec, dest, *args):
            with zipfile.ZipFile(dest, "w") as archive:
                archive.writestr(play.NATIVE if dest.name == "play-arm64.apk" else "AndroidManifest.xml", b"fixture")
        parsed = SimpleNamespace(get_package=lambda: play.PACKAGE, get_androidversion_name=lambda: "3.4.0",
                                 get_androidversion_code=lambda: str(30402))
        with tempfile.TemporaryDirectory() as temp, patch.object(play, "authenticate", return_value={}), \
                patch("goopdl.api.get_details", return_value=details), patch("goopdl.api.purchase", return_value="delivery") as purchase, \
                patch("goopdl.api.get_delivery", return_value=delivery) as get_delivery, patch.object(play, "download_file", side_effect=download), \
                patch("androguard.core.apk.APK", return_value=parsed):
            base, arm = play.acquire({}, Path(temp))
            self.assertEqual(base.name, "play-base.apk")
            self.assertEqual(arm.name, "play-arm64.apk")
            self.assertEqual(set(p.name for p in Path(temp).iterdir()), {base.name, arm.name})
            self.assertEqual(purchase.call_args.args[1], 30402)
            self.assertEqual(get_delivery.call_args.args[1], 30402)

    def test_failed_play_setup_keeps_signing_and_cleans_temporary_files(self):
        with tempfile.TemporaryDirectory() as temp:
            data = Path(temp)
            signing = data / ".setup-signing.private.json"
            signing.write_text("original")
            def fail(request, stage):
                (stage / "partial.apk").write_bytes(b"private")
                raise wizard.SetupError("play_auth", "Sign-in failed")
            with patch.object(play, "acquire", side_effect=fail), self.assertRaises(wizard.SetupError):
                wizard.handle({"command": "preparePlay", "dataDir": temp})
            self.assertEqual(signing.read_text(), "original")
            self.assertEqual(list(data.iterdir()), [signing])

    def test_json_protocol_preserves_play_error_without_echoing_token(self):
        with tempfile.TemporaryDirectory() as temp:
            result = subprocess.run([sys.executable, wizard.__file__], text=True, capture_output=True,
                                    input=json.dumps({"command": "preparePlay", "dataDir": temp,
                                                      "playAuth": "invalid", "playToken": "secret-fixture"}))
            self.assertEqual(json.loads(result.stdout)["error"], "invalid_request")
            self.assertNotIn("secret-fixture", result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
