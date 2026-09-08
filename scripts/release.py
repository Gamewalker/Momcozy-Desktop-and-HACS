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
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
TARGETS = (("windows", "amd64"), ("linux", "amd64"), ("linux", "arm64"), ("darwin", "amd64"), ("darwin", "arm64"))


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
    args = parser.parse_args()
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
        "README.md": (ROOT / "docs/BINARIES.md").read_bytes(),
        **notices,
    }
    sums = []
    with tempfile.TemporaryDirectory(prefix="momcozy-release-") as temp:
        for system, arch in TARGETS:
            stem = f"momcozy-desktop-{args.version}-{system}-{arch}"
            binary_name = "momcozy-desktop" + (".exe" if system == "windows" else "")
            binary = Path(temp) / binary_name
            subprocess.run([go, "build", "-trimpath", "-ldflags", f"-s -w -X main.VERSION={args.version}", "-o", str(binary), "."],
                           cwd=ROOT / "bridge", env=dict(env, GOOS=system, GOARCH=arch), check=True)
            files = {binary_name: binary.read_bytes(), **common}
            archive = output / (stem + (".zip" if system == "windows" else ".tar.gz"))
            if system == "windows":
                with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
                    for name, contents in sorted(files.items()):
                        info = zipfile.ZipInfo(stem + "/" + name, date_time=(2026, 1, 1, 0, 0, 0))
                        info.compress_type = zipfile.ZIP_DEFLATED
                        info.external_attr = (0o755 if name == binary_name else 0o644) << 16
                        bundle.writestr(info, contents)
            else:
                with tarfile.open(archive, "w:gz") as bundle:
                    for name, contents in sorted(files.items()):
                        info = tarfile.TarInfo(stem + "/" + name)
                        info.size = len(contents)
                        info.mode = 0o755 if name == binary_name else 0o644
                        info.mtime = 0
                        bundle.addfile(info, io.BytesIO(contents))
            digest = hashlib.sha256(archive.read_bytes()).hexdigest()
            sums.append(f"{digest}  {archive.name}")
            print(f"Built {archive.name}", flush=True)
    (output / "SHA256SUMS").write_text("\n".join(sums) + "\n", encoding="ascii")


if __name__ == "__main__":
    main()


