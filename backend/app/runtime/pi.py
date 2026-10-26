"""Chat-only Pi RPC supervision. One API worker; no paid calls outside prompt()."""

import asyncio
import concurrent.futures
import contextlib
import hashlib
import json
import math
import os
import shutil
import signal
import subprocess
import threading
from contextlib import asynccontextmanager
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from sqlmodel import Session, select

from ..budget import estimate_input_tokens, finish, reserve, validate_price
from ..config import settings
from ..model_catalog import PROVIDERS, find_model, provider_key
from ..models import Channel, Department, Organization
from ..relay import cached_models, list_price_usage, may_failover, refresh_pricing, resolve_route

RUNTIME_NODE = Path(__file__).resolve().parents[2] / "runtime-node"
CHAT_FLAGS = [
    "--no-tools",
    "--no-extensions",
    "--no-skills",
    "--no-mcp",
    "--no-context-files",
    "--no-prompt-templates",
]


class RuntimeFailure(Exception):
    """Safe user-facing error: never expose provider output or environment values."""


class RelayFailure(RuntimeFailure):
    def __init__(self, model_id, retryable=False, status=None):
        if status in {401, 403}:
            message = f"{model_id}: Relay authentication failed. Check RELAY_KEY and model access."
        elif status is not None and 400 <= status < 500:
            message = f"{model_id}: The relay rejected this request (HTTP {status}). Check model parameters and access."
        else:
            message = f"{model_id}: The relay reports this model is temporarily unavailable. Retry later; no model was substituted."
        super().__init__(message)
        self.retryable = retryable


def runtime_command():
    node = shutil.which("node")
    entry = RUNTIME_NODE / "node_modules/@earendil-works/pi-coding-agent/dist/cli.js"
    if not node or not entry.is_file():
        raise RuntimeFailure(
            "Pi is not installed. Run npm ci in backend/runtime-node with Node 22.19+."
        )
    return [node, "--import", (RUNTIME_NODE / "guard.mjs").as_uri(), str(entry)]


def private_environment(root, provider, max_output_tokens=4096):
    allowed = {"PATH", "SYSTEMROOT", "WINDIR", "COMSPEC", "PATHEXT", "LANG", "LC_ALL"}
    env = {key: value for key, value in os.environ.items() if key.upper() in allowed}
    env.update(
        HOME=str(root),
        USERPROFILE=str(root),
        TEMP=str(root),
        TMP=str(root),
        PI_CODING_AGENT_DIR=str(root / "config"),
        PI_CODING_AGENT_SESSION_DIR=str(root / "sessions"),
        PI_OFFLINE="1",
        PI_SKIP_VERSION_CHECK="1",
        AGENTSLACK_MAX_OUTPUT_TOKENS=str(max_output_tokens),
    )
    key = provider_key(provider)
    if key:
        env[PROVIDERS[provider]] = key
    return env


def model_configuration(relay_url=None):
    providers = {}
    for item in cached_models():
        model = {
            "id": item["model_id"],
            "name": item["name"],
            "api": item["api"],
            "reasoning": len(item["thinking_levels"]) > 1,
            "input": ["text"],
            "contextWindow": item["context"],
            "maxTokens": item["max_output"],
            "cost": {
                "input": float(item["input"]),
                "output": float(item["output"]),
                "cacheRead": float(item["cached"]),
                "cacheWrite": float(item["cache_write"]),
            },
        }
        if item["provider"] == "relay":
            if relay_url or settings.relay_base_url:
                provider = providers.setdefault(
                    "relay",
                    {
                        "baseUrl": relay_url or settings.relay_base_url,
                        "apiKey": "$RELAY_KEY",
                        "models": [],
                    },
                )
                model["compat"] = {
                    "supportsUsageInStreaming": True,
                    "supportsStore": False,
                    "supportsDeveloperRole": False,
                    "maxTokensField": "max_tokens",
                }
                model["reasoning"] = True
                model["thinkingLevelMap"] = {"off": "none"}
                model["compat"]["supportsReasoningEffort"] = True
                if item["model_id"] == "deepseek-v4.1-flash-1017":
                    model["compat"]["thinkingFormat"] = "deepseek"
                provider["models"].append(model)
        else:
            # Preserve built-in reasoning compatibility and conditional pricing metadata.
            provider = providers.setdefault(item["provider"], {"modelOverrides": {}})
            provider["modelOverrides"][item["model_id"]] = {
                "contextWindow": item["context"],
                "maxTokens": item["max_output"],
            }
    return {"providers": providers}


