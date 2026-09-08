#!/usr/bin/env python3
"""Build public release archives from source only; never include local configuration.

Usage: python scripts/release.py --version v0.1.0 --go /path/to/go --output /path/to/releases
Build dependencies: Go (go.mod version), Python 3.10+, network access for Go modules.
"""
import argparse
import hashlib
import io
import json
import os
import re
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
TARGETS = (("windows", "amd64"), ("linux", "amd64"), ("linux", "arm64"), ("darwin", "amd64"), ("darwin", "arm64"))


def helper_entries(helper, windows=False):
    """Preserve framework links without allowing links outside the private-free input."""
    helper = helper.resolve()
    files, modes, links = {}, {}, {}
    for path in helper.rglob("*"):
        name = "setup-helper/" + path.relative_to(helper).as_posix()
        if path.suffix.lower() == ".apk" or ".private." in path.name:
            raise ValueError("Private configuration or APK found in helper distribution")
        if path.is_symlink():
            target = os.readlink(path)
            if windows or Path(target).is_absolute():
                raise ValueError("Unsupported absolute or Windows helper symlink")
            try:
                path.resolve(strict=True).relative_to(helper)
            except (ValueError, OSError, RuntimeError):
                raise ValueError("Broken or escaping helper symlink") from None
            links[name] = Path(target).as_posix()
        elif path.is_file():
            files[name] = path.read_bytes()
            modes[name] = 0o755 if path.stat().st_mode & 0o111 else 0o644
        elif not path.is_dir():
            raise ValueError("Unsupported helper filesystem entry")
    return files, modes, links


def documentation():
    """Put linked guides alongside the archive README; source links go to GitHub."""
    files = {}
    for path in (ROOT / "docs").glob("*.md"):
        body = path.read_text(encoding="utf-8")
        body = re.sub(r"\]\(\.\./([^\s)]+)\)",
                      r"](https://github.com/Gamewalker/Momcozy-Desktop-and-HACS/blob/main/\1)", body)
        files[path.name] = body.encode("utf-8")
    files["README.md"] = files["BINARIES.md"]
    return files


def verify_archive(archive, stem, binary_name, has_helper):
    """Exercise the extracted layout, not the pre-archive build directory."""
    with tempfile.TemporaryDirectory(prefix="momcozy-release-smoke-") as temp:
        if archive.suffix == ".zip":
            with zipfile.ZipFile(archive) as bundle:
                bundle.extractall(temp)
        else:
            with tarfile.open(archive) as bundle:
                bundle.extractall(temp, filter="data")
        root = Path(temp) / stem
        subprocess.run([str(root / binary_name), "--version"], check=True, timeout=30)
        if has_helper:
            helper = root / "setup-helper" / ("momcozy-setup-helper" + (".exe" if os.name == "nt" else ""))
            subprocess.run([str(helper), "--help"], check=True, timeout=30)
            result = subprocess.run([str(helper), "--stdin"], input='{"command":"selfTest"}',
                                    capture_output=True, text=True, check=True, timeout=60)
            if not json.loads(result.stdout).get("nativeRuntime"):
                raise RuntimeError("Extracted helper failed native runtime test")


