"""Private runtime state, kept outside the checkout by default."""
import os
import json
import re
from pathlib import Path

os.umask(0o077)
DATA = Path(os.environ.get("MOMCOZY_DATA_DIR", Path.home()/".momcozy-desktop")).expanduser().resolve()
DATA.mkdir(mode=0o700, parents=True, exist_ok=True)
if os.name != "nt":
    DATA.chmod(0o700)


def app_version():
    file = DATA / "signing.private.json"
    if file.exists():
        value = json.loads(file.read_text(encoding="utf-8")).get("appVersion", "3.3.0")
        if isinstance(value, str) and re.fullmatch(r"[0-9A-Za-z.+_-]{1,40}", value):
            return value
    return "3.3.0"