def valid_usage(value):
    if not isinstance(value, dict) or not isinstance(value.get("cost"), dict):
        return False
    fields = [value.get(k) for k in ("input", "output", "cacheRead", "cacheWrite", "totalTokens")]
    fields.append(value["cost"].get("total"))
    return all(
        isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) and v >= 0
        for v in fields
    )


def stats_delta(before, after):
    if (
        not before
        or not after
        or after.get("assistantMessages", 0) <= before.get("assistantMessages", 0)
    ):
        return None
    try:
        tokens = {
            key: after["tokens"][key] - before["tokens"][key]
            for key in ("input", "output", "cacheRead", "cacheWrite")
        }
        tokens["totalTokens"] = after["tokens"]["total"] - before["tokens"]["total"]
        tokens["cost"] = {
            "total": float(Decimal(str(after["cost"])) - Decimal(str(before["cost"])))
        }
        return tokens if valid_usage(tokens) and tokens["totalTokens"] > 0 else None
    except (KeyError, TypeError):
        return None


def current_context_tokens(stats):
    tokens = (stats.get("contextUsage") or {}).get("tokens")
    if (
        isinstance(tokens, (int, float))
        and not isinstance(tokens, bool)
        and math.isfinite(tokens)
        and tokens >= 0
    ):
        return math.ceil(tokens)
    # A confirmed empty session has no retained transcript, even before its first usage report.
    if stats.get("assistantMessages") == 0 and stats.get("userMessages") == 0:
        return 0
    return None


class PiProcess:
    """Threaded pipes work on both Windows selector and proactor event loops."""

    def __init__(self):
        self.process = None
        self.reader = None
        self.stderr_reader = None
        self.exited = False
        self.job = None
        self.responses = {}
        self.events = asyncio.Queue(maxsize=1024)
        self.loop = None
        self.stopping = threading.Event()
        self.stdin_lock = threading.Lock()
        self.close_lock = asyncio.Lock()

    def _spawn(self, args, cwd, env):
        if os.name == "nt":
            options = {
                "creationflags": subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP
            }
        else:
            options = {"start_new_session": True}
        self.process = subprocess.Popen(
            args,
            cwd=cwd,
            env=env,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            **options,
        )
        if os.name == "nt":
            from .windows_job import WindowsJob

            self.job = WindowsJob(self.process._handle)

    async def start(self, args, cwd, env):
        self.loop = asyncio.get_running_loop()
        spawn = asyncio.create_task(asyncio.to_thread(self._spawn, args, cwd, env))
        try:
            # Cancellation must not leave a child created by an unfinished spawn thread.
            await asyncio.shield(spawn)
        except BaseException as exc:
            with contextlib.suppress(Exception):
                await spawn
            await self.close()
            if isinstance(exc, OSError):
                raise RuntimeFailure(
                    "Pi could not start. Check Node and the local runtime installation."
                ) from exc
            raise
        self.reader = threading.Thread(target=self._read, name="pi-stdout", daemon=True)
        self.stderr_reader = threading.Thread(
            target=self._drain_stderr, name="pi-stderr", daemon=True
        )
        self.reader.start()
        self.stderr_reader.start()
        try:
            event = await asyncio.wait_for(self.events.get(), 30)
            if event.get("type") != "runtime.ready" or event.get("tools") != []:
                raise RuntimeFailure(
                    "Pi startup refused: zero exposed tools could not be verified."
                )
            await self.command("set_auto_retry", enabled=False)
            await self.command("set_auto_compaction", enabled=False)
        except BaseException:
            await self.close()
            raise

    def _drain_stderr(self):
        # Provider diagnostics may contain secrets. Drain without logging raw data.
        try:
            while self.process.stderr.read(8192):
                pass
        except OSError:
            pass

    async def _deliver(self, event):
        if event.get("type") == "response":
            future = self.responses.get(event.get("id"))
            if future and not future.done():
                future.set_result(event)
        else:
            await self.events.put(event)

    def _read(self):
        try:
            while not self.stopping.is_set():
                # LF framing, bounded just like the former asyncio StreamReader.
                line = self.process.stdout.readline(8 * 1024 * 1024 + 1)
                if not line:
                    break
                if len(line) > 8 * 1024 * 1024:
                    raise ValueError("RPC line too long")
                event = json.loads(line)
                # run_coroutine_threadsafe uses loop.call_soon_threadsafe. Waiting for
                # delivery preserves ordering/backpressure without touching asyncio
                # queues or futures on this reader thread.
                delivery = asyncio.run_coroutine_threadsafe(self._deliver(event), self.loop)
                while True:
                    try:
                        delivery.result(timeout=0.1)
                        break
                    except concurrent.futures.TimeoutError:
                        if self.stopping.is_set():
                            delivery.cancel()
                            return
        except (ValueError, OSError, RuntimeError, concurrent.futures.CancelledError):
            pass
        finally:
            with contextlib.suppress(RuntimeError):
                self.loop.call_soon_threadsafe(self._notify_exit)

    def _notify_exit(self):
        if self.exited:
            return
        self.exited = True
        if self.process:
            self.process.poll()
        for future in self.responses.values():
            if not future.done():
                future.set_exception(RuntimeFailure("Pi exited or its RPC stream failed."))
        if self.events.full():
            self.events.get_nowait()
        self.events.put_nowait({"type": "runtime.exit"})

    def _write(self, data):
        with self.stdin_lock:
            if self.stopping.is_set():
                raise BrokenPipeError("Pi is shutting down")
            self.process.stdin.write(data)
            self.process.stdin.flush()

    async def command(self, kind, timeout=30, **data):
        if self.exited or self.process.poll() is not None:
            raise RuntimeFailure("Pi exited before completing the reply.")
        identifier = uuid4().hex
        future = asyncio.get_running_loop().create_future()
        self.responses[identifier] = future
        try:
            async with asyncio.timeout(timeout):
                await asyncio.to_thread(
                    self._write,
                    (json.dumps({"id": identifier, "type": kind, **data}) + "\n").encode(),
                )
                result = await future
            if not result.get("success"):
                raise RuntimeFailure(
                    "Pi/provider rejected the request. Check model configuration and credentials."
                )
            return result.get("data", {})
        except (OSError, ConnectionError, TimeoutError) as exc:
            raise RuntimeFailure("Pi RPC connection failed or timed out.") from exc
        finally:
            self.responses.pop(identifier, None)

    async def close(self):
        async with self.close_lock:
            self.stopping.set()
            if self.job:
                self.job.close()
                self.job = None
            elif self.process and self.process.poll() is None:
                if os.name == "nt":
                    self.process.kill()
                else:
                    with contextlib.suppress(ProcessLookupError):
                        os.killpg(self.process.pid, signal.SIGKILL)
            if self.process:
                await asyncio.to_thread(self.process.wait, timeout=5)
            for reader in (self.reader, self.stderr_reader):
                if reader:
                    await asyncio.to_thread(reader.join, 5)
                    if reader.is_alive():
                        raise RuntimeFailure("Pi pipe reader did not shut down.")
            if self.process:
                for pipe in (self.process.stdin, self.process.stdout, self.process.stderr):
                    pipe.close()
            self._notify_exit()


