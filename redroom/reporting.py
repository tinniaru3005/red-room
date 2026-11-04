"""Turn an AgentSec finding into a message a room can read. No AgentSec internals -- just its
report.json shape."""
from __future__ import annotations

from typing import Dict, List

_EMOJI = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "⚪"}

# OWASP tags AgentSec's built-in mapper doesn't know for pack-provided rules.
_PACK_OWASP = {"room_inter_agent_injection": ["ASI07", "ASI01"]}


def _owasp(f: Dict) -> str:
    tags = [o.get("id") for o in (f.get("owasp") or []) if isinstance(o, dict) and o.get("id")]
    if not tags:
        tags = _PACK_OWASP.get(f.get("rule"), [])
    return ", ".join(tags) if tags else "-"


def finding_card(f: Dict) -> str:
    sev = (f.get("severity") or "low").lower()
    lines = [
        "%s  **%s** — %s" % (_EMOJI.get(sev, "⚪"), sev.upper(), f.get("title") or f.get("rule")),
        "OWASP: %s   ·   rule: `%s`" % (_owasp(f), f.get("rule")),
        "What happened: %s" % (f.get("observed_action") or ""),
        "Why it matters: %s" % (f.get("policy_violated") or ""),
        "Reproduce: `agentsec replay .agentsec/report.json --finding %s`" % f.get("id"),
    ]
    return "\n".join(lines)


def scan_summary(findings: List[Dict]) -> str:
    if not findings:
        return "AgentSec run complete — no findings."
    by = {}
    for f in findings:
        by[f.get("severity", "low")] = by.get(f.get("severity", "low"), 0) + 1
    order = ["critical", "high", "medium", "low"]
    parts = ["%d %s" % (by[s], s) for s in order if by.get(s)]
    return "AgentSec run complete — **%d findings** (%s)." % (len(findings), ", ".join(parts))


def pick_headline(findings: List[Dict], rule: str) -> Dict:
    for f in findings:
        if f.get("rule") == rule:
            return f
    order = {"critical": 4, "high": 3, "medium": 2, "low": 1}
    return max(findings, key=lambda f: order.get(f.get("severity", "low"), 0)) if findings else {}


def _chain(ev: Dict) -> str:
    steps = [
        ("Attack delivered", ev.get("attack_delivered")),
        ("Unauthorized action observed", ev.get("unauthorized_action_observed")),
        ("Finding reproduced (independent run)", ev.get("reproduced")),
        ("Human approval", ev.get("approved", True)),
        ("Code patch applied", ev.get("patch_applied")),
        ("Attack blocked after patch", ev.get("attack_blocked")),
        ("Legitimate workflow still passes", ev.get("legitimate_workflow_passes")),
    ]
    return "\n".join("- [%s] %s" % ("x" if ok else " ", label) for label, ok in steps)


def audit_markdown(target, before, headline, approver, fixed, still, ev, diff=""):
    lines = [
        "# Red Room engagement — %s" % target,
        "",
        "## Evidence chain",
        _chain(ev),
        "",
        "## 1. Findings (vulnerable build)",
        scan_summary(before),
        "",
        "## 2. Headline finding",
        finding_card(headline) if headline else "-",
        "",
        "## 3. Human approval",
        "Approved by: %s" % approver,
        "",
        "## 4. Code patch (applied only after approval)",
        "```diff",
        "\n".join((diff or "").splitlines()[:40]) or "(no diff)",
        "```",
        "",
        "## 5. Re-verification (patched build)",
        "Fixed (gone AND re-tested): %d / %d findings." % (len(fixed), len(before)),
    ]
    if still:
        lines.append("Still present: %d." % len(still))
    lines += ["Attack blocked after patch: %s." % ev.get("attack_blocked"),
              "Legitimate workflow still passes: %s." % ev.get("legitimate_workflow_passes"),
              "", "_Every step above happened in this room. Switch is the coordination fabric, the "
              "human gate, and this audit trail._"]
    return "\n".join(lines)
