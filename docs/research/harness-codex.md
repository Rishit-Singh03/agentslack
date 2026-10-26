# Agent harness research: independent Codex assessment

Research snapshot: **2026-10-25**. Research only; no application changes, package installs, paid
model calls, or commits. Versions below are public registry versions, not versions installed or
integration-tested in this repository. Prices are USD, before tax, negotiated discounts, and
additional tool/compute charges. Recommendations are architectural judgments, not vendor guarantees.

## Decision

Use **Pi as the provisional default harness**, driven by a Python worker over its headless JSONL
RPC interface. Pin the maintained **`@earendil-works/pi-coding-agent@1.4.0`**, not the package named
in the original proposal. The old `@mariozechner/pi-coding-agent@0.73.1` is explicitly deprecated
in npm in favor of the new namespace; the old pi-mono repository redirects to
`earendil-works/pi`. This is a material dependency change, not just a version bump.
Sources: [old package metadata](https://registry.npmjs.org/@mariozechner%2fpi-coding-agent),
[maintained package metadata](https://registry.npmjs.org/@earendil-works/pi-coding-agent/1.4.0),
[repository](https://github.com/earendil-works/pi).

Two qualifications:

1. **“GPT-6.1 Luna” has no verified public API identifier or price.** Exact-name searches of
   official OpenAI documentation did not establish it, and its expected model URL returned 404.
   The public catalog lists **GPT-6 Luna (`gpt-6-luna`)** and **GPT-6.1 Sol (`gpt-6.1-sol`)**.
   Keep the requested choice unresolved until product clarification; do not silently substitute
   Luna or Sol. The pricing and compatibility findings below label the verified Luna separately.
   Sources: [model catalog](https://developers.openai.com/api/docs/models),
   [verified Luna](https://developers.openai.com/api/docs/models/gpt-6-luna).
2. Pi is a coding harness, while many employees will perform business work. Restrict their tools
   accordingly. **Pydantic AI is the strongest Python-native alternative** if application tools,
   structured results, and budget policy matter more than an existing coding environment. Benchmark
   it and the new official DeepSeek harness before making Pi an irreversible product assumption.

## 1. Pi: integration and operational fit

### Maintained package and embedding

The maintained coding-agent package is **1.4.0**, published **2026-10-21**, MIT licensed, requiring
**Node >=22.19.0**. Its SDK is TypeScript/JavaScript, with `createAgentSession`, model/auth registries,
tools, and session management. I did not find a first-party Python SDK. Python should supervise a
process rather than attempt to embed the JS SDK. A small Node bridge using the SDK remains an
option if RPC lacks a required policy hook.
Sources: [versioned npm metadata](https://registry.npmjs.org/@earendil-works/pi-coding-agent/1.4.0),
[SDK documentation](https://raw.githubusercontent.com/earendil-works/pi/main/packages/coding-agent/docs/sdk.md),
[MIT license](https://raw.githubusercontent.com/earendil-works/pi/main/LICENSE).

Use **`pi --mode rpc`** with stdin/stdout pipes for a persistent conversation. Requests are JSON
objects separated by LF; correlate commands using their IDs. Drain stderr independently and keep
it out of the protocol. A `prompt` acknowledgment means accepted/queued, not that the reply is
finished. Current docs distinguish `agent_end` from **`agent_settled`**, which accounts for automatic
continuations; also handle prompts with `disposition: "handled"` that start no run. Parse LF bytes,
not general Unicode line boundaries: text can contain U+2028/U+2029.
Source: [RPC protocol](https://raw.githubusercontent.com/earendil-works/pi/main/packages/coding-agent/docs/rpc.md).

Useful operations include model discovery/selection, abort, session creation/switching/forking,
and `get_session_stats`. In contrast, **`pi --mode json "prompt"`** is useful for one-shot jobs:
it emits a session header and event stream, then exits. It is less convenient for an interactive
employee that should retain a warm session.
Sources: [RPC commands](https://raw.githubusercontent.com/earendil-works/pi/main/packages/coding-agent/docs/rpc-commands.md),
[JSON mode](https://raw.githubusercontent.com/earendil-works/pi/main/packages/coding-agent/docs/json.md).

### Providers and exact model selection

The **published `@earendil-works/pi-ai@1.4.0` tarball**, not just repository HEAD, contains these
native chat entries:

| Pi provider | Model ID | Pi API adapter | Assessment |
| --- | --- | --- | --- |
| `deepseek` | `deepseek-flash` | `openai-completions` | Current native Flash alias; presently V4.1 Flash 1017. |
| `anthropic` | `claude-haiku-5-5` | `anthropic-messages` | Requested Haiku version is present. |
| `openai` | `gpt-6-luna` | `openai-responses` | Verified GPT-6 Luna; not the unresolved GPT-6.1 Luna request. |

These were read from `dist/providers/data/{deepseek,anthropic,openai}.json` in the published
tarball linked by [Pi AI 1.4.0 metadata](https://registry.npmjs.org/@earendil-works/pi-ai/1.4.0).
There is also a Luna classifier entry: explicitly select the **chat/Responses** entry. Native
provider keys are `DEEPSEEK_API_KEY`, `ANTHROPIC_API_KEY`, and `OPENAI_API_KEY`.
Source: [provider authentication](https://raw.githubusercontent.com/earendil-works/pi/main/packages/coding-agent/docs/providers.md).

OpenRouter is also supported, using provider `openrouter` and the router IDs in section 3.
Custom compatible endpoints/models can be configured through `models.json`; extensions can
register providers. Pi can overlay its bundled catalog with online model metadata, so a package
pin alone does not freeze routing, context limits, or prices. Record a validated catalog snapshot.
Published Luna chat metadata currently allows 272K context even though OpenAI documents longer
contexts with a pricing tier: do not silently expand it without testing.
Sources: [custom models/catalog refresh](https://raw.githubusercontent.com/earendil-works/pi/main/packages/coding-agent/docs/models.md),
[live Pi catalog](https://pi.dev/models), [published Pi AI package](https://registry.npmjs.org/@earendil-works/pi-ai/1.4.0).

DeepSeek publishes a Pi integration guide, including reasoning-content compatibility options.
However, it still names the deprecated package, legacy model aliases, and old prices. Use it for
compatibility hints, not dependency selection or current cost estimates.
Sources: [DeepSeek Pi guide](https://api-docs.deepseek.com/quick_start/agent_integrations/pi_mono/),
[current DeepSeek pricing](https://api-docs.deepseek.com/quick_start/pricing/).

### Streaming, tools, sessions, accounting

Pi emits `message_update` with `assistantMessageEvent`, including `text_delta`, `thinking_delta`,
and `toolcall_delta`. Only visible text belongs in our chat deltas. Treat completed `message_end`
content as authoritative, rather than assuming concatenated partial events always reconstruct
the final message. Tool execution has distinct start/update/end events; an agent run can contain
several assistant messages and tool rounds. Usage may only become meaningful at completion;
do not add together cumulative usage snapshots.
Source: [JSON/event examples](https://raw.githubusercontent.com/earendil-works/pi/main/packages/coding-agent/docs/json.md).

Pi supplies filesystem/shell coding tools and permits custom tool sets. Extensions can register
tools, providers, and hooks. Current SDK docs also describe MCP extension wiring, so old claims
that Pi categorically cannot use MCP are no longer a safe basis for comparison. Extensions execute
with the process's privileges; tool configuration is not an OS security boundary.
Sources: [SDK/tool composition](https://raw.githubusercontent.com/earendil-works/pi/main/packages/coding-agent/docs/sdk.md),
[extensions](https://raw.githubusercontent.com/earendil-works/pi/main/packages/coding-agent/docs/extensions.md).

Sessions persist as JSONL trees with parent relationships, message entries, compactions, and
extension state. This provides conversation recovery and branching; it does not supply a curated
long-term employee memory system. Session stats and provider usage/cost metadata are useful
inputs to our ledger, but are not a verified organization-wide spending governor.
Sources: [session format](https://raw.githubusercontent.com/earendil-works/pi/main/packages/coding-agent/docs/session-format.md),
[stats command](https://raw.githubusercontent.com/earendil-works/pi/main/packages/coding-agent/docs/rpc-commands.md).

### Windows

Pi documents native Windows and WSL operation. The built-in bash tool uses Git Bash on native
Windows; a PowerShell tool is an alternative. Node must meet the maintained package's requirement.
For our supervisor, launch a resolved executable/Node entry point with an argument array and
hidden window, not an interpolated shell command. Validate cancellation of descendant processes
on Windows, not just termination of the immediate Node child.
Sources: [Windows guide](https://raw.githubusercontent.com/earendil-works/pi/main/packages/coding-agent/docs/windows.md),
[package engines](https://registry.npmjs.org/@earendil-works/pi-coding-agent/1.4.0).

## 2. Alternatives

### Version and license snapshot

Versions were read directly from npm/PyPI metadata on the research date. Different language
packages need not share a release number. “MIT” here describes the cited package/repository;
provider service terms and bundled proprietary components are separate.

| Option | Current package/version | License and runtime notes |
| --- | --- | --- |
| OpenAI Agents SDK | Python `openai-agents` **0.24.0**; JS `@openai/agents` **0.21.0** | MIT; Python >=3.10. |
| Claude Agent SDK | Python `claude-agent-sdk` **0.2.174**; JS `@anthropic-ai/claude-agent-sdk` **0.3.310** | Python wrapper metadata MIT; JS points to README license. Bundled Claude runtime/SDK usage has separate terms. Python >=3.10. |
| LiteLLM | `litellm` **1.106.4** | MIT core; Python >=3.10,<3.15; check separate enterprise features. |
| Pydantic AI | `pydantic-ai` **2.61.0** | MIT; Python >=3.11. |
| OpenCode | `opencode-ai`, `@opencode-ai/sdk` **1.19.4** | MIT. Compare the shipped 1.x interface, not unrelated/newer 2.x examples. |
| Codex CLI | `@openai/codex` **0.164.0** | Apache-2.0; npm launcher installs platform-specific executable. |
| Official DeepSeek Harness | npm `@deepseek-ai/dsh` **0.2.1-rc.2**; Python `deepseek-harness-sdk` **0.2.1rc2** | MIT repository/runtime; Python >=3.10, bundled platform runtime. Preview. |

Registry sources: [OpenAI Python](https://pypi.org/pypi/openai-agents/json),
[OpenAI JS](https://registry.npmjs.org/@openai%2fagents),
[Claude Python](https://pypi.org/pypi/claude-agent-sdk/json),
[Claude JS](https://registry.npmjs.org/@anthropic-ai%2fclaude-agent-sdk),
[LiteLLM](https://pypi.org/pypi/litellm/json),
[Pydantic AI](https://pypi.org/pypi/pydantic-ai/json),
[OpenCode](https://registry.npmjs.org/opencode-ai),
[OpenCode SDK](https://registry.npmjs.org/@opencode-ai%2fsdk),
[Codex](https://registry.npmjs.org/@openai%2fcodex),
[DeepSeek CLI](https://registry.npmjs.org/@deepseek-ai%2fdsh),
[DeepSeek Python SDK](https://pypi.org/pypi/deepseek-harness-sdk/json).

### OpenAI Agents SDK

**Integration/providers:** native Python async agent loop; OpenAI Responses is a natural fit for
verified Luna. Non-OpenAI providers are supported through adapters, including LiteLLM or compatible
clients. DeepSeek and Haiku would still need provider-specific capability tests; a shared API shape
does not guarantee reasoning/tool compatibility. This is a framework for composing our agent,
not automatically the Codex coding harness.
Source: [model adapters](https://openai.github.io/openai-agents-python/models/).

**Events/tools/persistence:** streaming exposes raw model events and higher-level run items;
functions, handoffs, and approval flows integrate with the loop. Sessions include SQLite,
SQLAlchemy, and other backends, making application ownership straightforward. Usage is available,
but salary periods and a durable shared USD ledger remain our responsibility. The Python core is
portable to Windows; chosen shell/sandbox tools add their own platform constraints.
Sources: [streaming](https://openai.github.io/openai-agents-python/streaming/),
[sessions](https://openai.github.io/openai-agents-python/sessions/),
[usage](https://openai.github.io/openai-agents-python/usage/).

**Verdict:** credible Python-first alternative, especially for OpenAI-centric application tools.
Do not choose it merely because the product uses the word “agents.”

### Claude Agent SDK

**Integration/providers:** Python `query()` streams a job; `ClaudeSDKClient` supports a stateful
conversation. The Python package bundles the Claude Code CLI, so a separate global CLI installation
is unnecessary. Native Claude Haiku is the clear fit. Arbitrary OpenAI/DeepSeek execution is not a
first-class three-provider guarantee; DeepSeek's Anthropic-compatible endpoint is an integration
possibility, not proof that every SDK feature works. Windows operation and chosen shell tools must
be checked against Claude Code prerequisites.
Sources: [Python SDK README](https://raw.githubusercontent.com/anthropics/claude-agent-sdk-python/main/README.md),
[Python API](https://code.claude.com/docs/en/agent-sdk/python).

**Events/tools/persistence/budgets:** partial-message streaming, resumable session IDs, built-in
coding tools, MCP, and permission hooks are provided. `max_budget_usd` is useful but can overshoot;
it does not include restored-session spending and `/clear` resets its counter. Track each employee's
actual period spend externally. The SDK reports usage and total cost. Also, `allowed_tools` means
auto-approval, not removal of all unlisted tools; use explicit restrictions and permission handling.
Sources: [cost tracking](https://code.claude.com/docs/en/agent-sdk/cost-tracking),
[tool permission semantics](https://raw.githubusercontent.com/anthropics/claude-agent-sdk-python/main/README.md).

**License/risk:** wrapper metadata does not make the bundled harness uniformly MIT. SDK usage is
governed by Anthropic Commercial Terms, with exceptions for individually licensed components.
**Verdict:** offer as a Claude-specific premium harness, not the universal default.
Source: [SDK overview and terms](https://code.claude.com/docs/en/agent-sdk/overview).

### LiteLLM plus our own loop

**Integration/providers:** Python transport and optional proxy cover many providers, including the
three relevant API families. We would own the planning loop, tool dispatch, cancellation,
compaction, transcript persistence, and UI event normalization. Streaming and response usage help,
but model-price metadata must be verified/overridden for new models and conditional prices.
Source: [usage/cost helpers](https://docs.litellm.ai/docs/completion/token_usage).

**Budgets/Windows/license:** proxy virtual keys can scope models and spending by employee. However,
documented budget enforcement requires PostgreSQL: DB-less budget configuration fails open.
Adding this proxy therefore adds infrastructure beyond our current SQLite application. Python is
portable; our tools determine OS support and isolation. MIT core licensing does not imply every
enterprise proxy feature is included.
Sources: [proxy users/budgets](https://docs.litellm.ai/docs/proxy/users),
[virtual keys](https://docs.litellm.ai/docs/proxy/virtual_keys),
[package](https://pypi.org/pypi/litellm/json).

**Verdict:** useful gateway/accounting component; expensive as a reason to build a complete harness
from scratch. Do not confuse a provider abstraction with an employee runtime.

### Pydantic AI

**Integration/providers:** native Python, typed tools and results, streaming, and provider adapters
make it a particularly good fit for non-coding departments. Select native OpenAI/Anthropic or
compatible DeepSeek/OpenRouter configurations, with the exact IDs in section 3. Tool execution and
filesystem access are ours to supply. Python core can run on Windows; shell/container choices need
separate validation.
Source: [provider/model documentation](https://pydantic.dev/docs/ai/models/overview/).

**Budgets/persistence:** current docs expose `UsageLimits`, including a Decimal USD `cost_limit`,
request/token/tool-call limits, and accumulated usage. These are valuable local guards, not a shared
multi-worker salary ledger, and an in-flight request can cross a limit. Preserve usage along with
conversation history. Message history and optional durable-execution integrations provide building
blocks rather than a turnkey coding-agent session directory.
Sources: [agents/usage limits](https://pydantic.dev/docs/ai/core-concepts/agent/),
[message history](https://pydantic.dev/docs/ai/core-concepts/message-history/),
[durable execution](https://pydantic.dev/docs/ai/capabilities/durable_execution/overview/).

**Verdict:** preferred fallback if Pi's coding tools and Node process are more machinery than the
business workflows need. MIT and strong Python fit; more application loop/tool design than Pi.

### OpenCode server

**Integration/providers/Windows:** `opencode serve` exposes an HTTP/OpenAPI server with SSE, so
Python can use an HTTP client without embedding JS. Its provider system uses AI SDK/Models.dev and
supports custom compatible endpoints. Native Windows/WSL guidance exists. Validate current catalog
entries rather than assuming a provider's presence proves every new model is compatible.
Sources: [server API](https://docs.opencode.ai/docs/server/),
[providers](https://dev.opencode.ai/docs/providers),
[Windows](https://dev.opencode.ai/docs/windows-wsl).

**Events/tools/persistence/cost:** server sessions support messages, asynchronous prompting,
abort, and event subscriptions; the JS SDK supplies typed clients. Persistent sessions and coding
tools are already part of the product. Use reported token/cost information as ledger inputs;
I did not verify an organization-wide hard salary cap. Bind privately and enable authentication
(`OPENCODE_SERVER_PASSWORD`); a shared server and different working directories do not establish
tenant isolation.
Sources: [server endpoints/authentication](https://docs.opencode.ai/docs/server/),
[SDK](https://docs.opencode.ai/docs/sdk/),
[permissions](https://docs.opencode.ai/docs/permissions/).

**Verdict:** strongest alternative full coding harness when HTTP/SSE is preferred to JSONL pipes.
MIT, but a larger service surface to supervise and secure. Prefer separate isolated workers over
one powerful daemon shared by every employee.

### Codex CLI: exec and app-server

**Integration:** `codex exec --json` is the batch interface; app-server is the richer persistent
JSON-RPC integration. Its lifecycle includes initialization, threads, turns, cancellation, streamed
agent-message deltas, tool/approval events, and token-usage updates. Use supported protocols rather
than scrape the interactive terminal. Threads can resume; `exec` also supports resumption.
Sources: [non-interactive mode](https://learn.chatgpt.com/docs/non-interactive-mode),
[app-server protocol](https://learn.chatgpt.com/docs/app-server).

**Models/Windows/budgets:** OpenAI models are the primary fit; custom compatible providers need
separate validation, and Anthropic's native Messages API is not a drop-in Responses endpoint.
Native Windows sandbox documentation now exists; do not assume old “WSL only” advice remains true.
Usage events are not an employee's financial ledger. Prefer metered API credentials when billing
employees by spend rather than equating a subscription login with zero per-agent cost.
Sources: [provider configuration](https://learn.chatgpt.com/docs/config-file/config-reference),
[Windows sandbox](https://learn.chatgpt.com/docs/windows/windows-sandbox),
[package/license](https://registry.npmjs.org/@openai%2fcodex).

**Verdict:** useful optional OpenAI coding harness, Apache-2.0, but not the clearest universal
native-API solution for the requested three providers.

### Official DeepSeek Harness: a real additional contender

DeepSeek now publishes **`deepseek-ai/deepseek-harness`**, CLI `dsh`, and an official Python package
**`deepseek-harness-sdk`**. Its SDK starts a bundled runtime lazily and reuses it until closed;
normal SDK execution does not require system Node. Runtime **0.2.1rc2** wheels include Windows x64,
Linux x64/ARM64, and macOS variants. The Python import is `deepseek_harness`, despite the distribution
being named `deepseek-harness-sdk`.
Sources: [Python integration guide](https://raw.githubusercontent.com/deepseek-ai/deepseek-harness/master/docs/user/guide/python-sdk.md),
[SDK metadata](https://pypi.org/pypi/deepseek-harness-sdk/json),
[bundled runtime wheels](https://pypi.org/pypi/deepseek-harness-runtime-bin/json).

**Important package-name collision:** PyPI **`deepseek-harness==0.3.1`** links to an unrelated
third-party repository, not DeepSeek's official harness. Do not install it based on the name.
Also, repository HEAD currently names a newer RC than the npm release; do not mix source-build
requirements or HEAD-only features with a pinned released SDK.
Sources: [unrelated package metadata](https://pypi.org/pypi/deepseek-harness/json),
[official CLI release metadata](https://registry.npmjs.org/@deepseek-ai%2fdsh),
[source package manifest](https://raw.githubusercontent.com/deepseek-ai/deepseek-harness/master/apps/cli/package.json).

It offers SDK JSON-RPC, ACP, headless, and web profiles. Persistent sessions/logs and streaming
provider events exist; provider configuration includes DeepSeek and compatible OpenAI/Anthropic
paths. A Pi AI adapter makes this more than a DeepSeek-only thin API wrapper. Usage metering exists,
but I did not verify a hard shared spend cap. The repository is MIT and explicitly labels security
as unaudited developer preview.
Sources: [CLI profiles](https://raw.githubusercontent.com/deepseek-ai/deepseek-harness/master/apps/cli/README.md),
[providers](https://raw.githubusercontent.com/deepseek-ai/deepseek-harness/master/docs/user/guide/providers.md),
[LLM layer](https://raw.githubusercontent.com/deepseek-ai/deepseek-harness/master/packages/llm/README.md),
[safety notice](https://raw.githubusercontent.com/deepseek-ai/deepseek-harness/master/SAFETY.md),
[license](https://github.com/deepseek-ai/deepseek-harness/blob/master/LICENSE).

**Verdict:** include in the proof of concept, particularly for native Python ergonomics and
DeepSeek-first deployments. Preview maturity is currently the reason to rank it behind Pi.

### Other scope worth keeping separate

The **OpenAI hosted Agents API** offers managed durable agent sessions and tools; it is a separate
option from the open-source Agents SDK and local Codex CLI. It can reduce orchestration work for
an OpenAI-only lane, but introduces hosted compute/tool costs and does not establish a common
native-provider runtime for all requested models.
Source: [hosted Agents API](https://developers.openai.com/api/docs/guides/agents-api/overview).

Calling DeepSeek directly through its OpenAI/Anthropic-compatible API is also viable, but that is
a transport choice. Without a harness/framework, we still own the tool loop, retries, sessions,
permissions, and accounting. No additional DeepSeek-specific wrapper is necessary just to reach
the model.
Source: [DeepSeek API introduction](https://api-docs.deepseek.com/).

## 3. Exact model IDs, routes, and prices

### Identity and endpoint selection

| Requested choice | Verified native model ID | Native route | OpenRouter model ID |
| --- | --- | --- | --- |
| DeepSeek V4.1 Flash, 1017 release | `deepseek-flash` currently serves `DeepSeek-V4.1-Flash-1017`; mutable alias | OpenAI-compatible base `https://api.deepseek.com`; Anthropic-compatible base `https://api.deepseek.com/anthropic` | `deepseek/deepseek-v4.1-flash-1017` |
| Claude Haiku 5.5 | `claude-haiku-5-5`; fixed ID without a dated suffix | Anthropic Messages `https://api.anthropic.com/v1/messages` | `anthropic/claude-haiku-5.5` |
| GPT-6.1 Luna | **Unverified; no exact public API ID established** | **Unresolved** | **Unresolved** |
| GPT-6 Luna, verified nearby option only | `gpt-6-luna` | OpenAI Responses `https://api.openai.com/v1/responses` | `openai/gpt-6-luna` |

Sources: [DeepSeek 1017 release](https://api-docs.deepseek.com/news/news261017/),
[DeepSeek API routes](https://api-docs.deepseek.com/),
[Haiku model/migration details](https://platform.claude.com/docs/en/models/haiku-5-5/migration-guide),
[OpenAI Luna](https://developers.openai.com/api/docs/models/gpt-6-luna),
[OpenRouter current model JSON](https://openrouter.ai/api/v1/models).

OpenRouter's base is `https://openrouter.ai/api/v1`. These are router model IDs, not native model
IDs. The public models API currently lists all three verified alternatives above. Routing changes,
provider selection, account settings, and surcharges can affect actual cost and behavior; persist
the actual provider endpoint. A router listing does not validate our harness adapter.
Source: [OpenRouter models API](https://openrouter.ai/api/v1/models).

### Standard native token pricing

**Each amount below is USD per 1,000,000 tokens. Divide by 1,000,000 for USD/token.**
Cached input is an alternative input category, not an additional charge on the same tokens.

| Model / condition | Uncached input | Cached input/read | Output | Explicit cache-write rates |
| --- | ---: | ---: | ---: | --- |
| DeepSeek Flash, off-peak | $0.15 | $0.003 | $0.60 | No separate write rate in this token table. |
| DeepSeek Flash, peak | $0.30 | $0.006 | $1.20 | Same qualification. |
| Haiku 5.5, prompt <=100K | $0.10 | $0.01 | $0.50 | 5 min: $0.125; 1 hour: $0.20. |
| Haiku 5.5, prompt >100K | $0.50 | $0.05 | $2.50 | 5 min: $0.625; 1 hour: $1.00. |
| GPT-6 Luna, prompt <=272K | $0.10 | $0.01 | $0.50 | Standard cache write: $0.125. |
| GPT-6 Luna, prompt >272K | $0.20 | $0.02 | $0.75 | Standard cache write: $0.25. |
| GPT-6.1 Luna | Unknown | Unknown | Unknown | Do not assign another model's price. |

Sources: [DeepSeek pricing](https://api-docs.deepseek.com/quick_start/pricing/),
[Haiku 5.5 pricing/overview](https://platform.claude.com/docs/en/models/haiku-5-5/overview),
[GPT-6 Luna model/pricing](https://developers.openai.com/api/docs/models/gpt-6-luna).

For an explicit per-token representation:

| Standard condition | Input USD/token | Cached input USD/token | Output USD/token |
| --- | ---: | ---: | ---: |
| DeepSeek off-peak | 0.00000015 | 0.000000003 | 0.00000060 |
| DeepSeek peak | 0.00000030 | 0.000000006 | 0.00000120 |
| Haiku <=100K / Luna <=272K | 0.00000010 | 0.00000001 | 0.00000050 |
| Haiku >100K | 0.00000050 | 0.00000005 | 0.00000250 |
| Luna >272K | 0.00000020 | 0.00000002 | 0.00000075 |

The per-token numbers are arithmetic conversions of the cited rates, not a separate tariff.

### Conditions that matter for salary estimates

- **DeepSeek:** peak windows are 01:00–04:00 and 06:00–10:00 UTC, Monday–Friday excluding Chinese
  public holidays. Legacy `deepseek-v4-flash` aliases route to the current Flash rather than pinning
  an old model. Search/Fetch can add $0.75 per 1,000 successful calls each; an applicable harness
  promotion ends **2026-10-31 16:00 UTC**. Do not build a lasting “free tools” assumption into salary.
  Sources: [pricing and tool charges](https://api-docs.deepseek.com/quick_start/pricing/),
  [1017 alias changes](https://api-docs.deepseek.com/news/news261017/).
- **Haiku:** crossing 100K prompt tokens changes the rate tier. The new model uses adaptive
  thinking and does not accept the old temperature/top-p/top-k controls. Tokenizer changes also
  make historical Haiku token estimates unreliable. Native model ID uses hyphens; OpenRouter's
  version uses a dot. Sources: [pricing](https://platform.claude.com/docs/en/models/haiku-5-5/overview),
  [migration/parameters](https://platform.claude.com/docs/en/models/haiku-5-5/migration-guide).
- **Verified Luna:** the >272K tier applies to the whole request; service tiers and region settings
  can change price. Use Responses for reasoning plus tool use: Chat Completions tool compatibility
  is restricted to reasoning effort `none`. A generic Chat Completions adapter is therefore an
  insufficient compatibility test. Sources: [model capabilities](https://developers.openai.com/api/docs/models/gpt-6-luna),
  [latest model integration guide](https://developers.openai.com/api/docs/guides/latest-model).
- **OpenRouter:** today's model API exposes the base prices and conditional overrides, including
  DeepSeek time windows and the two long-context thresholds. DeepSeek's landing-page headline and
  provider-detail prices are not identical; do not turn a “from” headline into a guaranteed tariff.
  Fetch model/provider pricing at configuration time and store the effective schedule.
  Sources: [machine-readable pricing](https://openrouter.ai/api/v1/models),
  [DeepSeek router listing](https://openrouter.ai/deepseek/deepseek-v4.1-flash-1017).

Native APIs are my preferred initial route: fewer transformations and clearer billing/capability
ownership. OpenRouter is a useful explicit user choice for consolidated credentials or routing,
with its own endpoint/model/pricing snapshot. Never silently fail over to a more expensive model.

## 4. Recommended agslack architecture

This section proposes design; it has not been implemented or benchmarked.

### Runtime boundary and process lifecycle

Keep `Agent.runtime` as the harness selector and add independent, validated model/provider and
budget configuration. A department/title is not a model ID. Store credential references, never
plaintext API keys in agent records or websocket payloads. Freeze a configuration revision for
each run: harness/version, endpoint, model ID, tools, pricing schedule, limits, and session ID.

The present `AgentRuntime.stream()` produces strings; the message router runs it in FastAPI
`BackgroundTasks`, with process-local pending/status maps. That is adequate for the stub, but not
durable real agents. Add a typed adapter boundary conceptually equivalent to:

`start/resume -> text_delta | tool_event | usage | approval | error | completed`

FastAPI should persist a run and enqueue it. A separate supervised worker owns the harness child,
streams normalized events, and survives API reloads. Use leases/idempotency so two workers cannot
run the same employee/session concurrently. This is a proposal based on the existing
`backend/app/runtime/base.py` and `backend/app/routers/messages.py`.

Use **one process per active employee**, lazily started, optionally kept warm for an idle TTL.
Persist sessions independently of process lifetime. Serialize work within an employee; queue new
messages unless steering is an explicit product feature. Eight hired employees need not mean
eight permanently resident Node processes. Measure cold start/RSS before choosing the warm pool.

Use a separate logical session per employee and conversation/task. A single eternal employee
transcript would mix departments, channels, permissions, and tool context. A warm process may
switch sessions only when idle. Session files live in private server-owned directories, keyed by
immutable IDs. Memory later should be separately scoped, curated facts with provenance, not an
unbounded transcript automatically injected everywhere.

### Streaming into the existing socket protocol

1. Persist the run and initial assistant message, then emit existing `message.created`.
2. Subscribe to Pi events before issuing `prompt`; correlate run, session, provider message, and
   content-block IDs. Convert only visible assistant `text_delta` into
   `message.delta` with `{id, channel_id, delta}`. Give later assistant turns their own message IDs.
3. Send tool activity and approvals through separate events/activity entries. Do not expose thinking,
   tool-call argument fragments, credentials, or raw terminal output as assistant prose.
4. Batch short deltas, approximately every 20–50 ms, with monotonic sequence numbers. Persist
   recovery checkpoints/final content; reconnection should load a snapshot plus later events.
5. Reconcile each finished message to authoritative content. Mark the employee idle when the run
   settles, not at the first tool round's end. Distinguish completion, cancellation, timeout,
   budget exhaustion, and failure; preserve partial output without presenting it as a full success.

The exact socket additions need design review, but existing `message.delta` rendering can survive
the switch. Do not hold a SQL transaction open while waiting on a model or shell tool.

### Salary and budget enforcement

Treat salary as a **spend allowance**, separate from XP or task rewards. Support run/daily/monthly
USD caps, with optional token, tool-call, request, wall-clock, and organization caps. Record period
timezone/reset semantics. Represent money with Decimal or integer minor accounting units.

Keep an append-only application ledger of reservation, measured usage, settlement, and correction.
Associate entries with employee/run/provider-request IDs and pricing revisions. Track uncached
input, cache reads/writes, output/reasoning, service tier, billable tools, and other provider costs
without double counting. Usage returned after cancellation/failure may be incomplete; hold a
conservative reservation for reconciliation rather than assume the interrupted call was free.

**Reserve atomically before every billable request**, including retries, compaction, helper models,
and subagents. Eight simultaneous employees can all pass an independent “remaining balance” check
and collectively overspend. Reserve a conservative input/context plus bounded output/tool cost;
settle to actual usage after completion. Unknown model prices should fail closed. Long-context
tiers, changing DeepSeek time windows, caches, and routing must be included in that estimate.

For stronger enforcement, place provider credentials in a **request-gating gateway** outside the
harness environment, and constrain employee network egress to it. Otherwise a shell tool or
extension with the API key can bypass an SDK budget hook. Harness-native limits remain useful
defense in depth, but are insufficient as the only shared cap.

A literal zero-overspend promise is unsafe without bounded provider charges and control over all
billable requests. Aborting cannot undo work already billed. Explicitly distinguish a locally
enforced reservation policy from estimated usage and eventual provider invoice reconciliation.
If adopting LiteLLM's proxy, provision its required durable database rather than assuming its
budget feature works with our existing SQLite setup.

### Isolation and credentials

- Separate working directories, Git worktrees, tool allowlists, and process-per-agent layouts help
  organization but are **not security isolation**. Prefer per-employee containers/VMs or equivalent
  OS restrictions; on Windows evaluate WSL2 containers or native isolation with tested boundaries.
- Supply private HOME/config/session roots and an environment allowlist. Do not inherit the host's
  global Pi/Claude/OpenCode credentials, repository secrets, or unrestricted filesystem mounts.
  Treat transcripts/tool logs as sensitive data with retention and deletion controls.
- Default business employees to scoped application tools. Enable filesystem writes, shell, network,
  purchases, external messages, or destructive tools only through explicit permissions. All agents
  in an organization should not receive the same powerful key merely for convenience.
- Pin and review extensions/packages; disable unapproved automatic project-extension loading.
  Server-derived workspace paths must not come from unsanitized handles/slugs. Kill the entire
  worker process tree/container on forced cancellation and enforce output/time/resource limits.
- On model/provider changes, create a compatible session lane or transfer a sanitized summary.
  Do not blindly replay another provider's private reasoning blocks or incompatible tool history.

## 5. Risks, unresolved decisions, and next experiments

The recommendation is **conditional**, not a claim that three live integrations passed:

1. Resolve “GPT-6.1 Luna” with the product owner. No invented `gpt-6.1-luna` setting or price.
2. Pin Pi 1.4.0 and a model-catalog snapshot. Run a native Windows RPC smoke test for each agreed
   model: visible streaming, one permitted tool call/result round trip, cancellation, and restart/
   resume. Specifically test DeepSeek reasoning history, Haiku parameter constraints, and Luna's
   Responses adapter. No paid calls were made for this research.
3. Verify emitted usage/cost against provider billing for cached/uncached calls and tier boundaries.
   Exercise retries, compaction, parallel employees, and budget exhaustion while a request runs.
4. Benchmark warm/cold latency and memory against Pydantic AI and the official DeepSeek SDK.
   Confirm that selected SDK features exist in the release, rather than only on repository HEAD.
5. Test credential isolation and tool escape attempts. Treat harness licenses, provider service
   terms, and model-routing availability as separate deployment checks.

The main risks are dependency/catalog churn, the unresolved model name, approximate accounting,
process/resource overhead, and granting a coding harness unnecessary privileges for office work.
Keeping the harness adapter, model route, budget ledger, and tool permissions separate makes the
initial Pi choice replaceable without rewriting chat or departments.
