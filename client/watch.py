"""Run local camera bridges and VLC; Ctrl+C stops only the bridges started here."""
import argparse
import json
import os
from pathlib import Path
import shutil
import signal
import socket
import subprocess
import sys
import threading
import time
from state import DATA

class ViewerError(ValueError):
    pass

def find_player():
    if sys.platform == "darwin":
        app = Path("/Applications/VLC.app/Contents/MacOS/VLC")
        if app.is_file():
            return str(app)
    if os.name == "nt":
        app = Path(os.environ.get("ProgramFiles", "C:/Program Files"))/"VideoLAN/VLC/vlc.exe"
        if app.is_file():
            return str(app)
    return shutil.which("vlc")

def camera_configs():
    manifest = DATA/"cameras.private.json"
    paths = ([DATA/name for name in json.loads(manifest.read_text())] if manifest.exists()
             else sorted(DATA.glob("bridge-*.private.json")))
    if not paths:
        raise ViewerError("No cameras configured. Run client/configure.py first.")
    result = []
    ports = set()
    for path in paths:
        if path.resolve().parent != DATA:
            raise ViewerError("Camera configuration must be in the private state directory.")
        config = json.loads(path.read_text())
        port = int(config["port"])
        name = config["camera-name"]
        if not 1024 <= port <= 65535 or port in ports:
            raise ViewerError("Camera ports must be unique and between 1024 and 65535.")
        if not name.startswith("bm04_") or not name[5:].isdigit():
            raise ViewerError("Expected a generated bm04_N camera name.")
        ports.add(port)
        result.append((path,port,name))
    return result

def ready(port):
    try:
        with socket.create_connection(("127.0.0.1",port),timeout=0.2):
            return True
    except OSError:
        return False

def run(args):
    player = None if args.no_player else find_player()
    if not args.no_player and not player:
        raise ViewerError("VLC is missing. Install VLC or use --no-player.")
    suffix = ".exe" if os.name == "nt" else ""
    binary = Path(__file__).resolve().parents[1]/"bin"/("momcozy-bridge"+suffix)
    if not binary.is_file():
        raise ViewerError("Bridge binary missing. Run scripts/setup.sh or build bridge/ first.")
    cameras = camera_configs()
    for _,port,_ in cameras:
        if ready(port):
            raise ViewerError(f"Local port {port} is already in use. Stop the other viewer first.")
    stop = threading.Event()
    previous = {}
    for sig in (signal.SIGINT,signal.SIGTERM):
        previous[sig] = signal.signal(sig,lambda *_:stop.set())
    children = []
    logs = []
    try:
        for config,port,name in cameras:
            runtime = DATA/"runtime"/name
            runtime.mkdir(mode=0o700,parents=True,exist_ok=True)
            log = (runtime/"bridge.log").open("w")
            logs.append(log)
            options = {"creationflags":subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {"start_new_session":True}
            child = subprocess.Popen([str(binary),str(config)],cwd=runtime,stdout=log,stderr=subprocess.STDOUT,**options)
            children.append(child)
            deadline = time.monotonic()+30
            while not ready(port):
                if child.poll() is not None:
                    raise ViewerError(f"{name}: bridge exited. Check private logs or renew the account session.")
                if stop.wait(0.2):
                    return
                if time.monotonic()>deadline:
                    raise ViewerError(f"{name}: bridge startup timed out.")
            url = f"rtsp://127.0.0.1:{port}/{name}"
            print(f"{name}: {url}",flush=True)
            if player:
                subprocess.Popen([player,"--no-one-instance","--rtsp-tcp","--network-caching=500",
                                  "--meta-title="+name,url],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        print("Viewer running. Keep this terminal open; Ctrl+C stops camera connections.",flush=True)
        deadline = time.monotonic()+args.seconds if args.seconds else float("inf")
        while not stop.wait(0.5) and time.monotonic()<deadline:
            if any(child.poll() is not None for child in children):
                raise ViewerError("A camera bridge stopped. Check private logs; restart or refresh the session.")
    finally:
        for child in children:
            if child.poll() is None:
                child.terminate()
        for child in children:
            try:
                child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait()
        for log in logs:
            log.close()
        for sig,handler in previous.items():
            signal.signal(sig,handler)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-player",action="store_true",help="Only serve RTSP; open a player yourself")
    parser.add_argument("--seconds",type=float,default=0,help="Stop after N seconds (0: wait for Ctrl+C)")
    args = parser.parse_args()
    if args.seconds < 0:
        parser.error("--seconds cannot be negative")
    try:
        run(args)
    except ViewerError as error:
        print(str(error),file=sys.stderr)
        return 1
    except (ValueError,OSError,KeyError):
        # Deliberately do not dump arbitrary server/configuration data.
        print("Viewer could not run. Check configuration, VLC, free ports and private logs. See README.md.",file=sys.stderr)
        return 1
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
