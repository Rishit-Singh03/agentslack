# agentslack — Phase 1 plan: scaffolding + UI

Goal: a Slack/Teams-style workspace where the "members" are AI agents (specialists:
frontend, backend, finance, ...) that you assign work to. Agents will later level up and
keep long-term memory. **Phase 1 is only scaffolding and the UI.** No real agent runtime
yet: agents reply through a stub so the UI can be exercised end to end.

## Stack

| Part | Choice |
|---|---|
| Backend | Python 3.11, FastAPI, SQLModel on SQLite, managed with `uv` |
| Realtime | FastAPI WebSocket at `/ws` broadcasting new messages/task updates |
| Frontend | Vite + React 18 + TypeScript + Tailwind CSS, `fetch` + a small typed API client |
| Layout | Monorepo: `backend/`, `frontend/`, `docs/` |

## Backend (`backend/`)

```
backend/
  pyproject.toml            # uv project; deps: fastapi, uvicorn[standard], sqlmodel, pydantic-settings
  app/
    main.py                 # FastAPI app, CORS for http://localhost:5173, routers, startup seeds DB
    config.py               # pydantic-settings: DATABASE_URL (default sqlite:///./agentslack.db), RELAY_KEY (optional)
    db.py                   # engine, session dependency, create_all
    models.py               # SQLModel tables (below)
    schemas.py              # request/response models where they differ from tables
    seed.py                 # idempotent seed: org, channels, agents, a few messages, tasks
    realtime.py             # WebSocket connection manager (broadcast JSON events)
    routers/  agents.py channels.py messages.py tasks.py
    runtime/
      base.py               # AgentRuntime protocol: async def respond(agent, message, context) -> str
      stub.py               # StubRuntime: canned in-character reply after a short delay
  tests/test_api.py         # pytest + httpx TestClient smoke tests
```

### Data model
- **Agent**: id, handle (`@fiona`), name, role (`frontend|backend|finance|design|research|ops`),
  title, avatar_color, status (`online|busy|idle|offline`), level (int), xp (int),
  skills (JSON list of str), bio, runtime (str, default `"stub"`), created_at.
- **Channel**: id, name (`general`, `frontend`, `backend`, `finance`), topic, is_dm (bool),
  dm_agent_id (nullable), created_at. Membership: `ChannelMember(channel_id, agent_id)`.
- **Message**: id, channel_id, author_type (`human|agent|system`), author_id (nullable for
  human), body (markdown text), thread_parent_id (nullable), created_at.
- **Task**: id, title, description, assignee_agent_id, channel_id (nullable), status
  (`todo|in_progress|review|done`), priority (`low|med|high`), xp_reward (int), created_at, updated_at.
- **MemoryEntry** (placeholder for later): id, agent_id, kind (`fact|lesson|preference`), content, created_at.

### API (all under `/api`)
- `GET /health`
- `GET/POST /agents`, `GET/PATCH /agents/{id}`, `GET /agents/{id}/memory`
- `GET/POST /channels`, `GET /channels/{id}`, `POST /dms/{agent_id}` (get-or-create DM channel)
- `GET /channels/{id}/messages?before=&limit=`, `POST /channels/{id}/messages`
  - After a human posts, for each agent @mentioned (or the DM agent), schedule a background
    task: StubRuntime reply -> save Message -> broadcast. Set agent status busy while it is "thinking".
- `GET/POST /tasks`, `PATCH /tasks/{id}` (moving to `done` awards `xp_reward` to the assignee;
  level = 1 + xp // 100) and posts a system message in the task's channel.
- `WS /ws`: events `{type: "message.created"|"task.updated"|"agent.updated", data: {...}}`.

## Frontend (`frontend/`)

Slack-like three-column layout, dark theme by default (light theme toggle), responsive.

- **Left sidebar**: workspace name + switcher placeholder; sections "Channels" (with `#`),
  "Direct messages" (agent avatars with status dot), "Tasks" link, "Agents" directory link,
  "+ Hire agent" button (opens modal -> POST /agents).
- **Center**: channel header (name, topic, member avatars); message list grouped by author
  and day, markdown rendering, agent role badges, "typing..." indicator when an agent is busy;
  composer with `@mention` autocomplete for agents, Enter to send, Shift+Enter newline.
- **Right panel** (collapsible): clicking an agent opens a profile: avatar, title, role,
  level + XP progress bar, skills chips, current tasks, memory (empty-state placeholder).
- **Tasks view**: kanban board (todo / in progress / review / done), create task modal with
  assignee picker; drag or a status dropdown to move cards.
- **Agents view**: directory grid of agent cards.
- Live updates via the `/ws` socket; Vite dev server proxies `/api` and `/ws` to `localhost:8000`.

```
frontend/src/
  api/client.ts  api/types.ts  hooks/useSocket.ts
  components/  Sidebar, ChannelView, MessageList, Message, Composer, AgentProfile,
               AgentAvatar, TaskBoard, TaskCard, HireAgentModal, CreateTaskModal
  pages/ (or a simple view state)  App.tsx  main.tsx  index.css
```

## Seed data
Org "Acme Agents". Agents: Fiona (frontend), Bruno (backend), Penny (finance),
Dex (design), Remy (research), Opal (ops), with varied levels/xp/statuses.
Channels: #general, #frontend, #backend, #finance. A handful of messages and 5–6 tasks.

## Dev workflow
- `cd backend && uv run uvicorn app.main:app --reload` (port 8000)
- `cd frontend && npm install && npm run dev` (port 5173)
- Root README documents both, plus `.env.example` with `RELAY_KEY=` and `DATABASE_URL=`.

## Out of scope for phase 1
Real LLM harnesses (pi / DeepSeek / others plug in via `runtime/base.py` later), auth,
multi-user, persistent agent memory logic, file uploads.

## Acceptance
- `uv run pytest` passes; `npm run build` and `npm run lint`/`tsc` pass.
- Both servers start; UI loads seeded workspace; posting `@bruno hi` in #backend shows a
  typing indicator then a stub reply live; creating and completing a task updates XP/level.
