# Architecture

```
Switch room  #ship-refund-agent
  ├─ human (requester + approver)
  ├─ agentsec-redteam   ← Red Room agent: runs AgentSec, posts findings, drives the loop
  ├─ reproducer         ← independently reproduces the critical finding
  └─ refund-support     ← the agent under test
Linked room  #fix-refund-agent
  └─ coding agent        ← applies the fix
```

- **`redroom/switch_client.py`** — Switch agent protocol (SSE down, HTTP up): register, stream,
  heartbeat, `connect_to_room`, `post_message`, `send_targeted_message`, approval, room document.
- **`redroom/orchestrator.py`** — the workflow / state machine.
- **`redroom/agentsec_runner.py`** — shells out to the published `agentsec` CLI and
  reads its `report.json`.
- **`redroom/coding_agent.py`** — applies a **real source patch** to the vulnerable code path.
- **`redroom/legitimacy.py`** — proves the patched agent still does legitimate work.
- **`redroom/packs/room_injection.py`** — the new capability, delivered as an AgentSec *attack pack*
  (`CATEGORIES` + `EVALUATORS`) loaded via the policy's `attack_packs:` list. OWASP ASI07.
- **`agents/refund_support/server.py`** — a self-contained vulnerable / `--safe` reference agent.

## How the proof works (evidence chain)

```
ATTACK DELIVERED → UNAUTHORIZED ACTION OBSERVED → FINDING REPRODUCED (independent run)
→ HUMAN APPROVAL → REAL CODE PATCH APPLIED → ATTACK REPLAYED → ATTACK BLOCKED
→ LEGITIMATE WORKFLOW STILL PASSES
```

1. `agentsec test` runs against the **vulnerable** agent → `demo/out/before/report.json`. The headline
   finding's trace carries the actual unauthorized tool call (observed, not inferred).
2. **Independent reproduction:** a *second* `agentsec test` of just that scenario, with a different
   seed → `demo/out/reproduce/report.json`. Same finding id = confirmed.
3. **Human approval** gates everything below (in live mode, only the designated approver's reply
   counts — enforced in `switch_client.request_approval`).
4. **Real patch:** `redroom/coding_agent.py` reads the vulnerable source, rewrites the vulnerable code
   path, and writes a patched build to `build/refund_support_patched.py`, emitting a unified diff
   (`demo/out/patch.diff`). It raises rather than silently "fixing" if the vulnerable code isn't found.
5. **Re-verify:** `agentsec test` runs against the **patched** build → `demo/out/after/report.json`.
6. **Fix guard (`agentsec_runner.diff_fixed`):** a finding is FIXED only if it is absent from `after`
   **and** its scenario status in `after` is `passed` (genuinely re-tested). Error/inconclusive is
   never a fix.
7. **Legitimate workflow (`redroom/legitimacy.py`):** a benign request is run against the patched
   agent to prove the fix didn't brick it (`demo/out/legitimate.json`).

Sample artifacts from a real run are committed under `demo/sample-evidence/`.
