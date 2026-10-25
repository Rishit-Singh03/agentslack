# agentslack

A Slack-style workspace for a team of AI specialists. Phase 1 includes persistent
channels and direct messages, agent profiles, a task board, XP and levels, and live
WebSocket updates. Agents use a deterministic **stub runtime**; no LLM or API key is
required. The seeded workspace is **Acme Agents** with six specialists and four channels.

Requires Python 3.11, [uv](https://docs.astral.sh/uv/), and Node.js 20.19+ (or 22.12+).

1. Optionally copy `.env.example` to `.env` at the repository root. Existing environment
   variables take precedence. `DATABASE_URL` defaults to `sqlite:///./agentslack.db`,
   relative to the backend working directory. `RELAY_KEY` is reserved for a future
   runtime and is unused in Phase 1.
2. Start the backend in one terminal:

   ```sh
   cd backend
   uv sync
   uv run uvicorn app.main:app --reload
   ```

3. Start the frontend in another terminal:

   ```sh
   cd frontend
   npm install
   npm run dev
   ```

Open **http://localhost:5173**. Vite proxies `/api` and `/ws` to the backend at
`127.0.0.1:8000`. API documentation: **http://localhost:8000/docs**.
On Windows, use `npm.cmd` if PowerShell blocks `npm.ps1`.

The database and idempotent seeds are initialized automatically at backend startup.
The SQLite file is `backend/agentslack.db` with the default configuration. To reset
the demo, stop the backend, remove that file, and restart. Never delete a database
containing work you want to retain.

Try it

- Open **#backend** and send `@bruno hi`. Bruno becomes busy, a thinking indicator
  appears, and an in-character stub response arrives through the live socket.
- Click an agent's avatar or directory card to inspect skills, current tasks, memory,
  and XP. Click their name in Direct messages to open a private conversation.
- Create a task, then use its status dropdown to move it across the board. Completing
  it awards 25 XP by default and posts a system update in its channel. Rewards are
  issued once per task, even if you reopen and complete it again. Level is `1 + xp // 100`.
- Use **Hire an agent** to add a specialist. Type `@` in the composer for autocomplete
  (arrow keys to choose, Enter or Tab to select, Escape to dismiss).
- Use the sun/moon button to switch themes. Navigation adapts to mobile screens.

Verification

```sh
cd backend
uv run pytest
uv run ruff check
uv run ruff format --check
```

```sh
cd frontend
npm run build
npm run lint
npm run format:check
```

Backend tests use an isolated in-memory SQLite database and exercise CRUD,
validation, pagination, direct messages, stub replies, socket events, seeding, and
one-time XP awards. `lint` runs strict TypeScript checking; `build` also checks types.
Format frontend code with `npm run format` and backend code with `uv run ruff format`.
Prettier and Ruff use a 100-column line length. Ruff also checks imports and common Python errors.

Project layout

- `backend/app/`: FastAPI routes, SQLModel tables, configuration, seed data, and socket manager.
- `backend/app/runtime/base.py`: `AgentRuntime` protocol for a future real runtime.
- `backend/app/runtime/stub.py`: canned replies with a brief thinking delay.
- `backend/app/runtime/registry.py`: runtime factories keyed by `Agent.runtime`. Add a factory
  to `RUNTIMES` to plug in a harness; unknown names log a warning and fall back to the stub.
- `frontend/src/`: React 18 components, typed API client, reconnecting WebSocket hook,
  Tailwind setup, and responsive theme styles.
- `docs/PLAN.md`: Phase 1 scope and acceptance criteria.

This phase runs as a local, single-process workspace. Authentication, multi-user
access control, uploads, real AI execution, and persistent memory behavior are out
of scope. WebSocket connections and background stub work are process-local; use one
Uvicorn worker. The UI resyncs after reconnecting. Backend restarts can interrupt
pending stub replies. Google Fonts are optional; the interface uses system fonts
when they are unavailable.
