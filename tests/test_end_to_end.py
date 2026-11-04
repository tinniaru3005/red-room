"""Full offline engagement with the REAL evidence chain: spins up the reference agent, runs live
AgentSec scans, applies a real source patch, re-verifies, and checks the legitimate workflow still
works. Slower (subprocesses + several scans)."""
from redroom.config import repo_root
from redroom.orchestrator import run_engagement
from redroom.room import Room


class _Capture(Room):
    def __init__(self): self.posts = []
    def post(self, text): self.posts.append(text)
    def targeted(self, targets, text): self.posts.append(text)
    def say_as(self, who, text): self.posts.append(text)
    def approve(self, prompt, approver): return True
    def document(self, name, markdown): self.posts.append(markdown)


def test_full_loop_real_patch_and_proof():
    room = _Capture()
    result = run_engagement(room, repo_root(), auto_approve=True, offline=False)
    ev = result["evidence"]
    assert ev["unauthorized_action_observed"] is True
    assert ev["reproduced"] is True
    assert result["approved"] is True
    assert ev["patch_applied"] is True
    assert ev["attack_blocked"] is True
    assert ev["legitimate_workflow_passes"] is True
    assert result["success"] is True
    assert len(result["fixed"]) >= 1
    assert (repo_root() / "demo" / "out" / "patch.diff").read_text().strip()


def test_declined_approval_applies_no_patch():
    class _Decline(_Capture):
        def approve(self, prompt, approver): return False
    room = _Decline()
    result = run_engagement(room, repo_root(), offline=False)
    assert result["approved"] is False
    assert result["evidence"].get("patch_applied") is not True
    assert result.get("success") is not True
