"""The live approval gate only accepts a yes/no from the designated approver -- a different
participant's 'approve' must not count."""
from redroom.switch_client import SwitchClient


class _FakeClient(SwitchClient):
    def __init__(self, events):
        super().__init__("http://x", "k", "a")
        self._scripted = events
        self.sent = []

    def send_targeted_message(self, room_id, target_names, body):
        self.sent.append((target_names, body))
        with self._events_lock:
            self._events.extend(self._scripted)
        return {}


def _msg(sender, body):
    return {"type": "message", "payload": {"sender_name": sender, "body": body}}


def test_designated_approver_approves():
    c = _FakeClient([_msg("ada", "approve")])
    assert c.request_approval("room1", "ada", "ok?", timeout_s=2) is True


def test_other_participant_cannot_approve():
    c = _FakeClient([_msg("mallory", "approve"), _msg("ada", "decline")])
    assert c.request_approval("room1", "ada", "ok?", timeout_s=2) is False


def test_substring_name_is_not_the_approver():
    # Codex P1 regression: a participant ("ann") whose name is a substring of the approver
    # ("joanne") must NOT be accepted as the approver.
    c = _FakeClient([_msg("ann", "approve"), _msg("joanne", "decline")])
    assert c.request_approval("room1", "joanne", "ok?", timeout_s=2) is False


def test_partial_approver_name_times_out():
    # Only an exact match counts; a near/partial name never approves.
    c = _FakeClient([_msg("ann", "approve")])
    assert c.request_approval("room1", "joanne", "ok?", timeout_s=1) is False
