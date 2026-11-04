# Live Switch mode

Red Room's offline demo (`redroom demo`) simulates the room so it runs from a clean clone. Live mode
(`redroom run`) drives the identical workflow through a real Switch server using the agent protocol.

## Setup
1. Install **Switch Console** + Docker (it bundles Mattermost for local rooms).
2. Create a room (optionally from `templates/red-room.template.yaml`) and note its id.
3. Configure credentials:
   ```bash
   cp .env.example .env     # set SWITCH_BASE_URL and SWITCH_REGISTRATION_TOKEN
   redroom register         # prints SWITCH_AGENT_ID + SWITCH_API_KEY -> add to .env
   # add SWITCH_ROOM_ID, then:
   redroom run
   ```

## What the client does (`redroom/switch_client.py`)
- Registers via `POST /agents/register-known`.
- Opens the SSE event stream with a reused connection id; **heartbeats every 2s**.
- `connect_to_room`, then `post_message` / `send_targeted_message`.
- **Approval gate with approver-identity enforcement**: only the designated approver's `approve`/
  `decline` counts; other participants' replies are ignored; duplicate events are de-duplicated.
- Writes the engagement audit to a room document.

## Status
The client is written to the published protocol spec with timeouts, retries and duplicate-event
protection. Smoke-test it against your own Switch Console before a live demo — it is not verified
end-to-end against a live server in this build.
