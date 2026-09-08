"""Authenticate and discover cameras without putting passwords on the command line."""
import argparse
import json
import subprocess
import sys
from pathlib import Path
from state import DATA

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("credentials", type=Path, help="INI file containing USERNAME and PASSWORD")
    args = parser.parse_args()
    if not (DATA/"signing.private.json").exists():
        parser.error("Run prepare_apk.py first, or privately import your signing configuration.")
    folder = Path(__file__).parent
    subprocess.run([sys.executable,str(folder/"momcozy_login.py"),str(args.credentials)],check=True)
    for script in ("tuya_login.py", "list_momcozy_devices.py", "tuya_camera_info.py", "make_bridge_config.py"):
        subprocess.run([sys.executable,str(folder/script)],check=True)
    count = len(json.loads((DATA/"camera-config.private.json").read_text()))
    print(f"Prepared {count} camera(s). Private files: {DATA}")

if __name__ == "__main__":
    try:
        main()
    except (subprocess.CalledProcessError, KeyError, ValueError):
        sys.exit("Configuration failed. Existing sessions may need a fresh login; no automatic retry.")
