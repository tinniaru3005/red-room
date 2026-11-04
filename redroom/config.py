from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


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
