from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


def repo_root() -> Path:
    here = Path.cwd()
    if (here / "policies" / "redroom.agentsec.yaml").is_file():
        return here
    for parent in [here, *here.parents]:
        if (parent / "policies" / "redroom.agentsec.yaml").is_file():
            return parent
    raise SystemExit(
        "error: run redroom from the red-room repo root "
        "(could not find policies/redroom.agentsec.yaml)."
    )


def load_dotenv(root: Optional[Path] = None) -> None:
    """Load KEY=VALUE pairs from the repo's .env into the environment.

    The runbook tells you to fill in .env and then run `redroom`; without this the file is
    written but never read, and every live command fails with "set SWITCH_* first".
    Real environment variables win, so `VAR=... redroom run` still overrides the file.
    """
    try:
        base = root or repo_root()
    except SystemExit:
        return
    f = base / ".env"
    if not f.is_file():
        return
    for line in f.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip()
        if len(val) >= 2 and val[0] == val[-1] and val[0] in "\"'":
            val = val[1:-1]
        if key:
            os.environ.setdefault(key, val)


@dataclass
class SwitchConfig:
    base_url: str
    registration_token: str
    api_key: str
    agent_id: str
    room_id: str
    fix_room_id: str

    @classmethod
    def from_env(cls) -> "SwitchConfig":
        load_dotenv()
        return cls(
            base_url=os.environ.get("SWITCH_BASE_URL", "http://localhost:8000").rstrip("/"),
            registration_token=os.environ.get("SWITCH_REGISTRATION_TOKEN", ""),
            api_key=os.environ.get("SWITCH_API_KEY", ""),
            agent_id=os.environ.get("SWITCH_AGENT_ID", ""),
            room_id=os.environ.get("SWITCH_ROOM_ID", ""),
            fix_room_id=os.environ.get("SWITCH_FIX_ROOM_ID", ""),
        )


TARGET_PORT = 8900
TARGET_URL = os.environ.get("REDROOM_TARGET_URL", "http://127.0.0.1:%d/agent" % TARGET_PORT)
POLICY_REL = "policies/redroom.agentsec.yaml"
PACK_REL = "redroom/packs/room_injection.py"
PRIMARY_RULE = "room_inter_agent_injection"
