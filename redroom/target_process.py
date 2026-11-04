"""Start/stop an agent-under-test as a local subprocess and wait until it answers. Can run the
original reference agent (vulnerable or --safe) or a patched build produced by the coding agent."""
from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

import requests


class TargetAgent:
    def __init__(self, repo_root: Path, port: int, safe: bool = False,
                 server_path: Optional[Path] = None):
        self.server = Path(server_path) if server_path else \
            repo_root / "agents" / "refund_support" / "server.py"
        self.port = port
        self.safe = safe
        self.proc = None

    @property
    def url(self) -> str:
        return "http://127.0.0.1:%d/agent" % self.port

    def start(self, timeout: float = 15.0) -> "TargetAgent":
        args = [sys.executable, str(self.server), "--port", str(self.port)]
        if self.safe:
            args.append("--safe")
        self.proc = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                requests.post(self.url, json={"messages": [{"role": "user", "content": "ping"}]},
                              timeout=2)
                return self
            except requests.RequestException:
                time.sleep(0.2)
        raise RuntimeError("target agent did not come up on %s" % self.url)

    def stop(self) -> None:
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.proc.kill()
        self.proc = None

    def __enter__(self): return self.start()
    def __exit__(self, *a): self.stop()
