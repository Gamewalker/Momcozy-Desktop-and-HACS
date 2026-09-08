#!/usr/bin/env python3
"""Build the native setup helper. Run with a dedicated build venv, on each target OS.

Install requirements-setup-build.txt first. The output directory must not exist.
Only public client Python sources are copied; APKs and user state are never inputs.
Windows requires a C compiler and a rebuilt PyInstaller bootloader for Unicorn:
set PYINSTALLER_COMPILE_BOOTLOADER=1 and PYINSTALLER_BOOTLOADER_WAF_ARGS=--no-cfg,
then pip install --force-reinstall --no-binary pyinstaller --no-cache-dir PyInstaller==6.22.2.
See https://pyinstaller.org/en/stable/common-issues-and-pitfalls.html#windows-executables-and-control-flow-guard-cfg
"""
import argparse
import hashlib
import http.client
import importlib.metadata as metadata
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
NAME = "momcozy-setup-helper"


def download(url, limit=64 * 1024 * 1024):
    """Retry transient public-source transport failures, never checksum failures."""
    for attempt in range(3):
        try:
            with urllib.request.urlopen(url, timeout=60) as response:
                data = response.read(limit + 1)
            if len(data) > limit:
                raise ValueError("Dependency source exceeds download size limit")
            return data
        except (urllib.error.URLError, OSError, http.client.HTTPException):
            if attempt == 2:
                raise
            time.sleep(attempt + 1)


def licenses(destination):
    """Keep metadata and notices for installed distributions, including bundled transitives."""
    destination.mkdir()
    inventory = []
    for dist in metadata.distributions():
        name = dist.metadata.get("Name", "unknown")
        safe = "".join(c if c.isalnum() or c in "-_." else "_" for c in name)
        folder = destination / (safe + "-" + dist.version)
        folder.mkdir(exist_ok=True)
        (folder / "METADATA.txt").write_text(dist.read_text("METADATA") or "", encoding="utf-8")
        count = 0
        for entry in dist.files or []:
            path = Path(str(entry))
            if not any(part.lower().startswith(("license", "copying", "notice")) for part in path.parts):
                continue
            source = Path(dist.locate_file(entry))
            if not source.is_file():
                continue
            # Flatten paths, including possible ../ entries from wheel RECORD.
            target = folder / (str(count) + "-" + source.name)
            shutil.copyfile(source, target)
            count += 1
        inventory.append({"name": name, "version": dist.version, "noticeFiles": count})
        if name.lower() in {"unicorn", "loguru"}:
            # Some wheels omit notices. Keep the matching public source archive,
            # including its notices, alongside the unmodified bundled library.
            package = json.loads(download(f"https://pypi.org/pypi/{name}/{dist.version}/json"))
            source = next(item for item in package["urls"] if item["packagetype"] == "sdist")
            archive = download(source["url"])
            if hashlib.sha256(archive).hexdigest() != source["digests"]["sha256"]:
                raise RuntimeError("Dependency source checksum mismatch")
            (folder / source["filename"]).write_bytes(archive)
    (destination / "inventory.json").write_text(json.dumps(inventory, indent=2), encoding="utf-8")
    candidates = [Path(sys.base_prefix) / "LICENSE.txt", Path(sys.base_prefix) / "LICENSE"]
    found = next((p for p in candidates if p.is_file()), None)
    # CPython embeds its license text even when the OS package omits LICENSE.txt.
    if found:
        shutil.copyfile(found, destination / "Python-LICENSE.txt")
    else:
        import builtins
        builtins.license._Printer__setup()
        (destination / "Python-LICENSE.txt").write_text("\n".join(builtins.license._Printer__lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="New onedir destination")
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists():
        parser.error("Output already exists; choose a new directory.")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="momcozy-setup-build-") as temp:
        staging = Path(temp)
        command = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--onedir",
                   "--name", NAME, "--distpath", str(staging / "dist"),
                   "--workpath", str(staging / "build"), "--specpath", str(staging),
                   "--paths", str(ROOT / "client")]
        for source in sorted((ROOT / "client").glob("*.py")):
            command += ["--add-data", str(source) + os.pathsep + "client",
                        "--hidden-import", source.stem]
        # Importing every androguard submodule loads its optional Frida CLI.
        # APK parsing needs core.apk and packaged resources only.
        command += ["--collect-data", "androguard", "--hidden-import", "androguard.core.apk"]
        for package in ("unicorn", "elftools", "cryptography", "argon2"):
            command += ["--collect-all", package]
        command.append(str(ROOT / "client/setup_wizard.py"))
        subprocess.run(command, cwd=ROOT, check=True)
        distribution = staging / "dist" / NAME
        licenses(distribution / "licenses")
        shutil.copyfile(ROOT / "LICENSE", distribution / "LICENSE")
        executable = distribution / (NAME + (".exe" if os.name == "nt" else ""))
        subprocess.run([str(executable), "--help"], check=True, timeout=30)
        smoke = subprocess.run([str(executable), "--stdin"], input='{"command":"selfTest"}',
                               capture_output=True, text=True, check=True, timeout=60)
        if not json.loads(smoke.stdout).get("nativeRuntime"):
            raise RuntimeError("Frozen APK/Unicorn runtime smoke test failed")
        shutil.copytree(distribution, output, symlinks=True)
    print(f"Built native setup helper: {output}")


if __name__ == "__main__":
    main()
