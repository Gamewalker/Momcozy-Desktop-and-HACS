"""Private JSON stdin/stdout setup helper, also usable as a frozen executable.

The parent must serialize requests for a data directory. No credential or child
output is returned. Android is read through adb only; nothing is installed.
"""
import json
import ipaddress
import os
from pathlib import Path
import runpy
import secrets
import shutil
import subprocess
import sys
import tempfile
import zipfile
from setup_errors import SetupError

SCRIPTS = {"prepare_apk", "decode_tuya_key", "momcozy_login", "tuya_login",
           "list_momcozy_devices", "tuya_camera_info", "make_bridge_config"}


def script_command(name, *args):
    if name not in SCRIPTS:
        raise ValueError("Unknown setup script")
    if getattr(sys, "frozen", False):
        return [sys.executable, "--internal", name, *map(str, args)]
    return [sys.executable, str(Path(__file__).with_name(name + ".py")), *map(str, args)]


def private_dir(path):
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    if os.name != "nt":
        path.chmod(0o700)
    else:
        # Remove inherited access from newly created setup folders. The owner
        # and SYSTEM keep access, including when the user has a spaced name.
        import getpass
        result = subprocess.run(["icacls", str(path), "/inheritance:r", "/grant:r",
                                 getpass.getuser() + ":(OI)(CI)F", "*S-1-5-18:(OI)(CI)F"],
                                capture_output=True, creationflags=0x08000000)
        if result.returncode:
            raise SetupError("private_directory", "Could not protect the private setup directory.")


def run_script(name, stage, *args):
    env = dict(os.environ, MOMCOZY_DATA_DIR=str(stage))
    result = subprocess.run(script_command(name, *args), env=env, capture_output=True,
                            timeout=300, creationflags=0x08000000 if os.name == "nt" else 0)
    if result.returncode:
        raise SetupError("setup_failed", "Setup step failed: " + name + ". Check app version and account details.")


def adb(request, *args):
    executable = request.get("adbPath") or shutil.which("adb")
    if not executable:
        raise SetupError("adb_missing", "Android platform tools (adb) are not available.")
    try:
        result = subprocess.run([executable, *args], capture_output=True, text=True,
                                timeout=120, creationflags=0x08000000 if os.name == "nt" else 0)
    except FileNotFoundError:
        raise SetupError("adb_missing", "Android platform tools (adb) are not available.")
    if result.returncode:
        raise SetupError("adb_failed", "Android communication failed. Check the USB connection.")
    return result.stdout


def devices(request):
    return [{"serial": fields[0], "state": fields[1]} for line in adb(request, "devices").splitlines()
            if len(fields := line.split()) >= 2 and fields[1] in {"device", "unauthorized", "offline"}]


def select_device(request):
    found = devices(request)
    if request.get("serial"):
        found = [d for d in found if d["serial"] == request["serial"]]
    if not found:
        raise SetupError("no_device", "No Android phone found. Connect it and enable USB debugging.")
    if len(found) != 1:
        raise SetupError("multiple_devices", "Select one Android phone.")
    if found[0]["state"] != "device":
        raise SetupError("device_not_authorized", "Unlock the phone and approve USB debugging.")
    return found[0]["serial"]


def pull_apks(request, stage):
    serial = select_device(request)
    output = adb(request, "-s", serial, "shell", "pm", "path", "com.lute.momcozy")
    paths = [line[8:].strip() for line in output.splitlines() if line.startswith("package:")]
    if not paths:
        raise SetupError("app_missing", "Install and configure the Momcozy app on this phone first.")
    pulled = []
    for number, remote in enumerate(paths):
        local = stage / ("input-" + str(number) + ".apk")
        adb(request, "-s", serial, "pull", remote, str(local))
        pulled.append((remote, local))
    base = next((local for remote, local in pulled if remote.endswith("/base.apk")), None)
    arm = None
    for _, local in pulled:
        with zipfile.ZipFile(local) as archive:
            if "lib/arm64-v8a/libthing_security_algorithm.so" in archive.namelist():
                arm = local
                break
    if not base or not arm:
        raise SetupError("apk_unsupported", "The installed app must include its base and ARM64 APKs.")
    return base, arm


