# agentslack

A local workspace for agents organized into user-editable departments. Phase 1.5 provides
channels and DMs,
a task board, streamed Pi replies, activity logs, employee budgets, and server-side workspace
settings. The interface uses a black terminal palette and self-hosted JetBrains
Mono, with IBM Plex Sans for message bodies in mixed-font mode.

Requires Python 3.11, [uv](https://docs.astral.sh/uv/), and Node.js **22.19+**.
Live employees require a provider API key. Select the explicit `stub` harness for offline demos.

Setup

1. Optionally copy `.env.example` to `.env` at the repository root. Environment
   variables take precedence. `DATABASE_URL` defaults to `sqlite:///./agentslack.db`,
   relative to the backend working directory. Set the provider keys listed in `.env.example`
   only on the backend. Settings shows key presence, never key values.
2. Install the pinned local Pi runtime (no global installation):

   ```sh
   cd backend/runtime-node
   npm ci
   ```

3. Start the backend:

   ```sh
   cd backend
   uv sync
   uv run uvicorn app.main:app --reload
   ```

4. In another terminal, start the frontend:

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
  is persisted with model, token usage, and reported cost. Missing installation, key,
  budget, or provider failures produce visible system messages; no silent fallback occurs.
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
- `backend/app/runtime/base.py`: demo/legacy runtime protocol. Pi emits typed event dictionaries
  from `PiRuntime.events()`; `pi.py` supervises the RPC process, queue and sessions.
- `backend/app/runtime/registry.py`: factories keyed by `Agent.runtime`; unknown
  unsupported names produce a visible error. `Agent.harness` selects Pi or the explicit stub.
- `frontend/src/`: small React components, typed API client, socket/workspace hooks,
  keyboard controls, and shared appearance tokens in `index.css`.
- `frontend/scripts/smoke.mjs`: browser verification and screenshots.
- `docs/PLAN.md` and `docs/DESIGN.md`: scope and design direction.

Run one Uvicorn worker: connections and runtime jobs are process-local. Authentication,
access control, uploads, task execution tools, and persistent agent learning are out of
scope. Tabs resync after reconnecting. Backend restarts lose in-flight jobs; only completed replies are guaranteed to retain
their full body. Persisted reservations become unresolved after restart.

Existing fixed roles migrate to departments: frontend/backend to Engineering, design
to Design, research to Research, ops to Operations, and finance to Finance. Message
and task history is retained while legacy channels merge into department channels.
The fixed role column is removed. Back up important SQLite files before upgrading.


Pi employment and spending (Step 1)

- Agent profiles have an Employment section: harness, provider/model, model-specific thinking,
  maximum output tokens per reply (default 4096), monthly salary, and month-to-date spending including holds. Settings has the org default model,
  shared monthly budget, and provider key status. Department presets are editable starting points.
  Custom IDs can be saved but refuse execution until validated pricing/capabilities are added to
  `backend/app/model_catalog.py`. GPT-6 Luna is the verified OpenAI default; GPT-6.1 Luna is not
  a public API model identifier.
- Native keys: `DEEPSEEK_API_KEY`, `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`; optional OpenRouter uses
  `OPENROUTER_API_KEY`. A default model uses its direct key when present, otherwise the relay when
  `RELAY_KEY` and a relay URL are configured. The UI labels this route **via relay**. No model is
  substituted. DeepSeek's native `deepseek-flash` maps to relay `deepseek-v4.1-flash-1017`;
  Haiku and Luna retain `claude-haiku-5-5` and `gpt-6-luna`.
- Relay primary URL: `RELAY_BASE_URL`, falling back to `RELAY_BASE_URL_V1` when unset/empty.
  Reserve URL: `RELAY_RESERVE_URL`, falling back to `RELAY_RESERVE_URL_V1`. URLs include `/v1`.
  Keys remain only in backend environment files; neither keys nor raw provider errors are exposed.
- Relay accounting uses **list prices**, not gateway credits: input is `model_ratio * 2` USD/1M,
  output multiplies that by `completion_ratio`, cached input by `cache_ratio`. Group discounts,
  credit values, and credit billing multipliers are excluded. This is a consistent allowance unit,
  not a claim about cash charged to a relay account. Known default-model prices are verified in
  the catalog; unknown model prices still refuse execution.
- Public `/api/pricing` may refresh known prices/context lengths with a 3-second HTTP timeout and
  one-hour cache. Failures retain the last known prices or catalog defaults. No discovery or
  pricing request needs the relay key. Generated private `models.json` registers explicit relay
  chat-completion model entries; Pi does not discover models from the gateway.
- DeepSeek input usage is normalized conservatively to the maximum of reported prompt tokens,
  cache misses plus hits, and total tokens minus completion tokens. Replies show **list price**.
- Before any text or reported usage, a connection error, timeout, or HTTP 5xx releases that
  attempt's reservation and retries once against the reserve URL with a new reservation. Once
  text or usage has arrived, no failover occurs. Authentication/client errors do not trigger it.
  A model unavailable on both URLs posts a clear system message naming it; Haiku is not replaced.
- Defaults: employee allowance $10/month, org allowance $100/month, reset on UTC calendar-month
  boundaries. These are spend caps, separate from XP. Reservations are charged to their creation
  month. Monetary values are stored as Decimal-compatible text, not binary floats.
- Before reserving under the single-worker lock, the runtime reads Pi's current session context.
  Input reservations use that context plus the actual new prompt and system text (estimated at
  chars/3, framing allowance, and a 25% margin). Pricing uses the tier for that estimated size;
  long-context rates apply only above the threshold. Output reserves use the employee's enforced
  `max_output_tokens`, default 4096 and bounded by the model's maximum. Cache-write rates are
  included conservatively. A short reply can therefore run on a $1 monthly salary.
- If session context cannot be measured, input falls back to a full-window worst-case reserve.
  When estimated input plus output approaches 90% of the model's context limit, Pi starts a fresh
  session in the same employee/channel directory and posts a short system notice. Recent channel
  context is bounded when reseeding. There is no paid compaction or extra provider call.
- Reservations are estimates, not invoice guarantees: provider billing is the eventual authority.
  Unknown usage remains held for manual reconciliation and is never assumed free. There is no
  automatic release of unresolved charges within the month.
- `GET /api/models`, `/api/agents/{id}/spend`, and `/api/org/spend` expose catalog and accounting.
  `POST /api/agents/{id}/abort` terminates an active Pi process tree. Configuration changes wait
  until the employee's replies finish. Provider credentials are never stored in the database.
- `backend/runtime-node/guard.mjs` is a trusted preload pinned to Pi 1.4.0. Because RPC has no
  tool-list command, it verifies actual session tools and emits a startup assertion. It forces
  the employee's output cap (up to the model's maximum) and blocks a second provider stream per prompt.
  Pi remains pinned to 1.4.0; the lockfile overrides its vulnerable `undici` 8.10.2
  dependency with patched 8.12.2 (same Node requirement, npm audit reports zero issues). Retries, compaction,
  cache warming, tools, skills, MCP, prompt templates, and project context are disabled. Upgrade
  Pi only after rerunning these checks; the preload uses its published session API.
