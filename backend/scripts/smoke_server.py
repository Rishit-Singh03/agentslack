"""Browser-smoke server: substitutes only the child process, never calls a provider."""

import os
import sys
from pathlib import Path

import uvicorn

from app.config import settings
from app.runtime import pi


def main():
    fake = Path(__file__).resolve().parents[1] / "tests/fake_pi.py"
    pi.runtime_command = lambda: [sys.executable, "-u", str(fake), "--smoke"]
    for name in ("openai_api_key", "anthropic_api_key", "deepseek_api_key"):
        setattr(settings, name, "offline-browser-test-placeholder")
    settings.relay_key = None
    settings.relay_base_url = None
    settings.relay_reserve_url = None
    settings.runtime_data_dir = os.environ["SMOKE_RUNTIME_DIR"]
    uvicorn.run("app.main:app", host="127.0.0.1", port=int(sys.argv[1]))


if __name__ == "__main__":
    main()
