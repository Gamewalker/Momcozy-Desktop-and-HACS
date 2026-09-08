"""Private runtime state, kept outside the checkout by default."""
import os
from pathlib import Path

os.umask(0o077)
DATA = Path(os.environ.get("MOMCOZY_DATA_DIR", Path.home()/".momcozy-desktop")).expanduser().resolve()
DATA.mkdir(mode=0o700, parents=True, exist_ok=True)
if os.name != "nt":
    DATA.chmod(0o700)
