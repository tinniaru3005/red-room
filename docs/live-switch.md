# Live Switch mode — exact setup & run

`redroom demo` simulates the room so the loop runs from a clean clone. **Live mode (`redroom run`)
drives the identical workflow through a real Switch server** — this is the evidence that Switch does
the work. Two environments are involved:

- **[SWITCH]** — Switch Console / Gateway / your chat app (Mattermost). GUI + Docker.
- **[REPO]** — this `red-room` repository, in a terminal.

## A. Set up Switch  **[SWITCH]**
1. Install **Switch Console** + Docker and start it: <https://docs.switchagents.ai/switch-rooms/getting-started>.
   The local server includes Mattermost. Confirm the agent bridge is up (default `:8000`):
   `curl http://localhost:8000/health`  → expect `200`.
2. In the **Gateway**, open **Registration keys** and create one. Copy it — this is your
   `SWITCH_REGISTRATION_TOKEN`. (The user that key belongs to becomes the agent's owner.)

## B. Register the Red Room agent  **[REPO]**
```bash
cd ~/Documents/red-room
python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"
cp .env.example .env
# edit .env: set SWITCH_BASE_URL=http://localhost:8000  and  SWITCH_REGISTRATION_TOKEN=<the key>
.venv/bin/redroom register        # POST /agents with an always-on integration profile
# -> prints SWITCH_AGENT_ID and SWITCH_API_KEY (the API key is shown ONCE). Put both in .env.
```

## C. Put the agent in a room  **[SWITCH]**
- **Mattermost:** each agent has its own bot account, so **adding the `agentsec-redteam` bot to a
  channel creates the room.** Create/choose a channel, add the bot, and join it yourself (you are the
  approver).
- Get the room's id for `SWITCH_ROOM_ID`: the **Gateway → Rooms** page lists rooms with their ids.
  Put it in `.env`.

## D. Run the live engagement  **[REPO]**
```bash
# .env now has SWITCH_BASE_URL, SWITCH_API_KEY, SWITCH_AGENT_ID, SWITCH_ROOM_ID
.venv/bin/redroom run --approver "<your-mattermost-username>"
```
Then **watch the Mattermost channel**: findings post, the reproduction line appears, and when it asks
for approval, **type `approve` in the channel** (only your approver reply counts). The patch diff
posts, the re-verification runs, and the audit document is written to the room.

## Environment variables
| Var | Where from | Needed for |
|---|---|---|
| `SWITCH_BASE_URL` | the agent bridge URL (`:8000` local) | all live calls |
| `SWITCH_REGISTRATION_TOKEN` | Gateway → Registration keys | `redroom register` only |
| `SWITCH_AGENT_ID` | printed by `redroom register` (or Gateway → Agents) | `redroom run` |
| `SWITCH_API_KEY` | printed by `redroom register` (shown once) | `redroom run` |
| `SWITCH_ROOM_ID` | Gateway → Rooms (after inviting the agent) | `redroom run` |

## How approval & delivery work (why this is sound)
In Switch, **membership decides what an agent is shown; addressing decides what it may act on.** The
agent is a room member, so it receives your `approve` message regardless of its addressing policy —
and `redroom run` reads that message off the event stream and matches it to the named approver. You
do **not** need to widen the agent's addressing policy for the approval to register.

## Recording (see scripts/)
- Offline GIF (anywhere): `vhs scripts/demo.tape` → `assets/demo.gif`.
- **Live** MP4 + GIF: `vhs scripts/demo-live.tape` → `assets/demo-live.mp4`, `assets/demo-live.gif`
  (does not touch the offline GIF). After you confirm it, swap it into the README:
  `cp assets/demo-live.gif assets/demo.gif`. To shrink/speed a long capture:
  `ffmpeg -i assets/demo-live.mp4 -vf "setpts=0.6*PTS,fps=12,scale=1000:-1:flags=lanczos" assets/demo.gif`

## Troubleshooting
| Symptom | Cause | Fix |
|---|---|---|
| `cannot reach the Switch agent bridge` | wrong `SWITCH_BASE_URL` / Switch not running | start Switch; `curl $SWITCH_BASE_URL/health` = 200; use the bridge URL, not the Gateway |
| `never received connection_state` | bad `SWITCH_API_KEY`/`SWITCH_AGENT_ID` | re-copy from registration (key shown once) |
| `connect_to_room refused (403): not a member` | agent not in the room | add the `agentsec-redteam` bot to the channel; set the right `SWITCH_ROOM_ID` |
| approval never returns | approver name mismatch, or no reply | pass `--approver <your mattermost username>`; type `approve` in the channel |

`redroom run` **never falls back to the offline simulation** — on any live failure it prints the
reason and exits non-zero, so a clean run means real Switch calls succeeded.
