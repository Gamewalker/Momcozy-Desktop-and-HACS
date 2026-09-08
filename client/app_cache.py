"""Private, immutable app snapshots; only successful camera setup promotes one."""
import hashlib
import json
from pathlib import Path
import re
import shutil
import uuid

from setup_errors import SetupError


def digest(path):
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def signing_identity(path):
    config = json.loads(path.read_text(encoding="utf-8"))
    config.pop("deviceId", None)
    return config


def write_json(path, value):
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value), encoding="utf-8")
    temporary.replace(path)


def entry_path(data, key):
    if not isinstance(key, str) or not re.fullmatch(r"[0-9a-f]{32}", key):
        raise SetupError("cache_invalid", "The saved app cache is invalid.")
    root = data.resolve()
    entry = root / key
    if entry.resolve().parent != root:
        raise SetupError("cache_invalid", "The saved app cache points outside its directory.")
    return entry


def remember_candidate(data, base, arm, signing):
    from setup_wizard import private_dir
    root = data
    private_dir(root)
    key = uuid.uuid4().hex
    folder = entry_path(data, key)
    private_dir(folder)
    shutil.copyfile(base, folder / "base.apk")
    if base.resolve() != arm.resolve():
        shutil.copyfile(arm, folder / "arm64.apk")
    shutil.copyfile(signing, folder / "signing.private.json")
    config = json.loads(signing.read_text(encoding="utf-8"))
    metadata = {"appVersion": config.get("appVersion", "unknown"),
                "appVersionCode": config.get("appVersionCode", ""),
                "files": {p.name: digest(p) for p in folder.iterdir() if p.is_file()}}
    write_json(folder / "metadata.private.json", metadata)
    write_json(root / "candidate.private.json", {"entry": key})
    return metadata["appVersion"]


def read_entry(data, key):
    folder = entry_path(data, key)
    metadata = json.loads((folder / "metadata.private.json").read_text(encoding="utf-8"))
    files = metadata["files"]
    if not {"base.apk", "signing.private.json"}.issubset(files) or not set(files).issubset({"base.apk", "arm64.apk", "signing.private.json"}):
        raise SetupError("cache_invalid", "The saved app cache is incomplete.")
    for name, expected in files.items():
        file = folder / name
        if file.resolve().parent != folder.resolve() or digest(file) != expected:
            raise SetupError("cache_invalid", "A saved app file failed its checksum.")
    return folder, metadata


def restore(data, stage, current=None):
    """Use only a promoted entry, never an untested candidate."""
    index = data / "known-good.private.json"
    if not index.exists():
        return None
    try:
        key = json.loads(index.read_text(encoding="utf-8"))["entry"]
        folder, metadata = read_entry(data, key)
        if current and current.exists() and signing_identity(current) == signing_identity(folder / "signing.private.json"):
            return None
        shutil.copyfile(folder / "signing.private.json", stage / "signing.private.json")
        return {"appVersion": metadata["appVersion"], "fallbackUsed": True}
    except SetupError:
        raise
    except (OSError, ValueError, KeyError, TypeError):
        raise SetupError("cache_invalid", "Could not read the saved working app version.") from None


def promote(data, signing):
    root = data
    candidate = root / "candidate.private.json"
    if not candidate.exists():
        return
    key = json.loads(candidate.read_text(encoding="utf-8"))["entry"]
    folder, metadata = read_entry(data, key)
    if signing_identity(signing) != signing_identity(folder / "signing.private.json"):
        return  # A fallback or a signing-file import was used instead.
    metadata = {"entry": key, "appVersion": metadata["appVersion"],
                "validation": "tuya-session-and-camera-metadata"}
    known = root / "known-good.private.json"
    if known.exists():
        shutil.copyfile(known, root / "previous-good.private.json")
    write_json(known, metadata)
