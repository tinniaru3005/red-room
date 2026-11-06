"""A minimal Switch agent-protocol client: SSE down, HTTP up. Used only in live mode
(`redroom run`). Faithful to docs.switchagents.ai/.../internals/agent-protocol.

Flow: register (once) -> open the event stream with a reused connection id -> read
`connection_state` -> heartbeat every 2s -> `connect_to_room` -> call operations. Exact operation
argument names come from `GET /agents/{id}/ops`; call `discover_ops()` if the server's surface
differs from the defaults used here.
"""
from __future__ import annotations

import json
import threading
import time
import uuid
from typing import Dict, List, Optional

import requests


class SwitchClient:
    def __init__(self, base_url: str, api_key: str, agent_id: str):
        self.base = base_url.rstrip("/")
        self.api_key = api_key
        self.agent_id = agent_id
        self.connection_id = str(uuid.uuid4())
        self.cursor = 0
        self._beat_interval = 2.0
        self._stop = threading.Event()
        self._events: List[Dict] = []
        self._events_lock = threading.Lock()
        self._threads: List[threading.Thread] = []
        self._stream_error: Optional[str] = None
        self._beat_error: Optional[str] = None
        self._room_id: str = ""

    @staticmethod
    def register(base_url: str, registration_token: str, name: str, description: str) -> Dict:
        """Register a custom protocol agent via POST /agents (an always-on, message-exchanging
        integration profile). Returns {id, api_key}; the api_key is shown once."""
        r = requests.post(
            base_url.rstrip("/") + "/agents",
            headers={"Authorization": "Bearer " + registration_token},
            json={"name": name, "description": description,
                  "connector_type": "custom",
                  "overwrite": True,
                  "integration_profile": {
                      "connection_model": "always_on",
                      "message_exchange": True,
                      "pre_invocation_mediation": [],
                      "post_invocation_mediation": [],
                      "event_reporting": [],
                      "task_protocol": {"can_delegate": False, "can_accept": False}}},
            timeout=20)
        if r.status_code >= 400:
            raise SwitchClient.SwitchError(
                "registration failed (%s) at %s/agents: %s"
                % (r.status_code, base_url.rstrip("/"), r.text[:800]))
        return r.json()

    def _headers(self) -> Dict[str, str]:
        return {"Authorization": "Bearer " + self.api_key}

    class SwitchError(RuntimeError):
        """A live Switch call failed. Carries an actionable message for the operator."""

    def preflight(self) -> None:
        """Fail fast and clearly if the agent bridge isn't reachable at base_url."""
        try:
            r = requests.get(self.base + "/health", timeout=5)
        except requests.RequestException as e:
            raise SwitchClient.SwitchError(
                "cannot reach the Switch agent bridge at %s (%s). Is Switch Console running, and is "
                "SWITCH_BASE_URL the agent bridge URL? Check `curl %s/health`." % (self.base, e, self.base))
        if r.status_code >= 400:
            raise SwitchClient.SwitchError(
                "%s/health returned %s — that host/path is not the Switch agent bridge." % (self.base, r.status_code))

    def _wait_connection_state(self, timeout: float = 8.0) -> bool:
        deadline = time.time() + timeout
        while time.time() < deadline:
            with self._events_lock:
                if any(e.get("type") == "connection_state" for e in self._events):
                    return True
            time.sleep(0.2)
        return False

    def connect(self, room_id: str) -> Dict:
        self.preflight()
        self._start_stream(room_id)
        if not self._wait_connection_state():
            raise SwitchClient.SwitchError(
                "opened the event stream but never received `connection_state` from %s. The API key "
                "may be invalid, or the agent id wrong.%s"
                % (self.base, (" Stream error: %s" % self._stream_error) if self._stream_error else ""))
        self._start_heartbeat()
        self._room_id = room_id
        try:
            return self.call_op("connect_to_room", {"room_id": room_id})
        except requests.HTTPError as e:
            code = e.response.status_code if e.response is not None else "?"
            if code == 403:
                raise SwitchClient.SwitchError(
                    "connect_to_room was refused (403): agent %s is not a member of room %s. Invite "
                    "the agent to that room in Switch first." % (self.agent_id, room_id))
            raise SwitchClient.SwitchError("connect_to_room failed (%s): %s" % (code, e))

    def _start_stream(self, room_id: str) -> None:
        def run():
            url = (self.base + "/agents/%s/events" % self.agent_id)
            first = True
            # /events is a LONG POLL, not a persistent stream: the server closes it after
            # `timeout` seconds (default 10). Ask for a long window and reopen when it ends --
            # otherwise the connection lapses mid-engagement and ops fail with 409
            # "connection is not open".
            while not self._stop.is_set():
                params = {"connection_id": self.connection_id, "scope": "single",
                          "filter": "all", "start_from": "head", "rooms": room_id,
                          "timeout": 300}
                if not first:
                    params["last-event-id"] = str(self.cursor)
                first = False
                try:
                    with requests.get(url, headers={**self._headers(), "Accept": "text/event-stream"},
                                      params=params, stream=True, timeout=(10, None)) as resp:
                        event, data = None, []
                        for raw in resp.iter_lines(decode_unicode=True):
                            if self._stop.is_set():
                                break
                            if raw is None:
                                continue
                            if raw == "":
                                if data:
                                    self._on_frame(event, "\n".join(data))
                                event, data = None, []
                                continue
                            if raw.startswith(":"):
                                continue
                            if raw.startswith("event:"):
                                event = raw[6:].strip()
                            elif raw.startswith("data:"):
                                data.append(raw[5:].strip())
                            elif raw.startswith("id:"):
                                try:
                                    self.cursor = int(raw[3:].strip())
                                except ValueError:
                                    pass
                except requests.RequestException as e:
                    self._stream_error = str(e)
                    self._stop.wait(1.0)
        t = threading.Thread(target=run, daemon=True)
        t.start()
        self._threads.append(t)

    def _on_frame(self, event: Optional[str], data: str) -> None:
        try:
            obj = json.loads(data)
        except ValueError:
            return
        # Switch puts the event kind in the SSE `event:` line, not inside the JSON payload.
        # Carry it onto the object so the rest of the client can filter on `type`.
        if event and not obj.get("type"):
            obj["type"] = event
        if obj.get("type") == "connection_state":
            self._beat_interval = float(obj.get("heartbeat_interval_seconds") or 2.0)
            self.cursor = int(obj.get("cursor") or self.cursor)
        with self._events_lock:
            self._events.append(obj)

    def _start_heartbeat(self) -> None:
        def beat():
            while not self._stop.is_set():
                try:
                    r = requests.post(self.base + "/agents/%s/connection/beat" % self.agent_id,
                                      headers=self._headers(),
                                      json={"connection_id": self.connection_id, "cursor": self.cursor},
                                      timeout=5)
                    # A rejected heartbeat is why a long run gets evicted mid-engagement. Record it
                    # rather than swallowing it, so the failure names the real cause.
                    if r.status_code >= 400:
                        self._beat_error = "beat %s: %s" % (r.status_code, r.text[:200])
                    else:
                        self._beat_error = None
                except requests.RequestException as e:
                    self._beat_error = str(e)
                self._stop.wait(self._beat_interval)
        t = threading.Thread(target=beat, daemon=True)
        t.start()
        self._threads.append(t)

    def call_op(self, name: str, args: Dict, _retry: bool = True) -> Dict:
        r = requests.post(
            self.base + "/agents/%s/ops/%s" % (self.agent_id, name),
            headers={**self._headers(), "Content-Type": "application/json",
                     "X-Switch-Connection-Id": self.connection_id},
            json=args, timeout=30)
        # /events is a long poll; when it is re-established the server can rotate the
        # connection and the room binding is lost, so the next op fails with this 400.
        # Re-issue connect_to_room once and retry rather than failing the engagement.
        if (_retry and r.status_code == 400 and self._room_id and name != "connect_to_room"
                and "not connected to a room" in r.text.lower()):
            try:
                self.call_op("connect_to_room", {"room_id": self._room_id}, _retry=False)
            except SwitchClient.SwitchError:
                pass
            else:
                return self.call_op(name, args, _retry=False)
        if r.status_code >= 400:
            raise SwitchClient.SwitchError(
                "op `%s` failed (%s): %s%s" % (name, r.status_code, r.text[:600],
                 ("  [heartbeat: %s]" % self._beat_error) if self._beat_error else ""))
        return r.json().get("result", {})

    def discover_ops(self) -> Dict:
        r = requests.get(self.base + "/agents/%s/ops" % self.agent_id,
                         headers=self._headers(), timeout=20)
        r.raise_for_status()
        return r.json().get("operations", {})

    # The connected room is bound by the connection id header (see connect_to_room); these ops do
    # NOT take a room_id argument -- the server rejects unexpected keys. room_id stays on the method
    # only so SwitchRoom can mirror the offline room's interface.
    def post_message(self, room_id: str, body: str) -> Dict:
        return self.call_op("post_message", {"body": body})

    def send_targeted_message(self, room_id: str, target_names: List[str], body: str) -> Dict:
        return self.call_op("send_targeted_message",
                            {"body": body, "target_names": target_names})

    def create_room_document(self, room_id: str, name: str, content: str) -> Dict:
        return self.call_op("create_room_document",
                            {"name": name,
                             "description": "Red Room engagement audit trail",
                             "instructions": "Read-only record of the security engagement.",
                             "content": content})

    @staticmethod
    def _is_from(payload: dict, approver: str) -> bool:
        """Only the designated approver's word counts. Match the sender against the approver name
        across the identity fields Switch provides (a different participant's 'approve' is ignored)."""
        a = approver.strip().lower()
        for field in ("sender_name", "on_behalf_of", "sender"):
            v = str(payload.get(field) or "").lower()
            if v and a == v:   # exact, normalized match only -- never substring (a participant
                return True        # whose name is a substring of the approver's must NOT qualify)
        return False

    def request_approval(self, room_id: str, approver: str, prompt: str,
                         timeout_s: float = 300.0) -> bool:
        """Ask in-room and wait for a yes/no FROM THE APPROVER. Messages from anyone else are
        ignored; duplicate events are de-duplicated by message_id. Times out to False (deny)."""
        self.send_targeted_message(room_id, [approver],
                                   prompt + "\n\nReply `approve` or `decline`.")
        deadline = time.time() + timeout_s
        seen = 0
        processed = set()
        while time.time() < deadline:
            with self._events_lock:
                batch = self._events[seen:]
                seen = len(self._events)
            for ev in batch:
                if ev.get("type") != "message":
                    continue
                payload = ev.get("payload") or ev
                mid = payload.get("message_id")
                if mid is not None:
                    if mid in processed:
                        continue
                    processed.add(mid)
                if not self._is_from(payload, approver):
                    continue
                text = (payload.get("body") or "").strip().lower()
                if any(w in text for w in ("approve", "approved", "yes")):
                    return True
                if any(w in text for w in ("decline", "declined", "no", "reject")):
                    return False
            time.sleep(0.2)
        return False

    def close(self) -> None:
        self._stop.set()
