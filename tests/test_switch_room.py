"""SwitchRoom must post the actual message for each workflow step in live mode -- in particular the
independent-reproduction line, which an earlier version dropped as a 'waiting...' stub."""
from redroom.room import SwitchRoom


class _FakeClient:
    def __init__(self): self.posts = []
    def post_message(self, room_id, body): self.posts.append(("post", room_id, body))
    def send_targeted_message(self, room_id, targets, body): self.posts.append(("targeted", room_id, targets, body))
    def create_room_document(self, room_id, name, content): self.posts.append(("doc", room_id, name, content))
    def request_approval(self, room_id, approver, prompt): return True


def test_say_as_posts_real_text():
    c = _FakeClient()
    room = SwitchRoom(c, "room-1")
    room.say_as("reproducer", "Reproduced independently in a fresh AgentSec run (seed 7).")
    assert c.posts == [("post", "room-1", "Reproduced independently in a fresh AgentSec run (seed 7).")]
    assert "waiting" not in c.posts[0][2].lower()


def test_targeted_and_doc_reach_client():
    c = _FakeClient()
    room = SwitchRoom(c, "room-1")
    room.targeted(["reproducer"], "reproduce it")
    room.document("audit", "# content")
    kinds = [p[0] for p in c.posts]
    assert kinds == ["targeted", "doc"]
