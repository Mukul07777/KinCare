# Switch notes for KinCare

What we learned from docs.switchagents.ai (Switch Console v0.40.1), and how KinCare uses it.

## How agents join a room (two ways)

1. **Console-run agent** (no protocol code). In Switch Console: *Your Agents* -> `+` -> name, description,
   instructions, run location *This computer*, a **directory**, and an **agent provider** (Claude Code).
   Switch runs the coding agent in that directory whenever it is addressed in a room.
2. **Custom protocol agent** (our own process). `POST /agents` with a registration key (Gateway -> API Keys)
   returns `{id, api_key}` once. Then either:
   - post without a connection: `POST /agents/{id}/message` `{room_id, content}`, Bearer agent key; or
   - full connection: WebSocket `/agents/{id}/connection/ws` (SSE is deprecated), answer pings, act on
     `message` events where `payload.addressed` is true.
   Operations: `GET /agents/{id}/ops`, `POST /agents/{id}/ops/{op}` with `X-Switch-Connection-Id`.
   Useful ops: `post_message`, `send_targeted_message`, `read_context`, `create_room_document`,
   `update_room_document`, `create_reference`, `attach_reference_to_room`, `define_role`, `assume_role`.

Agent names: `^[a-z0-9][a-z0-9._-]*$`. New agents answer only their owner; widen with
`update_agent_detail` `addressing`: `owner_only` | `owner_and_owner_agents` | `anyone`.
Agents hand work to each other by @mention; there is no separate task protocol.

## KinCare design

| Agent | Kind | Job |
|---|---|---|
| `kincare-scan` | Console-run (Claude Code) | Strip/bill photo -> batch -> recall check -> Hindi/English reply |
| `kincare-pharmacist` | Console-run (Claude Code) | Same salt, clean maker, saving; asks the human pharmacist; records the decision |
| `kincare-dose` | Console-run (Claude Code) | Dose reminders, missed dose -> caregiver |
| `kincare-recall-watcher` | Custom protocol (Python) | Watches CDSCO alerts and posts on its own in the room when a family batch matches |

Console-run agents get a working directory under `switch/agents/<name>/` with their instructions and call
KinCare through one small CLI (`switch/kincare_cli.py`) that talks to the KinCare API on `localhost:8000`.
The watcher is a real protocol agent because it must speak first, without being asked.

Decisions and tasks are kept as **room documents** (`create_room_document` / `update_room_document`):
`Decisions` and `Tasks`, so everyone in the room reads the same record.

## Telegram

BotFather `/newbot` -> save token -> **Group Privacy: Turn off before adding the bot** -> Console Home ->
Messaging apps -> Connect -> Telegram (name, token, username) -> add bot to a group (Switch creates the
room) -> post a message -> Console Home -> Link account -> "This is me". DMs with the bot don't make rooms.

## Templates

Console -> Templates -> Import template (YAML). Format reference:
https://github.com/sandbox-quantum/switch/blob/main/docs/TEMPLATES.md (format versions 1 and 2).
Use an Official template's YAML as the starting point.
