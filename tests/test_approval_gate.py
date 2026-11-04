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
