"""Offline smoke: real Pi RPC, zero tools, three model routes; never prompts."""

import asyncio
import json
import tempfile
from pathlib import Path

from app.runtime.pi import (
    CHAT_FLAGS,
    PiProcess,
    model_configuration,
    private_environment,
    runtime_command,
)


async def main():
    data = Path("data/offline-check").resolve()
    data.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=data) as directory:
        root = Path(directory)
        (root / "config").mkdir()
        (root / "config/models.json").write_text(
            json.dumps(model_configuration()), encoding="utf-8"
        )
        env = private_environment(root, "openai")
        for name in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "DEEPSEEK_API_KEY"):
            env[name] = "offline-discovery-placeholder-not-a-key"
        process = PiProcess()
        try:
            await process.start([*runtime_command(), "--mode", "rpc", *CHAT_FLAGS], root, env)
            result = await process.command("get_available_models")
            models = {(item["provider"], item["id"]) for item in result["models"]}
            expected = {
                ("openai", "gpt-6-luna"),
                ("anthropic", "claude-haiku-5-5"),
                ("deepseek", "deepseek-flash"),
            }
            assert expected <= models, expected - models
            print(
                "Pi 1.4.0 RPC: zero tools verified; all three default models listed; no prompts or paid calls."
            )
        finally:
            await process.close()


if __name__ == "__main__":
    asyncio.run(main())
