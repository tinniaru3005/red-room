# Why Switch is essential (not a chat skin)

Red Room would not exist without Switch. The room is doing four load-bearing jobs at once:

1. **It is the coordination fabric.** The red-team agent, the reproducer, the human approver and
   the coding agent are separate participants that hand work to each other through the room --
   `send_targeted_message`, linked rooms, roles. Take the room away and there is no multi-party
   workflow, just a CLI.
2. **It is the human gate.** The fix is blocked until a human approves *in the room*, and **who may
   approve is enforced by Switch's addressing policy**, server-side -- not by an honour-system check
   in our code (enforced in `switch_client.request_approval`: a different participant's "approve"
   is ignored). That is a real security property Switch gives us for free.
3. **It is the attack surface.** The headline finding is **inter-agent prompt injection (OWASP
   ASI07)**: one participant's message steering another agent into a money/comms action. That
   vulnerability class only exists *because* agents share a room. Switch is what makes it real and
   testable.
4. **It is the audit trail.** The whole engagement -- finding, reproduction, approver, re-verification
   -- is written to a room document, visible to the whole team.

Remove Switch and all four collapse. That is the hackathon's bar: *the project should stop working
without it.*
