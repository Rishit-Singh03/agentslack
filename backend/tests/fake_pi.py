"""Deterministic offline Pi RPC fixture; no network or credentials are used."""

import json
import os
import subprocess
import sys
import time


def emit(value):
    print(json.dumps(value), flush=True)


stats = {
    "assistantMessages": 0,
    "userMessages": 0,
    "contextUsage": {"tokens": 0},
    "tokens": {"input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0, "total": 0},
    "cost": 0,
}
if "--initial-context" in sys.argv:
    stats["contextUsage"]["tokens"] = int(sys.argv[sys.argv.index("--initial-context") + 1])
    stats["assistantMessages"] = stats["userMessages"] = 1
emit({"type": "runtime.ready", "tools": []})
if "--child" in sys.argv:
    # Inherit the RPC pipes: killing only the launcher would leave them open.
    child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(600)"])
    emit({"type": "runtime.child", "pid": child.pid})
for line in sys.stdin:
    command = json.loads(line)
    kind = command["type"]
    data = {}
    if kind == "get_session_stats":
        data = stats
    elif kind == "new_session":
        stats.update(assistantMessages=0, userMessages=0, contextUsage={"tokens": 0}, cost=0)
        stats["tokens"] = {"input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0, "total": 0}
        data = {"cancelled": False}
    elif kind == "prompt":
        data = {"disposition": "started"}
    emit({"id": command["id"], "type": "response", "command": kind, "success": True, "data": data})
    if kind != "prompt":
        continue
    text = command["message"]
    stats["userMessages"] += 1
    if "--relay-failure" in sys.argv:
        mode = sys.argv[sys.argv.index("--relay-failure") + 1]
        config = json.load(open(os.path.join(os.environ["PI_CODING_AGENT_DIR"], "models.json")))
        primary = config["providers"]["relay"]["baseUrl"].endswith("/primary")
        if primary or mode != "primary":
            if mode == "partial":
                emit(
                    {
                        "type": "message_update",
                        "assistantMessageEvent": {"type": "text_delta", "delta": "Partial reply"},
                    }
                )
            if mode == "usage":
                emit({"type": "relay.usage"})
            emit(
                {
                    "type": "relay.failure",
                    "kind": "http",
                    "status": 401 if mode == "auth" else 503,
                    "code": "model_not_found",
                }
            )
            emit(
                {
                    "type": "message_end",
                    "message": {
                        "role": "assistant",
                        "stopReason": "error",
                        "content": [
                            {"type": "text", "text": "Partial reply" if mode == "partial" else ""}
                        ],
                    },
                }
            )
            continue
    if "FAKE_EXIT" in text:
        sys.exit(3)
    if "FAKE_HANG" in text:
        time.sleep(600)
    if "FAKE_SLOW" in text:
        time.sleep(0.15)
    emit(
        {
            "type": "message_update",
            "assistantMessageEvent": {"type": "thinking_delta", "delta": "private thinking"},
        }
    )
    for delta in ["Hello ", "from the fake."]:
        emit(
            {
                "type": "message_update",
                "assistantMessageEvent": {"type": "text_delta", "delta": delta},
            }
        )
        if "--smoke" in sys.argv:
            time.sleep(0.8)
    answer = {
        "role": "assistant",
        "content": [{"type": "text", "text": "Hello from the fake (final)."}],
        "stopReason": "error" if "FAKE_ERROR" in text else "stop",
    }
    if not any(marker in text for marker in ("FAKE_MISSING", "FAKE_ERROR")):
        usage = {
            "input": 100,
            "output": 20,
            "cacheRead": 5,
            "cacheWrite": 0,
            "totalTokens": 125,
            "cost": {"total": 0.00002},
        }
        stats["assistantMessages"] += 1
        for key in ("input", "output", "cacheRead", "cacheWrite"):
            stats["tokens"][key] += usage[key]
        stats["tokens"]["total"] += usage["totalTokens"]
        stats["cost"] += usage["cost"]["total"]
        stats["contextUsage"] = {"tokens": stats["contextUsage"]["tokens"] + usage["totalTokens"]}
        if "FAKE_STATS" not in text:
            answer["usage"] = usage
    emit({"type": "message_end", "message": answer})
    emit({"type": "agent_settled", "aborted": False})