def apply_options(request, stage, manifest):
    mode = request.get("targetMode", "desktop")
    audio = request.get("audioFormat", "copy")
    base = int(request.get("basePort") or (19554 if mode == "ha" else 18554))
    if mode not in {"desktop", "ha"} or audio not in {"copy", "aac"} or not 1024 <= base <= 65536 - len(manifest):
        raise SetupError("invalid_options", "Choose a valid mode, audio format and port range.")
    host = "127.0.0.1"
    if mode == "ha":
        try:
            address = ipaddress.ip_address(request.get("bridgeHost", ""))
            if address.is_unspecified or address.is_loopback or address.is_multicast or not address.is_private:
                raise ValueError()
            host = str(address)
        except ValueError:
            raise SetupError("invalid_host", "Enter this computer's private LAN IP for Home Assistant.")
    ffmpeg = request.get("ffmpegPath") or shutil.which("ffmpeg")
    if audio == "aac" and (not ffmpeg or not Path(ffmpeg).is_file()):
        raise SetupError("ffmpeg_missing", "AAC requires FFmpeg. Select its executable or install it first.")
    cameras = []
    for index, name in enumerate(manifest):
        file = stage / name
        config = json.loads(file.read_text(encoding="utf-8-sig"))
        config.update({"listen-host": host, "port": str(base + index), "audio-format": audio})
        config.pop("rtsp-user", None)
        config.pop("rtsp-password", None)
        config.pop("ffmpeg-path", None)
        camera = {"host": host, "port": base + index, "path": config["camera-name"]}
        if audio == "aac":
            config["ffmpeg-path"] = str(Path(ffmpeg).resolve())
        if mode == "ha":
            config["rtsp-user"] = "homeassistant"
            config["rtsp-password"] = secrets.token_urlsafe(24)
            camera["username"] = "homeassistant"
            # Deliberately return a path, never RTSP or cloud credentials. The
            # local UI can explain where HA credentials are stored privately.
            config["device-id"] += "-ha-" + secrets.token_hex(4)
        camera["configFile"] = name
        file.write_text(json.dumps(config), encoding="utf-8")
        cameras.append(camera)
    return cameras


def refuse_existing_cameras(data):
    if (data / "cameras.private.json").exists() or any(data.glob("bridge-*.private.json")):
        raise SetupError("existing_configuration", "This folder already contains cameras. Choose a new setup folder.")