class AgentSlot:
    def __init__(self):
        self.lock = asyncio.Lock()
        self.waiting = 0
        self.process = None
        self.identity = None
        self.expiry = None


class PiSupervisor:
    def __init__(self):
        self.slots = {}
        self.closed = False

    @asynccontextmanager
    async def acquire(self, agent_id):
        if self.closed:
            raise RuntimeFailure("Runtime is shutting down. Retry after restart.")
        slot = self.slots.setdefault(agent_id, AgentSlot())
        if slot.waiting >= settings.pi_queue_size:
            raise RuntimeFailure("Agent queue is full. Wait for a reply before trying again.")
        slot.waiting += 1
        try:
            async with slot.lock:
                if slot.expiry:
                    slot.expiry.cancel()
                if self.closed:
                    raise RuntimeFailure("Runtime is shutting down.")
                yield slot
        finally:
            slot.waiting -= 1
            if not self.closed and not slot.waiting:
                slot.expiry = asyncio.create_task(self._expire(slot))

    async def _expire(self, slot):
        await asyncio.sleep(settings.pi_idle_ttl)
        async with slot.lock:
            if slot.process:
                await slot.process.close()
                slot.process = None

    async def abort(self, agent_id):
        slot = self.slots.get(agent_id)
        if slot and slot.process:
            # Killing the tree makes EOF terminal, even if RPC abort cannot acknowledge.
            await slot.process.close()
            slot.process = None

    async def close(self):
        self.closed = True
        for slot in self.slots.values():
            if slot.expiry:
                slot.expiry.cancel()
            if slot.process:
                await slot.process.close()
        self.slots.clear()

    async def process_for(self, slot, agent, channel, prompt, relay_url=None):
        identity = hashlib.sha256(
            json.dumps(
                [
                    agent.provider,
                    agent.model_id,
                    agent.thinking_level,
                    agent.max_output_tokens,
                    prompt,
                    relay_url,
                ]
            ).encode()
        ).hexdigest()[:20]
        identity = f"{channel.id}-{identity}"
        if slot.process and slot.identity == identity and slot.process.process.poll() is None:
            return slot.process
        if slot.process:
            await slot.process.close()
        root = Path(settings.runtime_data_dir).resolve() / str(agent.id)
        cwd = root / "work"
        config = root / "config"
        sessions = root / "sessions" / identity
        for path in (cwd, config, sessions):
            path.mkdir(mode=0o700, parents=True, exist_ok=True)
            if os.name != "nt":
                path.chmod(0o700)
        (config / "models.json").write_text(
            json.dumps(model_configuration(relay_url)), encoding="utf-8"
        )
        (config / "settings.json").write_text(
            json.dumps(
                {
                    "compaction": {"enabled": False},
                    "retry": {"enabled": False, "provider": {"maxRetries": 0}},
                    "cacheWarming": "off",
                }
            ),
            encoding="utf-8",
        )
        args = [
            *runtime_command(),
            "--mode",
            "rpc",
            *CHAT_FLAGS,
            "--provider",
            agent.provider,
            "--model",
            agent.model_id,
            "--thinking",
            agent.thinking_level,
            "--session-dir",
            str(sessions),
            "--continue",
            "--system-prompt",
            prompt,
        ]
        process = PiProcess()
        await process.start(
            args, cwd, private_environment(root, agent.provider, agent.max_output_tokens)
        )
        slot.process, slot.identity = process, identity
        return process


