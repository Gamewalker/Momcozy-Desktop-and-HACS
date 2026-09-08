"""Extract SDK parameters from the user's own Android 3.3.0 APKs."""
import argparse
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
    apk = APK(str(args.base_apk))
    if apk.get_package() != "com.lute.momcozy" or apk.get_androidversion_name() != "3.3.0":
        parser.error("Only com.lute.momcozy 3.3.0 has been verified; refusing unknown native code.")
    android = "{http://schemas.android.com/apk/res/android}"
    metadata = {node.get(android+"name"): node.get(android+"value")
                for node in apk.get_android_manifest_xml().iter("meta-data")}
    names = ("THING_SMART_APPKEY", "THING_SMART_SECRET")
    if not all(metadata.get(name) and not metadata[name].startswith("@") for name in names):
        parser.error("SDK manifest values are missing or require resource resolution.")
    (DATA/"apk").mkdir(exist_ok=True)
    (DATA/"native").mkdir(exist_ok=True)
    target = DATA/"apk/base.apk"
    if args.base_apk.resolve() != target:
        shutil.copyfile(args.base_apk, target)
    with zipfile.ZipFile(args.arm64_apk) as archive:
        native = archive.read("lib/arm64-v8a/libthing_security_algorithm.so")
    (DATA/"native/libthing_security_algorithm.so").write_bytes(native)
    (DATA/"apk-parameters.private.json").write_text(json.dumps({name:metadata[name] for name in names}))
    from setup_wizard import script_command
    subprocess.run(script_command("decode_tuya_key"), check=True)
    from tuya_mobile import parameters
    if (DATA/"signing.private.json").exists():
        parser.error("Signing configuration already exists. Use a fresh MOMCOZY_DATA_DIR for another APK.")
    parameters()
    print("Local signing configuration prepared. No keys are printed or uploaded.")

if __name__ == "__main__":
    main()