def handle(request):
    command = request.get("command")
    if command == "selfTest":
        from goopdl.profiles import get_priority_profiles
        from goopdl.browser_oauth import capture_oauth_credentials
        from importlib.metadata import version
        from unicorn import Uc, UC_ARCH_ARM64, UC_MODE_ARM, UC_HOOK_CODE
        from unicorn.arm64_const import UC_ARM64_REG_X0
        from androguard.core.apk import APK
        from elftools.elf.elffile import ELFFile
        from cryptography.hazmat.primitives import hashes
        from argon2.low_level import Type
        emulator = Uc(UC_ARCH_ARM64, UC_MODE_ARM)
        emulator.mem_map(0x10000, 0x1000)
        # mov x0,#42 ; nop. Stop through a Python callback like the APK decoder.
        emulator.mem_write(0x10000, bytes.fromhex("400580d21f2003d5"))
        def stop(uc, address, size, userdata):
            if address == 0x10004:
                uc.emu_stop()
        emulator.hook_add(UC_HOOK_CODE, stop)
        emulator.emu_start(0x10000, 0x10008)
        if emulator.reg_read(UC_ARM64_REG_X0) != 42:
            raise SetupError("self_test_failed", "The native setup runtime did not pass its test.")
        if version("goopdl") != "1.2.1" or not get_priority_profiles("arm64"):
            raise SetupError("self_test_failed", "The Google Play downloader runtime is incomplete.")
        return {"ok": True, "nativeRuntime": True, "googlePlayRuntime": True}
    if command == "discover":
        return {"ok": True, "devices": devices(request)}
    if command not in {"prepareAndroid", "prepareApks", "preparePlay", "prepareCached", "importSigning", "importConfig", "configure"}:
        raise SetupError("invalid_request", "Unknown setup command.")
    data = Path(request["dataDir"]).expanduser().resolve()
    private_dir(data)
    signing = data / ".setup-signing.private.json"
    app_result = {}
    cache_data = Path(request.get("appCacheDir") or data / "app-cache").expanduser().resolve()
    with tempfile.TemporaryDirectory(prefix=".setup-", dir=data) as temp:
        stage = Path(temp)
        private_dir(stage)
        if command in {"preparePlay", "prepareCached"}:
            refuse_existing_cameras(data)
        if command == "importConfig":
            refuse_existing_cameras(data)
            source = Path(request["configDir"]).expanduser().resolve()
            manifest = json.loads((source / "cameras.private.json").read_text(encoding="utf-8-sig"))
            if not isinstance(manifest, list) or not manifest or len(set(manifest)) != len(manifest):
                raise SetupError("invalid_config", "The camera manifest is invalid.")
            for name in manifest:
                if not isinstance(name, str) or Path(name).name != name or not name.startswith("bridge-") or not name.endswith(".private.json") or "\\" in name or ":" in name:
                    raise SetupError("invalid_config", "The camera manifest contains an invalid filename.")
                config = json.loads((source / name).read_text(encoding="utf-8-sig"))
                required = ("signing-key", "sid", "ecode", "partner", "app-key", "device-id", "ch-key", "camera-id", "camera-name")
                if not all(isinstance(config.get(key), str) and config[key] for key in required):
                    raise SetupError("invalid_config", "A camera configuration is incomplete.")
                port = int(config.get("port", 0))
                if not 1 <= port <= 65535:
                    raise SetupError("invalid_config", "A camera port is invalid.")
                # Keep desktop imports local. A LAN-facing configuration requires
                # deliberate HA setup, not copying another computer's listener.
                config["listen-host"] = "127.0.0.1"
                config.pop("rtsp-user", None)
                config.pop("rtsp-password", None)
                # Independent desktop imports must not reuse a currently running
                # source bridge's MQTT client identity.
                config["device-id"] += "-import-" + secrets.token_hex(4)
                (stage / name).write_text(json.dumps(config), encoding="utf-8")
            cameras = apply_options(request, stage, manifest)
            for name in manifest:
                os.replace(stage / name, data / name)
            (stage / "cameras.private.json").write_text(json.dumps(manifest), encoding="utf-8")
            os.replace(stage / "cameras.private.json", data / "cameras.private.json")
            return {"ok": True, "cameraCount": len(manifest), "dataDir": str(data), "cameras": cameras}
        if command in {"prepareAndroid", "prepareApks", "preparePlay"}:
            from app_cache import remember_candidate, restore
            try:
                if command == "preparePlay":
                    from play_download import acquire
                    base, arm = acquire(request, stage)
                else:
                    base, arm = pull_apks(request, stage) if command == "prepareAndroid" else (
                        Path(request["baseApk"]).resolve(), Path(request["arm64Apk"]).resolve())
                run_script("prepare_apk", stage, base, arm)
            except SetupError:
                if command != "preparePlay" or not request.get("allowFallback", True):
                    raise
                app_result = restore(cache_data, stage)
                if not app_result:
                    raise
            else:
                app_result["appVersion"] = remember_candidate(cache_data, base, arm, stage / "signing.private.json")
        elif command == "prepareCached":
            from app_cache import restore
            app_result = restore(cache_data, stage)
            if not app_result:
                raise SetupError("cache_missing", "No successfully configured app version is saved in this folder.")
        elif command == "importSigning":
            config = json.loads(Path(request["signingPath"]).read_text(encoding="utf-8-sig"))
            if not all(isinstance(config.get(k), str) and config[k] for k in ("appKey", "signingKey", "deviceId")):
                raise SetupError("invalid_signing", "This is not a valid private signing configuration.")
            (stage / "signing.private.json").write_text(json.dumps(config), encoding="utf-8")
        else:
            refuse_existing_cameras(data)
            source = signing if signing.exists() else data / "signing.private.json"
            if not source.exists():
                raise SetupError("signing_missing", "Prepare the app or import your private signing configuration first.")
            shutil.copyfile(source, stage / "signing.private.json")
            config = json.loads((stage / "signing.private.json").read_text())
            config["deviceId"] = secrets.token_hex(16)
            (stage / "signing.private.json").write_text(json.dumps(config), encoding="utf-8")
            if not request.get("username") or not request.get("password"):
                raise SetupError("credentials_missing", "Enter your Momcozy email and password.")
            country = request.get("country", "DE")
            if country != "DE":
                raise SetupError("country_unsupported", "Only DE/EU accounts have been verified.")
            credentials = stage / "credentials.private.json"
            credentials.write_text(json.dumps({"email": request["username"], "password": request["password"], "countryCode": country}), encoding="utf-8")
            run_script("momcozy_login", stage, credentials, "--country", country)
            credentials.unlink()
            run_script("list_momcozy_devices", stage)
            try:
                for script in ("tuya_login", "tuya_camera_info"):
                    run_script(script, stage)
            except SetupError:
                from app_cache import restore
                app_result = restore(cache_data, stage, current=stage / "signing.private.json") if request.get("allowFallback", True) else None
                if not app_result:
                    raise
                config = json.loads((stage / "signing.private.json").read_text())
                config["deviceId"] = secrets.token_hex(16)
                (stage / "signing.private.json").write_text(json.dumps(config), encoding="utf-8")
                # Reuse the successful Momcozy login; retry only the SDK steps.
                for script in ("tuya_login", "tuya_camera_info"):
                    run_script(script, stage)
            run_script("make_bridge_config", stage)
            manifest = json.loads((stage / "cameras.private.json").read_text())
            if not manifest:
                raise SetupError("no_cameras", "The account did not return any supported cameras.")
            cameras = apply_options(request, stage, manifest)
            from app_cache import promote
            promote(cache_data, stage / "signing.private.json")
            app_result["appVersion"] = json.loads((stage / "signing.private.json").read_text()).get("appVersion", "3.3.0")
            # Publish manifest last: the desktop launcher cannot observe partial setup.
            for file in stage.glob("*.private.json"):
                if file.name != "cameras.private.json":
                    os.replace(file, data / file.name)
            os.replace(stage / "cameras.private.json", data / "cameras.private.json")
            signing.unlink(missing_ok=True)
            return {"ok": True, "cameraCount": len(manifest), "dataDir": str(data), "cameras": cameras, **app_result}
        os.replace(stage / "signing.private.json", signing)
        return {"ok": True, "prepared": True, **app_result}


