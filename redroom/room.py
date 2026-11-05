"""A room is where the workflow happens. Two implementations:

* `ConsoleRoom` -- an OFFLINE simulation of a Switch room, printed to your terminal, so the whole
  loop runs from a clean clone with no Switch server. Clearly labelled as a simulation.
* `SwitchRoom` -- the real thing: posts and approvals go through the Switch agent protocol.
"""
from __future__ import annotations

import sys
import time
from typing import List


class Room:
    def post(self, text: str) -> None: raise NotImplementedError
    def targeted(self, targets: List[str], text: str) -> None: raise NotImplementedError
    def say_as(self, who: str, text: str) -> None: raise NotImplementedError
    def approve(self, prompt: str, approver: str) -> bool: raise NotImplementedError
    def document(self, name: str, markdown: str) -> None: raise NotImplementedError


class ConsoleRoom(Room):
    """Offline simulation. The reproducer agent and the human are simulated locally; this is for
    development and for recording the demo without standing up Switch."""

    def __init__(self, auto_approve: bool = False, agent_name: str = "agentsec-redteam"):
        self.auto_approve = auto_approve
        self.agent = agent_name
        print("=" * 72)
        print("  Red Room — OFFLINE SIMULATION of a Switch room (#ship-refund-agent)")
        print("  (live mode runs the identical flow through the Switch protocol)")
        print("=" * 72)

    def _line(self, who: str, text: str) -> None:
        print("\n[%s]" % who)
        for ln in text.splitlines() or [""]:
            print("    " + ln)
        sys.stdout.flush()

    def post(self, text: str) -> None:
        self._line(self.agent, text)

    def targeted(self, targets: List[str], text: str) -> None:
        self._line(self.agent, "@%s %s" % (" @".join(targets), text))

    def say_as(self, who: str, text: str) -> None:
        self._line(who, text)

    def approve(self, prompt: str, approver: str) -> bool:
        self._line(self.agent, "%s\n(awaiting approval from @%s)" % (prompt, approver))
        if self.auto_approve:
            time.sleep(0.3)
            self._line(approver, "✅ Approved.")
            return True
        try:
            ans = input("\n    %s — approve? [y/N] " % approver).strip().lower()
        except EOFError:
            ans = "n"
        ok = ans in ("y", "yes")
        self._line(approver, "✅ Approved." if ok else "❌ Declined.")
        return ok

    def document(self, name: str, markdown: str) -> None:
        print("\n--- room document: %s ---" % name)
        print(markdown)
        print("--- end document ---")


class SwitchRoom(Room):
    """Live room, backed by a Switch agent-protocol client."""

    def __init__(self, client, room_id: str, fix_room_id: str = ""):
        self.client = client
        self.room_id = room_id
        self.fix_room_id = fix_room_id

    def post(self, text: str) -> None:
        self.client.post_message(self.room_id, text)

    def targeted(self, targets: List[str], text: str) -> None:
        self.client.send_targeted_message(self.room_id, targets, text)

    def say_as(self, who: str, text: str) -> None:
        # There is no separate reproducer participant in this build; the red-team agent reports the
        # independent re-run itself. Post the actual text so the live room shows the real step
        # (never a "waiting..." stub, which would drop a workflow message).
        self.client.post_message(self.room_id, text)

    def approve(self, prompt: str, approver: str) -> bool:
        return self.client.request_approval(self.room_id, approver, prompt)

    def document(self, name: str, markdown: str) -> None:
        self.client.create_room_document(self.room_id, name, markdown)
