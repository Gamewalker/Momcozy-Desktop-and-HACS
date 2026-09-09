import builtins
import importlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


CLIENT = Path(__file__).resolve().parents[2] / "client"
sys.path.insert(0, str(CLIENT))

import play_download as play
import setup_wizard as wizard
import goopdl.aastoken
import goopdl.auth
import goopdl.browser_oauth


class SetupMemoryTests(unittest.TestCase):
    def test_signing_derivation_does_not_parse_the_large_base_apk_again(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "apk-parameters.private.json").write_text(json.dumps({
                "THING_SMART_APPKEY": "app-key",
                "THING_SMART_SECRET": "app-secret",
                "package": "com.lute.momcozy",
                "certificateHash": "AA:BB",
                "appVersion": "3.4.0",
                "appVersionCode": "30402",
            }))
            (root / "embedded-keys.private.json").write_text(json.dumps(["656d626564646564"]))
            real_import = builtins.__import__

            def reject_apk_parser(name, *args, **kwargs):
                if name.startswith("androguard"):
                    raise AssertionError("large APK parsed twice during one setup")
                return real_import(name, *args, **kwargs)

            with patch.dict(os.environ, {"MOMCOZY_DATA_DIR": temp}):
                sys.modules.pop("tuya_mobile", None)
                sys.modules.pop("state", None)
                tuya_mobile = importlib.import_module("tuya_mobile")
                try:
                    with patch("builtins.__import__", side_effect=reject_apk_parser):
                        result = tuya_mobile.parameters()
                finally:
                    sys.modules.pop("tuya_mobile", None)
                    sys.modules.pop("state", None)

            self.assertEqual(result["appVersion"], "3.4.0")
            self.assertEqual(result["appVersionCode"], "30402")
            self.assertEqual(result["signingKey"], "com.lute.momcozy_AA:BB_embedded_app-secret")

    def test_google_browser_closes_before_heavy_play_and_apk_imports(self):
        events = []
        real_import = builtins.__import__

        def record_import(name, *args, **kwargs):
            if name in {"goopdl.auth", "goopdl.api", "androguard.core.apk"}:
                events.append(name)
            return real_import(name, *args, **kwargs)

        def browser(*args, **kwargs):
            events.append("browser")
            return "test@example.org", "oauth2_4/test"

        with patch("builtins.__import__", side_effect=record_import), \
                patch.object(goopdl.browser_oauth, "capture_oauth_credentials", side_effect=browser), \
                patch.object(goopdl.aastoken, "fetch_aas_token", return_value="aas"), \
                patch.object(goopdl.auth, "_direct_auth", return_value={"authToken": "fixture"}):
            play.authenticate({"playAuth": "browser"})

        self.assertLess(events.index("browser"), events.index("goopdl.auth"))

    def test_failed_auth_does_not_load_apk_parser(self):
        events = []
        real_import = builtins.__import__

        def record_import(name, *args, **kwargs):
            if name == "androguard.core.apk":
                events.append(name)
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=record_import), \
                patch.object(play, "authenticate", side_effect=wizard.SetupError("play_auth", "fixture")):
            with self.assertRaises(wizard.SetupError):
                play.acquire({}, Path("unused"))

        self.assertEqual(events, [])


if __name__ == "__main__":
    unittest.main()