supervisor = PiSupervisor()


class PiRuntime:
    async def events(self, bind, agent, message, context):
        route = resolve_route(agent.provider, agent.model_id)
        routed = agent.model_copy(
            update={"provider": route["provider"], "model_id": route["model_id"]}
        )
        if routed.provider == "relay":
            await refresh_pricing()
        endpoints = [settings.relay_base_url]
        if (
            routed.provider == "relay"
            and settings.relay_reserve_url
            and settings.relay_reserve_url != settings.relay_base_url
        ):
            endpoints.append(settings.relay_reserve_url)
        for attempt, endpoint in enumerate(endpoints):
            try:
                async for event in self._attempt(bind, routed, message, context, endpoint):
                    yield event
                return
            except RelayFailure as exc:
                if not exc.retryable or attempt + 1 == len(endpoints):
                    raise

    async def _attempt(self, bind, agent, message, context, endpoint=None):
        self.usage = None
        self.model_id = agent.model_id
        if not provider_key(agent.provider):
            raise RuntimeFailure(
                f"Missing provider key. Set {PROVIDERS.get(agent.provider, 'a supported provider key')} in backend .env."
            )
        if agent.provider == "relay" and not settings.relay_base_url:
            raise RuntimeFailure("Relay is missing RELAY_BASE_URL in backend .env.")
        model = find_model(agent.provider, agent.model_id)
        validate_price(model)
        async with supervisor.acquire(agent.id) as slot:
            with Session(bind) as session:
                org = session.exec(select(Organization)).one()
                channel = session.get(Channel, message.channel_id)
                department = (
                    session.get(Department, agent.department_id) if agent.department_id else None
                )
                prompt = (
                    f"You are {agent.name}, {agent.title}, at {org.name}.\n"
                    f"Department: {department.name if department else 'Unassigned'}.\n"
                    f"Skills: {', '.join(agent.skills)}. Bio: {agent.bio}\n"
                    f"Channel: #{channel.name}. Topic: {channel.topic}\n"
                    "You are chat-only. Do not claim to execute tools or complete external actions."
                )
            ledger_id = None
            process, baseline, usage = None, None, None
            failure = {}
            streamed = usage_reported = False
            started = False
            try:
                process = await supervisor.process_for(
                    slot, agent, channel, prompt, endpoint if agent.provider == "relay" else None
                )
                baseline = await process.command("get_session_stats")
                # Channel history is quoted data, not privileged system instructions.
                history = "\n".join(f"{item.author_type}: {item.body}" for item in context[-20:])
                rpc_prompt = f"Channel context (quoted):\n{history}\n\nReply to: {message.body}"
                input_tokens = estimate_input_tokens(
                    current_context_tokens(baseline), rpc_prompt, prompt
                )
                if (
                    input_tokens is not None
                    and input_tokens + agent.max_output_tokens >= model["context"] * 0.9
                ):
                    # New session persists in the same agent/channel directory and becomes
                    # the latest session for --continue after idle expiry or API restart.
                    result = await process.command("new_session")
                    if result.get("cancelled"):
                        raise RuntimeFailure(
                            "Pi could not start a fresh session near the context limit."
                        )
                    baseline = await process.command("get_session_stats")
                    # Limit the reseeded channel history as well, or a very large quoted
                    # transcript would immediately overflow the new session again.
                    rpc_prompt = (
                        "A fresh chat session was started because the previous one was near its context limit.\n"
                        f"Recent channel context (quoted):\n{history[-6000:]}\n\nReply to: {message.body}"
                    )
                    input_tokens = estimate_input_tokens(
                        current_context_tokens(baseline), rpc_prompt, prompt
                    )
                    yield {
                        "type": "system",
                        "text": f"{agent.handle}: Started a fresh session because the previous chat was near its context limit.",
                    }
                    if (
                        input_tokens is not None
                        and input_tokens + agent.max_output_tokens >= model["context"]
                    ):
                        raise RuntimeFailure(
                            "This message and its output allowance exceed the model's context limit."
                        )
                ledger_id = await reserve(bind, agent, channel.id, model, input_tokens)
                started = True  # A write/ack failure cannot prove that no billing occurred.
                ack = await process.command(
                    "prompt",
                    message=rpc_prompt,
                )
                if ack.get("disposition") == "handled":
                    started = False
                    raise RuntimeFailure("Pi handled the prompt without generating a reply.")
                async with asyncio.timeout(settings.pi_timeout):
                    while True:
                        event = await process.events.get()
                        kind = event.get("type")
                        if kind == "relay.failure":
                            failure = event
                        elif kind == "relay.usage":
                            usage_reported = True
                        elif kind == "message_update":
                            delta = event.get("assistantMessageEvent", {})
                            if delta.get("type") == "text_delta":
                                streamed = streamed or bool(delta["delta"])
                                yield {"type": "text", "text": delta["delta"]}
                        elif (
                            kind == "message_end"
                            and event.get("message", {}).get("role") == "assistant"
                        ):
                            answer = event["message"]
                            candidate = answer.get("usage")
                            if valid_usage(candidate) and (
                                candidate["totalTokens"] > 0
                                or (
                                    agent.provider != "relay"
                                    and answer.get("stopReason") not in {"error", "aborted"}
                                )
                            ):
                                usage = candidate
                                usage_reported = True
                            yield {
                                "type": "final",
                                "text": "".join(
                                    part.get("text", "")
                                    for part in answer.get("content", [])
                                    if part.get("type") == "text"
                                ),
                            }
                            if answer.get("stopReason") in {"error", "aborted"}:
                                if agent.provider == "relay":
                                    raise RelayFailure(
                                        agent.model_id,
                                        may_failover(failure, streamed, usage_reported),
                                    )
                                raise RuntimeFailure(
                                    "Provider error or reply aborted. Check credentials, model access, and provider availability."
                                )
                        elif kind == "agent_settled":
                            if event.get("aborted"):
                                raise RuntimeFailure("Reply aborted.")
                            break
                        elif kind in {"runtime.exit", "error"}:
                            raise RuntimeFailure(
                                "Pi exited or reported a provider error before the reply finished."
                            )
                if usage is None:
                    usage = stats_delta(baseline, await process.command("get_session_stats"))
                if usage is not None:
                    if agent.provider == "relay":
                        usage = list_price_usage(usage, model)
                    yield {"type": "usage", "usage": usage, "model_id": agent.model_id}
            except BaseException as exc:
                if agent.provider == "relay" and isinstance(exc, TimeoutError):
                    failure = {"kind": "timeout"}
                if process and process.process.poll() is None:
                    if usage is None and baseline:
                        with contextlib.suppress(Exception):
                            usage = stats_delta(
                                baseline, await process.command("get_session_stats", timeout=2)
                            )
                    await process.close()
                    slot.process = None
                if agent.provider == "relay" and (
                    isinstance(exc, TimeoutError) or isinstance(exc, RelayFailure)
                ):
                    retryable = may_failover(failure, streamed, usage_reported or usage is not None)
                    if retryable:
                        started = False
                    raise RelayFailure(agent.model_id, retryable, failure.get("status")) from exc
                if isinstance(exc, TimeoutError):
                    raise RuntimeFailure(
                        "Pi reply timed out. Usage may remain reserved for reconciliation."
                    ) from exc
                raise
            finally:
                if usage is not None and agent.provider == "relay":
                    usage = list_price_usage(usage, model)
                self.usage = usage
                if ledger_id is not None:
                    finish(bind, ledger_id, usage, started)
