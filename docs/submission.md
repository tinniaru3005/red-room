# Red Room — submission kit

## Project description (for the submission form)
**Red Room — collaborative agent red-teaming on Switch.** Teams increasingly run multiple AI agents
that read each other's messages in shared channels. That creates a new attack surface — one agent's
message can steer another into a dangerous action (OWASP ASI07, "prompt infection") — and there is no
shared, auditable way for a team to find such a bug, approve a fix, and prove it's gone.

Red Room runs the whole security workflow **inside a Switch room**: a red-team agent runs Invaris
AgentSec against a teammate agent and posts findings; the critical one is reproduced by an independent
run; a **human approves the fix in the room** (who may approve is enforced by Switch's addressing
policy); a coding agent applies a **real source patch**; and the red-team agent **re-runs the exact
suite** to prove the attack is blocked and the legitimate workflow still works — writing the full
audit trail to a room document. AgentSec is used unmodified as a dependency; the new ASI07 check ships
as an external AgentSec attack pack.

## Why Switch is indispensable (not an optional chat layer)
- **Human approval gate** is server-enforced by Switch's addressing policy — a security property we
  get from Switch, not an honour-system check in our code.
- **Multi-participant coordination** (red-team → reproducer → approver → coder) is the room.
- **The attack surface itself** — inter-agent injection — only exists because agents share a room.
- **The audit trail** is a room document every participant can see.
Remove Switch and there is no workflow, only a local CLI scanner.

## 60–90s live-demo script (exact)
| Narration | Action |
|---|---|
| "We're shipping a refund agent. The team red-teams it — in our chat room." | Show the Switch room (Mattermost) with the agents + you. |
| "I ask our security teammate to test it." | Type `@agentsec-redteam red-team refund-support before we ship`. |
| "AgentSec runs the full suite; here's the dangerous one — a refund triggered by a message relayed from another agent. OWASP ASI07. A normal scanner misses this." | Point at the 🔴 CRITICAL `room_inter_agent_injection` card. |
| "An independent re-run reproduces it." | Show the reproducer line. |
| "A human must approve — Switch decides who can." | Click/▶ approve in the room. |
| "The coding agent patches the real source — here's the diff." | Show the posted diff. |
| "Re-run the exact attack on the patched build: blocked. And the legit refund flow still works." | Show ATTACK BLOCKED + STILL PASSES + the room audit doc. |

Detailed version: `demo/DEMO.md`. Opening/closing in the README GIF.

## Backup demo plan (if the live Switch environment fails)
1. Run `redroom demo --offline --auto-approve` — identical workflow, no server; findings/patch/verify
   are the same real AgentSec runs (clearly labelled "simulated room").
2. Fall back to the README GIF (`assets/demo.gif`) and walk through `demo/sample-evidence/`
   (transcript, `patch.diff`, before/after summaries, `legitimate.json`).
Never present the offline run as live — the output and GIF are labelled OFFLINE.

## Submission checklist
- [ ] Public GitHub repo with README (GIF at top), architecture, why-switch, live runbook.
- [ ] **Record the live `redroom run` against Switch Console** (the one thing that proves Switch) and
      add that GIF/video. Use `scripts/demo.tape` (swap `redroom demo` → `redroom run`).
- [ ] Demo video (60–90s) per the script above.
- [ ] Submit on the WeMakeDevs/DevTools-Academy form with the description above + repo + video links.
- [ ] Verify `git clone … && just setup && just demo` works on a clean machine.
- [ ] (Optional, extra prizes) Best Blog post; `#HowISwitch` social post.
