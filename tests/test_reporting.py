from redroom import reporting
from redroom.agentsec_runner import diff_fixed


def _f(fid, sid=None, sev="critical", rule="room_inter_agent_injection"):
    return {"id": fid, "scenario_id": sid or fid.split(":")[0], "severity": sev, "rule": rule,
            "title": "t", "observed_action": "o", "policy_violated": "p",
            "owasp": [{"id": "ASI07"}]}


def _rep(findings, scenarios):
    return {"findings": findings, "scenarios": scenarios}


def test_finding_card_has_key_bits():
    card = reporting.finding_card(_f("s1:room_inter_agent_injection", "s1"))
    assert "CRITICAL" in card and "ASI07" in card and "replay" in card


def test_scan_summary_counts():
    s = reporting.scan_summary([_f("a", "a"), _f("b", "b", sev="high")])
    assert "2 findings" in s.lower()


def test_pick_headline_prefers_pack_rule():
    fs = [_f("a", "a", sev="high", rule="secret_leak"), _f("b", "b", rule="room_inter_agent_injection")]
    assert reporting.pick_headline(fs, "room_inter_agent_injection")["id"] == "b"


def test_diff_fixed_requires_scenario_retested():
    before = _rep([_f("a", "sa"), _f("b", "sb")], [])
    after = _rep([_f("b", "sb")], [{"id": "sa", "status": "passed"}, {"id": "sb", "status": "findings"}])
    fixed, still = diff_fixed(before, after)
    assert [f["id"] for f in fixed] == ["a"]
    assert [f["id"] for f in still] == ["b"]


def test_inconclusive_is_not_a_fix():
    before = _rep([_f("a", "sa")], [])
    after = _rep([], [{"id": "sa", "status": "inconclusive"}])
    fixed, still = diff_fixed(before, after)
    assert fixed == []
    assert [f["id"] for f in still] == ["a"]


def test_audit_markdown_renders_chain():
    ev = {"attack_delivered": True, "unauthorized_action_observed": True, "reproduced": True,
          "approved": True, "patch_applied": True, "attack_blocked": True,
          "legitimate_workflow_passes": True}
    md = reporting.audit_markdown("refund-support", [_f("a", "sa")], _f("a", "sa"),
                                  "approver", [_f("a", "sa")], [], ev, "--- a\n+++ b\n")
    assert "Evidence chain" in md and "[x] Attack blocked after patch" in md
