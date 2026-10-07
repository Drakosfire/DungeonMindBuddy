from __future__ import annotations

from contextlib import ExitStack
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import time
import urllib.request

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.skipif(
    not Path("/proc/self/stat").exists(), reason="Linux launcher ownership witness"
)


def _ports() -> list[int]:
    with ExitStack() as stack:
        listeners = [stack.enter_context(socket.socket()) for _ in range(4)]
        for listener in listeners:
            listener.bind(("127.0.0.1", 0))
        return [listener.getsockname()[1] for listener in listeners]


def _live(pid: int, start: str) -> bool:
    try:
        fields = Path(f"/proc/{pid}/stat").read_text().rsplit(") ", 1)[1].split()
    except FileNotFoundError:
        return False
    return fields[0] != "Z" and fields[19] == start


def _ready(port: int) -> bool:
    try:
        with urllib.request.urlopen(
            f"http://127.0.0.1:{port}/docs", timeout=0.2
        ) as response:
            return response.status == 200
    except OSError:
        return False


def test_term_launcher_stops_owned_grandchildren_and_preserves_unrelated_listener(
    tmp_path: Path,
) -> None:
    root = tmp_path / "buddy"
    ui = root / "apps/live-control-ui"
    (ui / "node_modules").mkdir(parents=True)
    api = root / "apps/live_control_server/main.py"
    api.parent.mkdir(parents=True)
    api.touch()
    dms = tmp_path / "server"
    dms.mkdir()
    (dms / "dev_server.py").touch()
    launcher = root / "run"
    launcher.write_bytes((REPO_ROOT / "run").read_bytes())
    launcher.chmod(0o700)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    records = tmp_path / "processes"
    records.mkdir()
    # Fake uv/npm wrappers deliberately leave grandchildren when TERM'd, as
    # npm -> sh -> Vite does. Leaves ignore TERM to exercise verified KILL too.
    fixture = tmp_path / "process_tree.py"
    fixture.write_text("""import http.server,json,os,signal,subprocess,sys,time
from pathlib import Path
args=sys.argv[1:]
if args[0]=='--level':
 level,port,owned=int(args[1]),int(args[2]),args[3]=='owned'
else:
 level,owned=2,True
 if '--port' in args:port=int(args[args.index('--port')+1])
 else:port=int(os.environ['DUNGEONMIND_SERVER_PORT'])
fields=Path('/proc/self/stat').read_text().rsplit(') ',1)[1].split()
if owned:
 Path(os.environ['FIXTURE_RECORDS'],str(os.getpid())+'.json').write_text(json.dumps({'pid':os.getpid(),'start':fields[19],'level':level}))
if level:
 subprocess.Popen([sys.executable,__file__,'--level',str(level-1),str(port),'owned' if owned else 'control'])
 while True:time.sleep(.1)
else:
 if owned:signal.signal(signal.SIGTERM,signal.SIG_IGN)
 class Handler(http.server.BaseHTTPRequestHandler):
  def do_GET(self):self.send_response(200);self.end_headers();self.wfile.write(b'ok')
  def log_message(self,*args):pass
 http.server.HTTPServer(('127.0.0.1',port),Handler).serve_forever()
""")
    for command in ("uv", "npm"):
        path = bin_dir / command
        path.write_text(
            f'#!{sys.executable}\nimport runpy,sys\nsys.argv=[{str(fixture)!r}]+sys.argv[1:]\nrunpy.run_path({str(fixture)!r},run_name="__main__")\n'
        )
        path.chmod(0o700)
    ports = _ports()
    env = os.environ.copy()
    env.pop("DMB_AGENT_GRAPH_LOCAL_PROFILE", None)
    env.update(
        {
            "PATH": f"{bin_dir}:{env['PATH']}",
            "FIXTURE_RECORDS": str(records),
            "DUNGEONMIND_SERVER_ROOT": str(dms),
            "DUNGEONMIND_SERVER_PORT": str(ports[0]),
            "BUDDY_API_PORT": str(ports[1]),
            "BUDDY_UI_PORT": str(ports[2]),
            "RUN_NO_RELOAD": "1",
        }
    )
    control = subprocess.Popen(
        [sys.executable, str(fixture), "--level", "0", str(ports[3]), "control"],
        env=env,
    )
    log = tmp_path / "launcher.log"
    owned: list[dict] = []
    with log.open("w") as output:
        process = subprocess.Popen(
            ["bash", str(launcher)], env=env, stdout=output, stderr=subprocess.STDOUT
        )
        try:
            deadline = time.monotonic() + 15
            while time.monotonic() < deadline:
                assert process.poll() is None, log.read_text()
                if (
                    all(_ready(port) for port in ports)
                    and "Ctrl+C to stop" in log.read_text()
                ):
                    break
                time.sleep(0.1)
            else:
                pytest.fail(log.read_text())
            owned = [json.loads(path.read_text()) for path in records.glob("*.json")]
            assert len(owned) == 9  # Three root/child/grandchild trees.
            assert sorted(item["level"] for item in owned) == [
                0,
                0,
                0,
                1,
                1,
                1,
                2,
                2,
                2,
            ]
            process.terminate()
            assert process.wait(timeout=10) == 0, log.read_text()
            assert not any(_ready(port) for port in ports[:3]), log.read_text()
            assert not any(_live(item["pid"], item["start"]) for item in owned), (
                log.read_text()
            )
            assert control.poll() is None and _ready(ports[3])
        finally:
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=10)
            # Test failure cleanup also uses birth identities, never groups/ports.
            for path in records.glob("*.json"):
                item = json.loads(path.read_text())
                if _live(item["pid"], item["start"]):
                    os.kill(item["pid"], signal.SIGKILL)
            control.terminate()
            control.wait(timeout=5)
