# agentslack - implementation plan and current model

The local workspace uses specialist agents organized by user-editable departments.
Agents have free-text job titles and optional department assignments. There is no
fixed agent role enum. AI execution remains a local streaming stub.

## Stack

- Python 3.11, FastAPI, SQLModel, SQLite, uv.
- Vite, React 18, TypeScript, Tailwind, Prettier.
- WebSocket events at `/ws`; REST routes under `/api`.
- Terminal-native design follows `DESIGN.md`. Department markers, handles, and tags
  use their department color; the rest of the chrome uses the org accent and status tokens.

## Data model

- **Organization**: name, derived slug, tagline, accent, theme, density, font mode,
  optional CRT effects, initialized flag. Single org for now.
- **UserProfile**: display name and handle; single local user.
- **Department**: id, name, slug, description, hex color, channel_id, sort_order,
  created_at. Names/slugs are unique; each department owns one non-DM channel.
  Colors support neutrals and green/amber/cyan/blue/warm hues; the excluded hue
  band is validated on create and update.
- **Agent**: id, handle, name, nullable department_id, free-text title, avatar color
  metadata, status, level, XP, skills, bio, runtime, created_at. Null department means
  unassigned. Membership follows assignment; moving departments removes the old
  department membership and adds the new one.
- **Channel**: id, name, topic, is_dm, dm_agent_id, created_at.
  **ChannelMember** links agents to shared and department channels.
- **Message**: channel, human/agent/system author, body, optional thread parent,
  created_at, is_streaming. Deltas are transient; final bodies are persisted.
- **Task**: title, description, assignee, optional channel, status, priority,
  XP reward, one-time XP flag, timestamps. Level is `1 + xp // 100`.
- **MemoryEntry**: placeholder facts, lessons, and preferences; no learning harness yet.

## Department catalog and workspace fundamentals

`backend/app/catalog.py` is the catalog source, served at `/api/departments/catalog`.
Core departments (preselected during setup): Leadership, Operations, Finance,
People (HR), Product, Engineering, Marketing, Sales.
Optional departments: Design, Legal, Customer Support, Research, Data & Analytics.
Each has a one-line description and an allowed default color. Users can add custom
names, descriptions, colors, and ordering. Core departments can also be edited or removed.

Every new workspace gets these channels, even with no departments or agents:

| Channel | Purpose |
| --- | --- |
| #general | Company-wide discussion and updates |
| #announcements | Official decisions and milestones |
| #standup | Daily progress, priorities, and blockers |
| #requests | Work intake across departments |
| #random | Informal conversation |

Each selected department adds `#slug`. Reserved org-wide slugs cannot be used for
departments. Department rename updates its channel name; description changes update
its topic. Remove a department to delete its channel and messages, unassign its agents,
and keep tasks with a null channel. #general is always protected. Direct channel deletion
or renaming of a department channel is rejected; use department settings instead.

## Onboarding and sample data

A fresh database is uninitialized. Step 1 collects org/user identity, accent, and sample
team versus empty workspace. Step 2 offers the catalog checkboxes and a custom-department
form. Nothing is seeded before initialization is submitted. Both choices create the five
org-wide channels and the selected department channels.

Sample mode adds one agent per selected core department (eight with default choices):

| Department | Name | Title |
| --- | --- | --- |
| Leadership | Alice | Chief of Staff |
| Operations | Omar | Operations Manager |
| Finance | Nina | Finance Analyst |
| People (HR) | Maya | People Partner |
| Product | Leo | Product Manager |
| Engineering | Evan | Software Engineer |
| Marketing | Zoe | Marketing Lead |
| Sales | Ben | Account Executive |

Skills and stub replies reflect department responsibilities. Eight sample tasks cover
company fundamentals and are spread across department channels and #requests. Deselected
core departments do not receive sample agents/tasks. Optional and custom departments start
without agents until a user hires one. Empty mode creates no agents, messages, or tasks.

## API and events

- `GET /health`; `GET/PATCH /org`; `GET/PATCH /me`; `POST /onboarding`.
- `GET /departments/catalog`; `GET/POST /departments`;
  `PATCH/DELETE /departments/{id}`.
- `GET/POST /agents`; `GET/PATCH/DELETE /agents/{id}`; `GET /agents/{id}/memory`.
- `GET/POST /channels`; `GET/PATCH/DELETE /channels/{id}`; `POST /dms/{agent_id}`.
- `GET /channels/{id}/messages?before=&limit=`; `POST /channels/{id}/messages`.
- `GET/POST /tasks`; `PATCH /tasks/{id}`.

Events: `department.updated/deleted`, `org.updated`, `profile.updated`,
`channel.updated/deleted`, `agent.updated/deleted`, `task.updated/deleted`,
`message.created`, and `message.delta`. Mentions and DMs invoke the runtime registry.
The stub streams department-aware text and restores agent status after completion or error.

## Frontend

- Sidebar separates shared CHANNELS, colored DEPARTMENTS, and DIRECT messages.
- Agent directory groups entries by department with an explicit Unassigned group.
- Hire and edit forms use a department dropdown plus a free-text title.
- Settings include department add, rename, description, color, reorder, and confirmed removal.
  The appearance preview is a sample announcement row using the current accent/font/density.
- IRC-style messages, streamed caret, status line, profile/channel panes, task board,
  command palette, slash commands, activity log, level-up feedback, and keyboard shortcuts
  remain available. Sidebar shortcut hints use bracketed notation.

## Existing database upgrade

The startup upgrade preserves existing agents, XP, task IDs, and conversation history.
Legacy role mapping: frontend/backend -> Engineering, finance -> Finance,
design -> Design, research -> Research, ops -> Operations. The old role column is
removed and department_id is added. Legacy frontend/backend/ops channel histories,
tasks, and members move to the matching department channel; already matching channels
are reused. Missing org-wide channels are added to initialized workspaces. Upgrades are
idempotent and tested on a file-backed SQLite database with foreign keys enabled.

## Acceptance

Backend: `uv run pytest`, `uv run ruff check`, `uv run ruff format --check`.
Frontend: `npm run lint`, `npm run format:check`, `npm run build`, `npm run smoke`.
Tests cover CRUD, catalog, selected/custom/empty onboarding, assignment/unassignment,
department-aware replies, color and reserved-slug validation, deletion references,
role migration, streaming, XP, settings, and socket events.

The browser smoke script uses isolated servers/data and refreshes screenshots including
both onboarding steps, the workspace, grouped agents, and department settings.

Out of scope: auth, multi-user access control, real LLM execution, uploads, persistent
learning, and multi-process runtime coordination. Do not commit without explicit instruction.
