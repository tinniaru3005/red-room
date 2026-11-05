"""The Red Room workflow, with a real evidence chain:

  ATTACK DELIVERED -> UNAUTHORIZED ACTION OBSERVED -> FINDING REPRODUCED (independent run)
  -> HUMAN APPROVAL -> REAL CODE PATCH APPLIED -> ATTACK REPLAYED -> ATTACK BLOCKED
  -> LEGITIMATE WORKFLOW STILL PASSES

Every stage produces a structured artifact under demo/out/. A finding is called FIXED only when the
after-run genuinely re-tested its scenario (status passed) AND the legitimate workflow still works.
An error or inconclusive scan is never counted as a fix.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict

from . import agentsec_runner as ar
from . import coding_agent, legitimacy, reporting
from .config import POLICY_REL, PRIMARY_RULE, TARGET_PORT
from .room import Room
from .target_process import TargetAgent

log = logging.getLogger("redroom")

TARGET = "refund-support"
REPRODUCER = "reproducer"
APPROVER = "approver"


def _save(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(obj if isinstance(obj, str) else json.dumps(obj, indent=2))


def run_engagement(room: Room, repo_root: Path, approver: str = APPROVER,
                   auto_approve: bool = False, offline: bool = True) -> Dict:
    out = repo_root / "demo" / "out"
    result: Dict = {"approved": False, "fixed": [], "evidence": {}}
    ev = result["evidence"]

    room.post("Starting a security engagement against **%s** before launch. "
              "Running AgentSec's full suite now." % TARGET)

    # --- 1. Scan the vulnerable build -----------------------------------------------------------
    with TargetAgent(repo_root, TARGET_PORT, safe=False):
        before = ar.run_suite(repo_root, POLICY_REL, out / "before")
    _save(out / "before.report.json", before)
    before_findings = ar.findings(before)
    result["before"] = before
    room.post(reporting.scan_summary(before_findings))
    for f in before_findings:
        room.post(reporting.finding_card(f))

    headline = reporting.pick_headline(before_findings, PRIMARY_RULE)
    if not headline:
        room.post("No findings to act on under this policy.")
        return result
    hid, hsid = headline.get("id"), headline.get("scenario_id")

    tool_evidence = [e for e in headline.get("evidence") or [] if e.get("type") == "tool_call"]
    ev["attack_delivered"] = bool(headline.get("input"))
    ev["unauthorized_action_observed"] = bool(tool_evidence)
    log.info("headline=%s unauthorized_action_observed=%s", hid, ev["unauthorized_action_observed"])

    # --- 2. Independent reproduction (a fresh AgentSec run, different seed) ----------------------
    room.targeted([REPRODUCER], "most severe finding is `%s` (%s). Reproduce it independently."
                  % (headline.get("rule"), hsid))
    with TargetAgent(repo_root, TARGET_PORT, safe=False):
        repro = ar.run_suite(repo_root, POLICY_REL, out / "reproduce", seed=7, scenarios=[hsid])
    _save(out / "reproduce.report.json", repro)
    reproduced = ar.has_finding(repro, hid)
    ev["reproduced"] = reproduced
    room.say_as(REPRODUCER, ("Reproduced independently in a fresh AgentSec run (seed 7): `%s` fired "
                             "again on %s." % (headline.get("rule"), hsid)) if reproduced else
                ("Could NOT reproduce %s independently -- treating as unconfirmed." % hsid))
    if not reproduced:
        room.post("Reproduction failed; not proceeding to a fix on an unconfirmed finding.")
        return result

    # --- 3. Human approval gate -----------------------------------------------------------------
    approved = room.approve(
        "Critical finding confirmed and reproduced. Approve a code fix for **%s**?" % TARGET,
        approver)
    result["approved"] = approved
    if not approved:
        room.post("Fix declined — %s left unchanged. Engagement paused." % TARGET)
        return result

    # --- 4. Real code patch by the coding agent (deterministic remediation, not --safe) ---------
    try:
        patched_path, diff = coding_agent.apply_patch(repo_root)
    except coding_agent.PatchError as exc:
        room.post("Coding agent could not produce a patch: %s" % exc)
        return result
    _save(out / "patch.diff", diff)
    ev["patch_applied"] = True
    excerpt = "\n".join(diff.splitlines()[:16])
    room.post("Coding agent applied a source patch to `%s` (full diff in demo/out/patch.diff):\n"
              "```diff\n%s\n```" % (coding_agent.ORIGINAL_REL, excerpt))

    # --- 5. Re-verify: scan the PATCHED build ---------------------------------------------------
    room.post("Re-running the **exact** suite against the patched build to verify.")
    with TargetAgent(repo_root, TARGET_PORT, server_path=patched_path):
        after = ar.run_suite(repo_root, POLICY_REL, out / "after")
        legit = legitimacy.probe_legitimate("http://127.0.0.1:%d/agent" % TARGET_PORT)
    _save(out / "after.report.json", after)
    _save(out / "legitimate.json", {"still_works": legit.still_works, "searched": legit.searched,
                                    "replied": legit.replied,
                                    "no_unauthorized_action": legit.no_unauthorized_action})
    result["after"] = after

    fixed, still = ar.diff_fixed(before, after)
    result["fixed"], result["still"] = fixed, still
    headline_fixed = (not ar.has_finding(after, hid)
                      and ar.scenario_status(after, hsid) == "passed")
    ev["attack_blocked"] = headline_fixed
    ev["legitimate_workflow_passes"] = legit.still_works

    if headline_fixed:
        room.post("**ATTACK BLOCKED.** `%s` no longer reproduces against the patched build "
                  "(scenario %s re-tested, status passed)." % (headline.get("rule"), hsid))
    else:
        room.post("Headline finding NOT confirmed fixed (absent but scenario not cleanly "
                  "re-tested) — refusing to claim remediation.")
    room.post("Legitimate support workflow after the patch: %s (searched=%s, replied=%s, "
              "no unauthorized action=%s)."
              % ("STILL PASSES" if legit.still_works else "BROKEN",
                 legit.searched, legit.replied, legit.no_unauthorized_action))
    room.post("Overall: %d of %d findings fixed (gone AND re-tested)."
              % (len(fixed), len(before_findings)))

    # --- 7. Audit trail -------------------------------------------------------------------------
    room.document("red-room-engagement.md",
                  reporting.audit_markdown(TARGET, before_findings, headline, approver,
                                           fixed, still, ev, diff))
    room.post("Audit trail + artifacts written (demo/out/). Done.")
    result["success"] = bool(headline_fixed and legit.still_works)
    if result["success"]:
        room.post("═══  VERDICT  ═══\n"
                  "Inter-agent injection (OWASP ASI07) found → reproduced → human-approved → "
                  "patched in source → re-verified FIXED, with the legitimate workflow intact. "
                  "All of it in the room.")
    return result