- Each active employee has one lazy process, a bounded serialized queue (8 slots including the
  active run), and a 300-second idle TTL. Sessions persist by employee/channel/config revision in
  `backend/data/runtime`; the private working/config directories do not load host credentials.
  Pi's online catalog refresh is disabled for deterministic routing. `PI_TIMEOUT` defaults to
  180 seconds. Shutdown/abort kills the child tree using a Windows Job Object or a POSIX process
  group; it does not depend on taskkill/WMI permissions. This chat-only setup is not an execution sandbox.
- **Run exactly one Uvicorn worker.** There are no durable jobs, leases, provider gateway, or
  cross-process locks yet. Do not run this unauthenticated local app as a public service.

Offline runtime verification:

```sh
cd backend
uv run python -m scripts.check_pi
```

This starts real Pi 1.4.0, verifies zero tools and the three native model entries with placeholder
keys, and never prompts. Backend tests use a fake JSONL child. The browser smoke server likewise
substitutes the fake child and overrides provider credentials with placeholders; no paid requests
are made. The smoke test also verifies employment editing, model costs, salary display and settings,
with `profile-employment.png` and `settings-models-budget.png` in `frontend/.artifacts/`.


Explicitly authorized live relay checks (small paid requests):

```powershell
cd backend
$env:AGENTSLACK_LIVE = '1'
uv run pytest tests/test_live_relay.py -m live -s
```

Without that variable, the two live cases are skipped; all unit tests block network pricing
requests and clear provider credentials. The live tests boot real Pi, stream one 32-output-token
reply each from DeepSeek and Luna, and assert nonzero usage and settled ledger entries.

For browser evidence, run `node scripts/relay-live.mjs` from `frontend` with the same opt-in flag.
It starts isolated app servers/database, mentions DeepSeek, Luna and Haiku at 32 output tokens,
then saves `relay-deepseek.png`, `relay-luna.png` and `relay-haiku-unavailable.png` in
`frontend/.artifacts/`. It makes real requests, checks the reported Haiku outage without swapping
models, logs only safe counts/costs, and removes temporary sessions/database/browser profiles.
