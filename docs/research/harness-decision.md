# Harness decision (Step 1)

Date: 2026-10-25. Inputs: Claude's research and Codex's independent research
([harness-codex.md](harness-codex.md)), then one round of deliberation.

## Decision

**Default harness: pi** (`@earendil-works/pi-coding-agent`, pinned **1.4.0**, MIT), driven from the
Python backend over `pi --mode rpc` (LF-delimited JSONL on stdin/stdout). The old
`@mariozechner/pi-coding-agent` package is deprecated; do not use it.

Why pi:
- It reaches all three default models through **built-in** providers (no custom adapters), with
  prices in its bundled catalog, so cost accounting works out of the box.
- Assistant `message_end.message.usage` reports `input, output, cacheRead, cacheWrite, totalTokens`
  and `cost {input, output, cacheRead, cacheWrite, total}`; this feeds the salary ledger.
- Headless RPC with prompt/abort/steer/new_session/switch_session/set_model; JSONL session files
  (useful for memory in Step 2); per-process `--api-key`, `--system-prompt`, tool allowlists.
- Documented native Windows support; MIT; actively maintained.

Alternatives considered: Pydantic AI (best Python-native fallback, more loop to own), official
DeepSeek Harness (promising, still preview), OpenCode server (good HTTP/SSE harness, larger
surface), Claude Agent SDK / Codex CLI (single-vendor), LiteLLM (gateway, not a harness). The
runtime registry keeps these pluggable later.

## Default models

| Choice | Provider (pi) | Model ID | $/1M in / cached / out |
|---|---|---|---|
| DeepSeek V4.1 Flash (1017) | `deepseek` | `deepseek-flash` (alias currently serving V4.1-Flash-1017) | 0.30 / 0.006 / 1.20 peak; half off-peak |
| Claude Haiku 5.5 | `anthropic` | `claude-haiku-5-5` | 0.10 / 0.01 / 0.50 (≤100K prompt) |
| GPT-6 Luna | `openai` | `gpt-6-luna` (Responses API) | 0.10 / 0.01 / 0.50 (≤272K prompt) |

"GPT-6.1 Luna" has no public API model; only GPT-6.1 **Sol** exists. We ship **GPT-6 Luna**,
labelled as such (confirmed by the project owner, 2026-10-26). The catalog is data, so swapping
it later is a one-line change.

A fourth provider, **relay**, is an OpenAI-compatible endpoint configured by `RELAY_KEY` and
`RELAY_BASE_URL` (or `RELAY_BASE_URL_V1`). An optional reserve uses `RELAY_RESERVE_URL` (or
`RELAY_RESERVE_URL_V1`). Default models prefer their direct key, then use the same model through
relay chat completions. Explicit `models.json` entries avoid discovery. Step 1b budgets use verified
list pricing, ignoring gateway discounts and unknown credit conversions. A pre-text/pre-usage
connection error, timeout or HTTP 5xx may release the hold and retry once on the reserve endpoint;
there is no model substitution or failover after text/usage.

Department presets (editable starting points, not benchmark results): Haiku 5.5 for Leadership,
People, Marketing, Sales, Legal, Support; DeepSeek Flash for Engineering, Data & Analytics,
Research; GPT-6 Luna for Product, Operations, Finance, Design; custom departments use the org default.

## Step 1 architecture (agreed scope)

- **Process model:** in-process asyncio supervisor inside FastAPI (single Uvicorn worker, which is
  documented). One lazily started pi process per active agent, idle TTL, per-agent serialized
  queue (bounded). Session files per agent+channel under a server-owned data dir
  (`PI_CODING_AGENT_SESSION_DIR` / `--session-dir`). Kill whole process trees on shutdown/abort.
  In-flight jobs are lost on restart (documented); a separate worker with leases comes later.
- **Chat-only agents:** `--no-tools --no-extensions --no-skills --no-mcp --no-context-files
  --no-prompt-templates`, private `PI_CODING_AGENT_DIR` (generated `models.json`, no host config),
  private cwd, env allowlist containing only the key that agent's provider needs. Verify at
  startup that zero tools are exposed. Tools and sandboxing are designed in Step 3.
- **Credentials:** provider keys only from backend env/.env (`DEEPSEEK_API_KEY`,
  `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `OPENROUTER_API_KEY`, `RELAY_KEY` + `RELAY_BASE_URL`).
  Never stored in the DB or sent over the socket; the API exposes only "configured: true/false".
- **Salary (budget):** per-agent monthly USD cap plus an org monthly cap, Decimal money.
  Persisted ledger with states `reserved → settled | unresolved | released`. Before each run,
  reserve measured session context plus estimated new prompt/system text (chars/3 with a 25%
  margin), plus the employee output cap (default 4096), at the applicable size tier under a lock;
  unknown context uses a full-window input reserve. Refuse when either cap would be exceeded.
  The guard enforces the output cap; near the context limit, start a fresh session with a notice
  instead of paid compaction. Settle from
  assistant `message_end` usage; if usage is missing after failure/abort, keep the reservation
  `unresolved` (counts against budget) instead of settling to zero. Session-stats fallback uses
  the delta from a pre-run baseline. Unknown price means refuse.
- **Streaming:** `text_delta` → existing `message.delta`; thinking and tool deltas are never
  shown as prose; final text reconciled from assistant `message_end`; agent goes idle on
  `agent_settled`, and abort/error/process exit are handled as terminal states too.
- **Fallback:** if node/pi/the provider key is missing, or the budget is exhausted, the agent
  posts a clearly marked system message explaining why. It never silently switches to the stub
  or to a different model. The stub stays selectable as harness `stub` (offline/demo).
