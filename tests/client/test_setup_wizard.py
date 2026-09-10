import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "client"))
import setup_wizard as wizard


class SetupWizardTests(unittest.TestCase):
    def test_google_play_download_runs_in_an_isolated_helper_process(self):
        response = subprocess.CompletedProcess(
            ["play_download"], 0,
            '{"ok":true,"base":"play-base.apk","arm":"play-arm64.apk"}', "",
        )
        with tempfile.TemporaryDirectory() as temp:
            stage = Path(temp)
            (stage / "play-base.apk").write_bytes(b"base")
            (stage / "play-arm64.apk").write_bytes(b"arm")
            with patch.object(wizard.subprocess, "run", return_value=response) as run:
                base, arm = wizard.acquire_play({"playAuth": "browser", "playVersionCode": 0}, stage)
        self.assertEqual((base.name, arm.name), ("play-base.apk", "play-arm64.apk"))
        self.assertIn("play_download", " ".join(map(str, run.call_args.args[0])))
        self.assertEqual(run.call_args.kwargs["input"], '{"playAuth": "browser", "playVersionCode": 0}')

    def test_prepare_apk_failure_reports_the_actual_validation_problem(self):
        failed = subprocess.CompletedProcess(
            ["prepare_apk"], 2, b"",
            b"prepare_apk: error: Base and ARM64 APKs must belong to the same app build.\n",
        )
        with patch.object(wizard.subprocess, "run", return_value=failed):
            with self.assertRaises(wizard.SetupError) as caught:
                wizard.run_script("prepare_apk", Path("/private/stage"), "base.apk", "arm64.apk")
        self.assertEqual(caught.exception.code, "apk_prepare")
        self.assertEqual(
            caught.exception.message,
            "Basis- und ARM64-APK stammen nicht aus demselben App-Build.",
        )

    def test_prepare_apk_failure_never_echoes_unknown_subprocess_output(self):
        failed = subprocess.CompletedProcess(
            ["prepare_apk"], 1, b"", b"private-token fixture-secret /private/path\n",
        )
        with patch.object(wizard.subprocess, "run", return_value=failed):
            with self.assertRaises(wizard.SetupError) as caught:
                wizard.run_script("prepare_apk", Path("/private/stage"), "base.apk", "arm64.apk")
        self.assertEqual(caught.exception.code, "apk_prepare")
        self.assertNotIn("fixture-secret", caught.exception.message)
        self.assertNotIn("/private/path", caught.exception.message)

    def test_prepare_apk_oom_is_not_reported_as_a_damaged_apk(self):
        failed = subprocess.CompletedProcess(["prepare_apk"], 137, b"", b"")
        with patch.object(wizard.subprocess, "run", return_value=failed):
            with self.assertRaises(wizard.SetupError) as caught:
                wizard.run_script("prepare_apk", Path("/private/stage"), "base.apk", "arm64.apk")
        self.assertEqual(caught.exception.code, "apk_memory")
        self.assertIn("Arbeitsspeicher", caught.exception.message)

    def test_diagnostic_self_test_never_reads_stdin_and_keeps_traceback(self):
        with patch.object(sys, "argv", ["helper", "--self-test"]), patch.object(wizard, "handle", side_effect=RuntimeError("fixture failure")) as handle:
            with self.assertRaisesRegex(RuntimeError, "fixture failure"):
                wizard.main()
            handle.assert_called_once_with({"command": "selfTest"})

    def test_device_selection_requires_explicit_choice(self):
        with patch.object(wizard, "devices", return_value=[{"serial": "a", "state": "device"}, {"serial": "b", "state": "device"}]):
            with self.assertRaises(wizard.SetupError) as caught:
                wizard.select_device({})
            self.assertEqual(caught.exception.code, "multiple_devices")
            self.assertEqual(wizard.select_device({"serial": "b"}), "b")

    def test_unauthorized_phone_is_not_used(self):
        with patch.object(wizard, "devices", return_value=[{"serial": "a", "state": "unauthorized"}]):
            with self.assertRaises(wizard.SetupError) as caught:
                wizard.select_device({})
            self.assertEqual(caught.exception.code, "device_not_authorized")

    def test_frozen_dispatch_runs_module_through_helper(self):
        with patch.object(sys, "frozen", True, create=True):
            self.assertEqual(wizard.script_command("decode_tuya_key"), [sys.executable, "--internal", "decode_tuya_key"])

    def test_login_failure_preserves_existing_files_and_removes_password(self):
        with tempfile.TemporaryDirectory() as temp:
            data = Path(temp)
            (data / "signing.private.json").write_text('{"test":"original"}')
            with patch.object(wizard, "run_script", side_effect=wizard.SetupError("setup_failed", "Login failed")):
                with self.assertRaises(wizard.SetupError):
                    wizard.handle({"command": "configure", "dataDir": temp, "username": "test", "password": "secret"})
            self.assertEqual((data / "signing.private.json").read_text(), '{"test":"original"}')
            self.assertEqual([p.name for p in data.iterdir()], ["signing.private.json"])

    def test_existing_cameras_are_not_replaced(self):
        with tempfile.TemporaryDirectory() as temp:
            manifest = Path(temp) / "cameras.private.json"
            manifest.write_text('["existing"]')
            with self.assertRaises(wizard.SetupError) as caught:
                wizard.handle({"command": "configure", "dataDir": temp})
            self.assertEqual(caught.exception.code, "existing_configuration")
            self.assertEqual(manifest.read_text(), '["existing"]')

    def test_explicit_reconfiguration_replaces_existing_setup_atomically(self):
        with tempfile.TemporaryDirectory() as temp:
            data = Path(temp)
            (data / "cameras.private.json").write_text('["bridge-old.private.json"]')
            (data / "bridge-old.private.json").write_text('{"camera-name":"old"}')
            (data / ".setup-signing.private.json").write_text('{}')

            def pipeline(name, stage, *args):
                if name == "make_bridge_config":
                    (stage / "cameras.private.json").write_text('["bridge-new.private.json"]')
                    (stage / "bridge-new.private.json").write_text(
                        '{"camera-name":"new","device-id":"new-device"}'
                    )

            with patch.object(wizard, "run_script", side_effect=pipeline):
                result = wizard.handle({
                    "command": "configure",
                    "dataDir": temp,
                    "replaceExisting": True,
                    "username": "user",
                    "password": "secret",
                })

            self.assertEqual(result["cameras"][0]["name"], "new")
            self.assertEqual(json.loads((data / "cameras.private.json").read_text()), ["bridge-new.private.json"])
            self.assertFalse((data / "bridge-old.private.json").exists())

    def test_import_rejects_traversal_before_publishing(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "source"
            source.mkdir()
            (source / "cameras.private.json").write_text('["../bridge-1.private.json"]')
            with self.assertRaises(wizard.SetupError):
                wizard.handle({"command": "importConfig", "configDir": str(source), "dataDir": str(root / "target")})
            self.assertFalse((root / "target/cameras.private.json").exists())

    def test_legacy_bridge_without_manifest_is_preserved(self):
        with tempfile.TemporaryDirectory() as temp:
            bridge = Path(temp) / "bridge-1.private.json"
            bridge.write_text('{"legacy":"keep"}')
            for command in ("configure", "importConfig"):
                with self.assertRaises(wizard.SetupError) as caught:
                    wizard.handle({"command": command, "dataDir": temp})
                self.assertEqual(caught.exception.code, "existing_configuration")
                self.assertEqual(bridge.read_text(), '{"legacy":"keep"}')

    def test_import_makes_desktop_config_loopback_and_strips_rtsp_password(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "source"
            source.mkdir()
            (source / "cameras.private.json").write_text('["bridge-1.private.json"]')
            config = dict.fromkeys(("signing-key", "sid", "ecode", "partner", "app-key", "device-id", "ch-key", "camera-id", "camera-name"), "value")
            config.update(port="18554", **{"listen-host": "0.0.0.0", "rtsp-password": "secret"})
            (source / "bridge-1.private.json").write_text(json.dumps(config))
            result = wizard.handle({"command": "importConfig", "configDir": str(source), "dataDir": str(root / "target")})
            self.assertEqual(result["cameraCount"], 1)
            saved = json.loads((root / "target/bridge-1.private.json").read_text())
            self.assertEqual(saved["listen-host"], "127.0.0.1")
            self.assertTrue(saved["device-id"].startswith("value-import-"))
            self.assertEqual(json.loads((source / "bridge-1.private.json").read_text())["device-id"], "value")
            self.assertNotIn("rtsp-password", saved)
            self.assertNotIn("secret", json.dumps(result))

    def test_protocol_error_does_not_echo_input(self):
        result = subprocess.run([sys.executable, wizard.__file__], input=json.dumps({"command": "private-password-value"}), text=True, capture_output=True)
        response = json.loads(result.stdout)
        self.assertFalse(response["ok"])
        self.assertNotIn("private-password-value", result.stdout + result.stderr)

    def test_success_publishes_only_after_all_pipeline_steps(self):
        with tempfile.TemporaryDirectory() as temp:
            data = Path(temp)
            (data / ".setup-signing.private.json").write_text('{}')
            calls = []
            def pipeline(name, stage, *args):
                calls.append(name)
                self.assertFalse((data / "cameras.private.json").exists())
                if name == "momcozy_login":
                    self.assertEqual(json.loads(Path(args[0]).read_text())["password"], "test-secret")
                    self.assertEqual(json.loads(Path(args[0]).read_text())["countryCode"], "DE")
                if name == "make_bridge_config":
                    (stage / "cameras.private.json").write_text('["bridge-1.private.json"]')
                    (stage / "bridge-1.private.json").write_text('{"camera-name":"bm04_1","device-id":"test"}')
            with patch.object(wizard, "run_script", side_effect=pipeline):
                result = wizard.handle({"command": "configure", "dataDir": temp, "username": "user", "password": "test-secret", "basePort": 21000})
            self.assertEqual(len(calls), 5)
            self.assertEqual(result["cameraCount"], 1)
            self.assertEqual(result["cameras"][0]["port"], 21000)
            self.assertNotIn("test-secret", str(result))
            self.assertFalse(list(data.glob(".setup-*")))
            self.assertFalse((data / "credentials.private.json").exists())

    def test_ha_options_require_private_host_and_generate_auth(self):
        with tempfile.TemporaryDirectory() as temp:
            stage = Path(temp)
            config = stage / "bridge-1.private.json"
            config.write_text('{"camera-name":"bm04_1","device-id":"test"}')
            with self.assertRaises(wizard.SetupError):
                wizard.apply_options({"targetMode": "ha", "bridgeHost": "0.0.0.0"}, stage, [config.name])
            result = wizard.apply_options({"targetMode": "ha", "bridgeHost": "192.168.1.2"}, stage, [config.name])
            saved = json.loads(config.read_text())
            self.assertGreaterEqual(len(saved["rtsp-password"]), 16)
            self.assertEqual(saved["rtsp-user"], "homeassistant")
            self.assertNotIn(saved["rtsp-password"], str(result))
            self.assertEqual(result[0]["port"], 19554)

    def test_addon_options_bind_container_and_return_ingress_credentials(self):
        with tempfile.TemporaryDirectory() as temp:
            stage = Path(temp)
            config = stage / "bridge-1.private.json"
            config.write_text('{"camera-name":"bm04_1","device-id":"test"}')
            result = wizard.apply_options(
                {"targetMode": "ha", "bridgeHost": "192.168.1.2", "addonMode": True,
                 "audioFormat": "aac", "ffmpegPath": sys.executable},
                stage, [config.name])
            saved = json.loads(config.read_text())
            self.assertEqual(saved["listen-host"], "0.0.0.0")
            self.assertEqual(result[0]["name"], "bm04_1")
            self.assertEqual(result[0]["host"], "192.168.1.2")
            self.assertEqual(result[0]["username"], "homeassistant")
            self.assertEqual(result[0]["password"], saved["rtsp-password"])

    def test_addon_options_accept_loopback_for_same_home_assistant_host(self):
        with tempfile.TemporaryDirectory() as temp:
            stage = Path(temp)
            config = stage / "bridge-1.private.json"
            config.write_text('{"camera-name":"bm04_1","device-id":"test"}')
            result = wizard.apply_options(
                {"targetMode": "ha", "bridgeHost": "127.0.0.1", "addonMode": True,
                 "audioFormat": "aac", "ffmpegPath": sys.executable},
                stage, [config.name])
            saved = json.loads(config.read_text())
            self.assertEqual(saved["listen-host"], "0.0.0.0")
            self.assertEqual(result[0]["host"], "127.0.0.1")

    def test_addon_options_accept_home_assistant_dns_name(self):
        with tempfile.TemporaryDirectory() as temp:
            stage = Path(temp)
            config = stage / "bridge-1.private.json"
            config.write_text('{"camera-name":"bm04_1","device-id":"test"}')
            result = wizard.apply_options(
                {"targetMode": "ha", "bridgeHost": "HomeAssistant.local.", "addonMode": True,
                 "audioFormat": "aac", "ffmpegPath": sys.executable},
                stage, [config.name])
            saved = json.loads(config.read_text())
            self.assertEqual(saved["listen-host"], "0.0.0.0")
            self.assertEqual(result[0]["host"], "homeassistant.local")

            config.write_text('{"camera-name":"bm04_1","device-id":"test"}')
            for invalid_host in ("localhost", "0.0.0.0", "::1"):
                with self.subTest(invalid_host=invalid_host), self.assertRaises(wizard.SetupError):
                    wizard.apply_options(
                        {"targetMode": "ha", "bridgeHost": invalid_host, "addonMode": True,
                         "audioFormat": "aac", "ffmpegPath": sys.executable},
                        stage, [config.name])

    def test_addon_options_reject_more_than_exposed_ports(self):
        with tempfile.TemporaryDirectory() as temp:
            stage = Path(temp)
            names = []
            for index in range(wizard.ADDON_MAX_CAMERAS + 1):
                name = f"bridge-{index}.private.json"
                (stage / name).write_text(json.dumps({"camera-name": f"bm04_{index}", "device-id": str(index)}))
                names.append(name)
            with self.assertRaises(wizard.SetupError):
                wizard.apply_options(
                    {"targetMode": "ha", "bridgeHost": "192.168.1.2", "addonMode": True},
                    stage, names)

    def test_pull_selects_arm64_library_not_split_filename(self):
        import zipfile
        with tempfile.TemporaryDirectory() as temp:
            def fake_adb(request, *args):
                if "pm" in args:
                    return "package:/data/app/base.apk\npackage:/data/app/split_config.arm64_v8a.apk\n"
                if "pull" in args:
                    with zipfile.ZipFile(args[-1], "w") as apk:
                        if "arm64" in args[-2]:
                            apk.writestr("lib/arm64-v8a/libthing_security_algorithm.so", b"fixture")
                    return ""
                self.fail("Unexpected adb invocation")
            with patch.object(wizard, "select_device", return_value="phone"), patch.object(wizard, "adb", side_effect=fake_adb):
                base, arm = wizard.pull_apks({}, Path(temp))
            self.assertEqual(base.name, "input-0.apk")
            self.assertEqual(arm.name, "input-1.apk")


if __name__ == "__main__":
    unittest.main()