def main():
    if sys.argv[1:] == ["--self-test"]:
        # Public, fixed native-runtime fixture only. Keep its traceback visible
        # in build logs without reading stdin or touching account configuration.
        result = handle({"command": "selfTest"})
        print(json.dumps(result))
        if not result.get("ok"):
            raise SystemExit(1)
        return
    if sys.argv[1:] == ["--help"]:
        print("Momcozy setup helper: send one JSON request on stdin. Commands: discover, prepareAndroid, prepareApks, preparePlay, prepareCached, importSigning, importConfig, configure.")
        return
    if len(sys.argv) > 1 and sys.argv[1] == "--internal":
        if getattr(sys, "frozen", False):
            sys.path.insert(0, str(Path(sys._MEIPASS) / "client"))
        name = sys.argv[2]
        if name not in SCRIPTS:
            raise SystemExit(2)
        sys.argv = [name, *sys.argv[3:]]
        runpy.run_module(name, run_name="__main__")
        return
    try:
        request = json.loads(sys.stdin.buffer.read(1024 * 1024 + 1))
        if not isinstance(request, dict):
            raise ValueError()
        result = handle(request)
    except SetupError as error:
        result = {"ok": False, "error": error.code, "message": error.message}
    except Exception:
        result = {"ok": False, "error": "setup_failed", "message": "Setup could not complete. Check the supplied files and USB connection."}
    print(json.dumps(result))


if __name__ == "__main__":
    main()
