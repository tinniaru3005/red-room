from __future__ import annotations

import argparse
import sys

from . import __version__
from .config import SwitchConfig, repo_root
from .orchestrator import APPROVER, run_engagement
from .room import ConsoleRoom, SwitchRoom


def _demo(args) -> int:
    room = ConsoleRoom(auto_approve=args.auto_approve)
    run_engagement(room, repo_root(), approver=args.approver,
                   auto_approve=args.auto_approve, offline=True)
    return 0


def _run(args) -> int:
    cfg = SwitchConfig.from_env()
    missing = [k for k in ("api_key", "agent_id", "room_id") if not getattr(cfg, k)]
    if missing:
        print("error: set SWITCH_%s in your environment (see .env.example). "
              "Register first with `redroom register`."
              % ", SWITCH_".join(m.upper() for m in missing), file=sys.stderr)
        return 2
    from .switch_client import SwitchClient
    client = SwitchClient(cfg.base_url, cfg.api_key, cfg.agent_id)
    try:
        client.connect(cfg.room_id)   # preflight + stream + connect_to_room; raises on failure
    except SwitchClient.SwitchError as e:
        print("Live Switch connection failed — NOT falling back to the offline simulation.\n  %s"
              % e, file=sys.stderr)
        client.close()
        return 2
    try:
        room = SwitchRoom(client, cfg.room_id, cfg.fix_room_id)
        print("Connected to Switch room %s as agent %s. Driving the live engagement."
              % (cfg.room_id, cfg.agent_id), file=sys.stderr)
        run_engagement(room, repo_root(), approver=args.approver,
                       auto_approve=False, offline=False)
    except Exception as e:  # surface the failing step; do not silently simulate
        print("Live engagement failed mid-run: %s" % e, file=sys.stderr)
        return 2
    finally:
        client.close()
    return 0


def _register(args) -> int:
    cfg = SwitchConfig.from_env()
    if not cfg.registration_token:
        print("error: set SWITCH_REGISTRATION_TOKEN (and SWITCH_BASE_URL) first.", file=sys.stderr)
        return 2
    from .switch_client import SwitchClient
    out = SwitchClient.register(cfg.base_url, cfg.registration_token, args.name,
                                "Red Room security teammate (AgentSec).")
    print("Registered. Add these to your environment:")
    print("  SWITCH_AGENT_ID=%s" % out.get("id"))
    print("  SWITCH_API_KEY=%s" % out.get("api_key"))
    print("(the API key is shown once).")
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="redroom",
                                description="Collaborative agent red-teaming on Switch (AgentSec).")
    p.add_argument("--version", action="version", version="red-room " + __version__)
    sub = p.add_subparsers(dest="command", required=True)

    d = sub.add_parser("demo", help="run the whole loop offline (no Switch server needed)")
    d.add_argument("--offline", action="store_true", help="simulate the room locally (default/only mode for demo)")
    d.add_argument("--auto-approve", action="store_true", help="approve the fix automatically (for recording)")
    d.add_argument("--approver", default=APPROVER, help="name shown at the human gate")
    d.set_defaults(func=_demo)

    r = sub.add_parser("run", help="run against a live Switch room (reads SWITCH_* env)")
    r.add_argument("--approver", default=APPROVER, help="the Switch user who may approve the fix")
    r.set_defaults(func=_run)

    g = sub.add_parser("register", help="register the Red Room agent with a Switch server")
    g.add_argument("--name", default="agentsec-redteam")
    g.set_defaults(func=_register)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
