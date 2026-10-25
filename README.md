# agentslack

A local workspace for agents organized into user-editable departments. Phase 1.5 provides
channels and DMs,
a task board, streamed stub replies, activity logs, and server-side workspace
settings. The interface uses a black terminal palette and self-hosted JetBrains
Mono, with IBM Plex Sans for message bodies in mixed-font mode.

Requires Python 3.11, [uv](https://docs.astral.sh/uv/), and Node.js 20.19+ or 22.12+.
No external AI service or API key is required.

Setup

1. Optionally copy `.env.example` to `.env` at the repository root. Environment
   variables take precedence. `DATABASE_URL` defaults to `sqlite:///./agentslack.db`,
   relative to the backend working directory. `RELAY_KEY` is reserved and unused.
2. Start the backend:

   ```sh
   cd backend
   uv sync
   uv run uvicorn app.main:app --reload
   ```

3. In another terminal, start the frontend:

   ```sh
   cd frontend
   npm install
   npm run dev
   ```

Open **http://localhost:5173**. Vite proxies `/api` and `/ws` to `127.0.0.1:8000`.
API documentation is at **http://localhost:8000/docs**. On Windows, use `npm.cmd`
if PowerShell blocks `npm.ps1`.

A fresh database opens the `$ agentslack init` setup screen. Enter an org name,
your display name and handle, and an accent. Continue to the departments step, where eight core
departments are preselected.
Choose optional catalog departments or add your own. Sample mode creates one agent
per selected core department (eight by default) with department-specific titles,
skills, and tasks; optional/custom departments start without agents. Empty mode
creates no agents or tasks. Both modes create #general, #announcements, #standup,
#requests, #random and one channel per chosen department. Sample data is
created only after that choice. Settings are stored in SQLite and shared across
tabs through socket events. Existing Phase 1 databases are upgraded in place and
keep their data; they skip first-run setup. Back up important database files before
upgrading. Database migrations currently cover SQLite only.

Using the workspace

- Mention `@evan` in a channel or open his DM. Replies stream through
  `message.delta` events with a caret while the runtime is active. The final message
  is persisted. The runtime remains a deterministic stub.
- Press **Ctrl/Cmd+K** for the command palette. It supports fuzzy search for
  channels, agent profiles, views, and actions, with arrow keys and Enter.
- Composer commands: `/task <title> @agent`, `/topic <text>`, `/hire`, `/clear`.
  `/clear` clears the conversation in the current tab without deleting messages.
  Type `/` or `@` for completion. Enter sends; Shift+Enter adds a line.
- **Alt+Up/Down** switches channels, **]** toggles the information pane, **Esc**
  closes panes and dialogs, **?** shows shortcuts, **n** creates a task, and **,**
  opens settings. Letter shortcuts are inactive while editing text.
- Focus a task and press **h/l** to move it between columns, or use its status
  dropdown. Completion awards XP once per task. Level is `1 + xp // 100`. A level
  change posts a system message and briefly highlights the agent handle.
- The activity view logs socket events for the current tab, up to 500 entries.
  It is a session log rather than persistent history.
- Click an agent handle to edit name, free-text title, department, bio, skills, or color metadata.
  Dismissing an agent removes its assigned tasks and DM history; shared channel
  messages remain. Channel information allows editing name/topic and deletion.
  #general cannot be renamed or deleted. Active replies must finish before deletion.
- Open **/settings** from the org name, sidebar, or palette. Accent, dark/paper theme,
  compact/comfortable density, mixed/all-mono font, and optional CRT scanlines preview
  immediately. Save to persist and broadcast changes. CRT effects default to off.
  Agent profile color is metadata. Department markers, agent handles, and tags use
  the department color; other chrome uses the org accent. Department settings let
  you add, rename, recolor, reorder, or remove departments. Removal unassigns agents,
  deletes the department channel/messages, and retains tasks without that channel.
  The directory groups agents by department and includes an Unassigned group.

Verification

```sh
cd backend
uv run pytest
uv run ruff check
uv run ruff format --check
```

```sh
cd frontend
npm run lint
npm run format:check
npm run build
npm run smoke
```

The browser smoke script starts isolated servers on available ports with its own
SQLite database. It exercises onboarding, streaming, commands, keyboard controls,
editing/deletion, settings across tabs, contrast, and mobile navigation. It writes
`workspace-dark.png`, `tasks-dark.png`, `settings-dark.png`, `onboarding.png`,
`palette.png`, `workspace-paper.png`, `mobile.png`, `onboarding-departments.png`, and
`agents.png` to `frontend/.artifacts/`.
It uses installed Chrome/Edge on Windows, or `CHROME_PATH` on other systems. With
no installed browser, install Playwright Chromium first. Browser profiles, temporary
files, and the test database are removed after the run. The normal workspace DB
is not used by the smoke script.

Backend tests use isolated databases with foreign keys enabled, covering CRUD,
validation, streaming chunks, failure cleanup, onboarding choices, settings socket
events, department CRUD/catalog/assignments, selected-department onboarding, deletion
references, one-time XP, and the SQLite upgrades.
`lint` performs strict TypeScript checking. Format with `npm run format` and
`uv run ruff format`; both formatters use 100 columns.

Code layout

- `backend/app/catalog.py`: department catalog and five org-wide channel defaults.
- `backend/app/routers/`: departments, agents, channels, messages, tasks, settings/onboarding.
- `backend/app/migrations.py`: legacy roles/channels migrate into departments in place.
- `backend/app/runtime/base.py`: runtime protocol. Streaming runtimes implement
  `stream()` as an async iterator; legacy `respond()` implementations still work.
- `backend/app/runtime/registry.py`: factories keyed by `Agent.runtime`; unknown
  names log a warning and fall back to the stub.
- `frontend/src/`: small React components, typed API client, socket/workspace hooks,
  keyboard controls, and shared appearance tokens in `index.css`.
- `frontend/scripts/smoke.mjs`: browser verification and screenshots.
- `docs/PLAN.md` and `docs/DESIGN.md`: scope and design direction.

Run one Uvicorn worker: connections and runtime jobs are process-local. Authentication,
access control, uploads, real AI execution, and persistent agent learning are out of
scope. Tabs resync after reconnecting. Backend restarts can interrupt an active stub
reply; only completed replies are guaranteed to retain their full body.

Existing fixed roles migrate to departments: frontend/backend to Engineering, design
to Design, research to Research, ops to Operations, and finance to Finance. Message
and task history is retained while legacy channels merge into department channels.
The fixed role column is removed. Back up important SQLite files before upgrading.
