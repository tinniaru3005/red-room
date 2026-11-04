# Red Room — 2–3 minute demo script

Two ways to show it:

- **Offline (reliable, for recording):** `just demo` (or `redroom demo --offline --auto-approve`).
  Runs the whole loop in your terminal as a simulated Switch room. Every finding and the
  REPRODUCED → FIXED proof come from real AgentSec runs against the bundled agent.
- **Live (for the "it's really in chat" moment):** `redroom run` with Switch Console + a bridged
  Mattermost/Slack room (see README → Live mode). Identical workflow, real room.

## Two-column script (narration ‖ on-screen action)

| Narration (say) | Action (do) |
|---|---|
| "We're shipping a refund-support agent. Before launch, the team red-teams it — in chat." | Show the room (or `redroom demo`) with the participants. |
| "Our security teammate runs AgentSec's full suite against the live agent." | `agentsec-redteam` posts "Running…" then findings stream in. |
| "Here's the dangerous one: a message *relayed from another agent* made it issue a refund — inter-agent injection, OWASP ASI07. A normal scanner can't see this; our pack can." | Point at the 🔴 CRITICAL `room_inter_agent_injection` card. |
| "A second, independent AgentSec run — different seed — reproduces it. Not a fluke." | Show the reproducer confirmation line. |
| "The turning point: a human must approve. In a live room, Switch's addressing policy decides who can." | Click ✅ at the approval gate. |
| "Now a real fix — the coding agent patches the vulnerable code path. Here's the diff." | Show the `diff` block posted in the room. |
| "Re-run the exact suite against the patched build… blocked. And the legitimate refund workflow still works — we didn't just gag the agent." | Show **ATTACK BLOCKED** + **legitimate workflow STILL PASSES**. |
| "Every step is written to the room. None of this works without Switch." | Show the room engagement document. |

**Honesty note for Q&A:** offline mode simulates only the room transport and the human/reproducer;
the findings, the patch, and the re-verification are real AgentSec runs. The live Switch client is
code-complete but smoke-test it against your own server before demoing live.
