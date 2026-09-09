import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "client"))
import app_cache as cache
import setup_wizard as wizard


class AppCacheTests(unittest.TestCase):
    def fixture(self, root, version="3.4.0"):
        source = root / ("source-" + version)
        source.mkdir(exist_ok=True)
        base, arm, signing = (source / n for n in ("base.apk", "arm64.apk", "signing.private.json"))
        base.write_bytes(b"base " + version.encode())
        arm.write_bytes(b"arm " + version.encode())
        signing.write_text(json.dumps({"appKey": "fixture", "signingKey": version,
                                       "deviceId": "old-device", "appVersion": version}))
        archive = root / "archive"
        cache.remember_candidate(archive, base, arm, signing)
        return archive, signing

    def test_unverified_candidate_cannot_be_restored(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            archive, _ = self.fixture(root)
            self.assertIsNone(cache.restore(archive, root))

    def test_new_candidate_does_not_replace_working_version(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            archive, signing = self.fixture(root)
            cache.promote(archive, signing)
            self.fixture(root, "9.9.9")
            result = cache.restore(archive, root)
            self.assertEqual(result["appVersion"], "3.4.0")
            self.assertTrue(result["fallbackUsed"])

    def test_promote_accepts_fresh_device_identity_but_not_different_signing(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            archive, signing = self.fixture(root)
            config = json.loads(signing.read_text())
            config["deviceId"] = "fresh-device"
            signing.write_text(json.dumps(config))
            cache.promote(archive, signing)
            original = (archive / "known-good.private.json").read_bytes()
            self.fixture(root, "9.9.9")
            cache.promote(archive, signing)
            self.assertEqual((archive / "known-good.private.json").read_bytes(), original)

    def test_corrupted_fallback_is_not_restored(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            archive, signing = self.fixture(root)
            cache.promote(archive, signing)
            key = json.loads((archive / "known-good.private.json").read_text())["entry"]
            (archive / key / "base.apk").write_bytes(b"corrupt")
            with self.assertRaises(wizard.SetupError):
                cache.restore(archive, root)
            self.assertFalse((root / "signing.private.json").exists())

    def test_cache_path_traversal_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "known-good.private.json").write_text('{"entry":"../outside"}')
            with self.assertRaises(wizard.SetupError):
                cache.restore(root, root)

    def test_failed_download_uses_shared_cache_in_new_configuration_folder(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            archive, signing = self.fixture(root)
            cache.promote(archive, signing)
            request = {"command": "preparePlay", "dataDir": str(root / "new"), "appCacheDir": str(archive)}
            with patch.object(wizard, "acquire_play", side_effect=wizard.SetupError("play_download", "Unavailable")):
                result = wizard.handle(request)
                self.assertTrue(result["fallbackUsed"])
                self.assertEqual(result["appVersion"], "3.4.0")
                request["allowFallback"] = False
                with self.assertRaises(wizard.SetupError):
                    wizard.handle(request)

    def test_sdk_failure_retries_only_sdk_with_working_version_and_fresh_device(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            archive, signing = self.fixture(root)
            cache.promote(archive, signing)
            data = root / "target"
            data.mkdir()
            (data / ".setup-signing.private.json").write_text('{"signingKey":"bad","appVersion":"9.9.9"}')
            calls, identities = [], []
            def run(name, stage, *args):
                calls.append(name)
                if name == "tuya_login":
                    sign = json.loads((stage / "signing.private.json").read_text())
                    identities.append(sign["deviceId"])
                    if sign["signingKey"] == "bad":
                        raise wizard.SetupError("setup_failed", "SDK rejected")
                    self.assertEqual(sign["appVersion"], "3.4.0")
                if name == "make_bridge_config":
                    (stage / "cameras.private.json").write_text('["bridge-1.private.json"]')
                    (stage / "bridge-1.private.json").write_text('{"camera-name":"bm04_1","device-id":"fixture"}')
            with patch.object(wizard, "run_script", side_effect=run):
                result = wizard.handle({"command": "configure", "dataDir": str(data), "appCacheDir": str(archive),
                                        "username": "fixture", "password": "fixture"})
            self.assertEqual(calls.count("momcozy_login"), 1)
            self.assertEqual(calls.count("tuya_login"), 2)
            self.assertTrue(result["fallbackUsed"])
            self.assertEqual(result["appVersion"], "3.4.0")
            self.assertEqual(len(set(identities)), 2)
            self.assertNotIn("old-device", identities)


if __name__ == "__main__":
    unittest.main()
