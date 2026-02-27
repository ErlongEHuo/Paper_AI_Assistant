#!/usr/bin/env python3
import subprocess
import sys
from pathlib import Path

from config.settings import settings


def main() -> int:
    app_path = Path(__file__).resolve().parent / "streamlit_app.py"
    cmd = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(app_path),
        "--server.address",
        settings.HOST,
        "--server.port",
        str(settings.PORT),
    ]
    print(f"Starting Streamlit on http://{settings.HOST}:{settings.PORT}")
    return subprocess.call(cmd)


if __name__ == "__main__":
    raise SystemExit(main())