def module_licenses(go, env):
    raw = subprocess.check_output([go, "list", "-m", "-json", "all"], cwd=ROOT / "bridge", env=env, text=True)
    decoder = json.JSONDecoder()
    files = {}
    while raw.strip():
        module, end = decoder.raw_decode(raw.lstrip())
        raw = raw.lstrip()[end:]
        directory = module.get("Dir")
        if not directory or module.get("Main"):
            continue
        found = False
        for path in Path(directory).iterdir():
            if path.is_file() and path.name.upper().startswith(("LICENSE", "COPYING", "NOTICE")):
                files[f"licenses/dependencies/{module['Path']}@{module['Version']}/{path.name}"] = path.read_bytes()
                found = True
        if not found and module["Path"] == "github.com/mdp/qrterminal":
            files[f"licenses/dependencies/{module['Path']}@{module['Version']}/LICENSE"] = (ROOT / "scripts/release-licenses/qrterminal-LICENSE").read_bytes()
            files["licenses/dependencies/qrterminal-license-source.md"] = (ROOT / "scripts/release-licenses/README.md").read_bytes()
            found = True
        if not found:
            raise RuntimeError(f"Missing license for dependency {module['Path']}; inspect before release")
    return files


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", required=True)
    parser.add_argument("--go", default="go")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--target", choices=[f"{system}/{arch}" for system, arch in TARGETS])
    parser.add_argument("--setup-helper", type=Path, help="Native helper onedir; requires matching --target")
    parser.add_argument("--verify-native", action="store_true", help="Extract and execute archive on its native build runner")
    args = parser.parse_args()
    if args.setup_helper and not args.target:
        parser.error("--setup-helper requires a single matching --target")
    if args.verify_native and not args.target:
        parser.error("--verify-native requires a single native --target")
    helper_files = {}
    helper_modes = {}
    helper_links = {}
    if args.setup_helper:
        helper = args.setup_helper.resolve()
        expected = "momcozy-setup-helper" + (".exe" if args.target.startswith("windows/") else "")
        if not (helper / expected).is_file():
            parser.error("Setup helper executable is missing")
        try:
            helper_files, helper_modes, helper_links = helper_entries(helper, args.target.startswith("windows/"))
        except ValueError as error:
            parser.error(str(error))
    if not args.version.startswith("v") or any(c not in "v0123456789.-abcdefghijklmnopqrstuvwxyz" for c in args.version):
        parser.error("Use a release version such as v0.1.0")
    go = shutil.which(args.go) or str(Path(args.go).resolve())
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, CGO_ENABLED="0")
    env.pop("GOOS", None)
    env.pop("GOARCH", None)
    subprocess.run([go, "mod", "download"], cwd=ROOT / "bridge", env=env, check=True)
    notices = module_licenses(go, env)
    goroot = Path(subprocess.check_output([go, "env", "GOROOT"], cwd=ROOT / "bridge", env=env, text=True).strip())
    common = {
        "LICENSE": (ROOT / "LICENSE").read_bytes(),
        "licenses/Go-LICENSE": (goroot / "LICENSE").read_bytes(),
        "licenses/bridge-LICENSE": (ROOT / "bridge/LICENSE").read_bytes(),
        "NOTICE.md": (ROOT / "NOTICE.md").read_bytes(),
        **documentation(),
        **notices,
    }
    sums = []
    with tempfile.TemporaryDirectory(prefix="momcozy-release-") as temp:
        for system, arch in ([tuple(args.target.split("/"))] if args.target else TARGETS):
            stem = f"momcozy-desktop-{args.version}-{system}-{arch}"
            binary_name = "momcozy-desktop" + (".exe" if system == "windows" else "")
            binary = Path(temp) / binary_name
            subprocess.run([go, "build", "-trimpath", "-ldflags", f"-s -w -X main.VERSION={args.version}", "-o", str(binary), "."],
                           cwd=ROOT / "bridge", env=dict(env, GOOS=system, GOARCH=arch), check=True)
            files = {binary_name: binary.read_bytes(), **common, **helper_files}
            archive = output / (stem + (".zip" if system == "windows" else ".tar.gz"))
            if system == "windows":
                with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
                    for name, contents in sorted(files.items()):
                        info = zipfile.ZipInfo(stem + "/" + name, date_time=(2026, 1, 1, 0, 0, 0))
                        info.compress_type = zipfile.ZIP_DEFLATED
                        info.external_attr = (0o755 if name == binary_name else helper_modes.get(name, 0o644)) << 16
                        bundle.writestr(info, contents)
            else:
                with tarfile.open(archive, "w:gz") as bundle:
                    for name, contents in sorted(files.items()):
                        info = tarfile.TarInfo(stem + "/" + name)
                        info.size = len(contents)
                        info.mode = 0o755 if name == binary_name else helper_modes.get(name, 0o644)
                        info.mtime = 0
                        bundle.addfile(info, io.BytesIO(contents))
                    for name, target in sorted(helper_links.items()):
                        info = tarfile.TarInfo(stem + "/" + name)
                        info.type = tarfile.SYMTYPE
                        info.linkname = target
                        info.mode = 0o777
                        info.mtime = 0
                        bundle.addfile(info)
            if args.verify_native:
                verify_archive(archive, stem, binary_name, bool(args.setup_helper))
            digest = hashlib.sha256(archive.read_bytes()).hexdigest()
            sums.append(f"{digest}  {archive.name}")
            print(f"Built {archive.name}", flush=True)
    (output / "SHA256SUMS").write_text("\n".join(sums) + "\n", encoding="ascii")


if __name__ == "__main__":
    main()
