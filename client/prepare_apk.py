"""Extract SDK parameters from a compatible Momcozy ARM64 APK."""
import argparse
import gc
import hashlib
import json
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path
from state import DATA

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("base_apk", type=Path)
    parser.add_argument("arm64_apk", type=Path, help="arm64 split, or base APK if it contains the native library")
    args = parser.parse_args()
    from loguru import logger
    logger.remove()
    from androguard.core.apk import APK
    try:
        apk = APK(str(args.base_apk))
    except Exception:
        parser.error("One of the selected files is not a valid APK.")
    package = apk.get_package()
    app_version = apk.get_androidversion_name()
    app_version_code = apk.get_androidversion_code()
    if package != "com.lute.momcozy" or not app_version:
        parser.error("Expected a versioned com.lute.momcozy package.")
    certificates = {cert.dump() for cert in apk.get_certificates()}
    android = "{http://schemas.android.com/apk/res/android}"
    metadata = {node.get(android+"name"): node.get(android+"value")
                for node in apk.get_android_manifest_xml().iter("meta-data")}
    names = ("THING_SMART_APPKEY", "THING_SMART_SECRET")
    if not all(metadata.get(name) and not metadata[name].startswith("@") for name in names):
        parser.error("SDK manifest values are missing or require resource resolution.")
    del apk
    gc.collect()
    # Future versions are attempted in the bounded ARM64 emulator. Native
    # compatibility and subsequent Tuya authentication determine acceptance.
    try:
        arm_apk = APK(str(args.arm64_apk))
    except Exception:
        parser.error("One of the selected files is not a valid APK.")
    if (arm_apk.get_package() != package
            or arm_apk.get_androidversion_code() != app_version_code):
        parser.error("Base and ARM64 APKs must belong to the same app build.")
    if not certificates or certificates != {cert.dump() for cert in arm_apk.get_certificates()}:
        parser.error("Base and ARM64 APKs must carry matching signing certificates.")
    certificate = next(iter(certificates))
    certificate_hash = ":".join(f"{byte:02X}" for byte in hashlib.sha256(certificate).digest())
    parameters = {name: metadata[name] for name in names}
    parameters.update({
        "package": "com.lute.momcozy",
        "certificateHash": certificate_hash,
        "appVersion": app_version,
        "appVersionCode": app_version_code,
    })
    # Androguard retains the complete, very large base APK object graph. Drop
    # it before starting Unicorn and the signing stack so their peaks do not
    # overlap in memory-constrained Home Assistant containers.
    del arm_apk
    gc.collect()
    (DATA/"apk").mkdir(exist_ok=True)
    (DATA/"native").mkdir(exist_ok=True)
    target = DATA/"apk/base.apk"
    if args.base_apk.resolve() != target:
        shutil.copyfile(args.base_apk, target)
    try:
        with zipfile.ZipFile(args.arm64_apk) as archive:
            native = archive.read("lib/arm64-v8a/libthing_security_algorithm.so")
    except KeyError:
        parser.error("The ARM64 APK does not contain the required Momcozy native library.")
    except (OSError, zipfile.BadZipFile):
        parser.error("One of the selected files is not a valid APK.")
    (DATA/"native/libthing_security_algorithm.so").write_bytes(native)
    (DATA/"apk-parameters.private.json").write_text(json.dumps(parameters))
    from setup_wizard import script_command
    try:
        subprocess.run(script_command("decode_tuya_key"), check=True, timeout=120)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        parser.error("The Tuya key could not be decoded from this app version.")
    from tuya_mobile import parameters
    if (DATA/"signing.private.json").exists():
        parser.error("Signing configuration already exists. Use a fresh MOMCOZY_DATA_DIR for another APK.")
    try:
        parameters()
    except Exception:
        parser.error("SDK signing data could not be derived from this app version.")
    print("Local signing configuration prepared. No keys are printed or uploaded.")

if __name__ == "__main__":
    main()
