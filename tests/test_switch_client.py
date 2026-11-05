"""Verify the live Switch client sends the EXACT wire shapes the real Switch agent protocol
expects (this is what makes the live demo work first try). A tiny mock server captures the op
bodies; we assert no stray room_id, the required document fields, and the connection-id header.

These shapes were checked against the Switch source:
  post_message(body, thread_id=None)                      -- no room_id
  send_targeted_message(body, target_names, target_roles, thread_id)  -- no room_id
  create_room_document(name, description, instructions, content)      -- no room_id
"""
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from redroom.switch_client import SwitchClient

CAPTURED = []


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_POST(self):
        length = int(self.headers.get("Content-Length") or 0)
        body = json.loads(self.rfile.read(length) or b"{}")
        CAPTURED.append({"path": self.path, "body": body,
                         "conn": self.headers.get("X-Switch-Connection-Id")})
        data = json.dumps({"result": {"ok": True}}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def _server():
    srv = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, "http://127.0.0.1:%d" % srv.server_address[1]


def test_op_wire_shapes():
    CAPTURED.clear()
    srv, base = _server()
    try:
        c = SwitchClient(base, "api-key", "agent-1")
        c.post_message("room-xyz", "hello")
        c.send_targeted_message("room-xyz", ["reproducer"], "please reproduce")
        c.create_room_document("room-xyz", "audit", "# content")
    finally:
        srv.shutdown()

    by_op = {x["path"].rsplit("/", 1)[-1]: x for x in CAPTURED}

    pm = by_op["post_message"]
    assert pm["body"] == {"body": "hello"}          # no room_id
    assert pm["conn"] == c.connection_id            # connection-id header bound

    tm = by_op["send_targeted_message"]
    assert tm["body"] == {"body": "please reproduce", "target_names": ["reproducer"]}
    assert "room_id" not in tm["body"]

    doc = by_op["create_room_document"]
    assert doc["body"]["name"] == "audit" and doc["body"]["content"] == "# content"
    assert "description" in doc["body"] and "instructions" in doc["body"]
    assert "room_id" not in doc["body"]


def test_register_uses_agents_endpoint_with_profile():
    CAPTURED.clear()
    srv, base = _server()
    try:
        SwitchClient.register(base, "reg-token", "agentsec-redteam", "desc")
    finally:
        srv.shutdown()
    reg = CAPTURED[0]
    assert reg["path"].endswith("/agents")
    prof = reg["body"]["integration_profile"]
    assert prof["connection_model"] == "always_on" and prof["message_exchange"] is True
