"""Command-line entrypoint for the local runtime server."""

from __future__ import annotations

import argparse
from pathlib import Path

import uvicorn

from .runtime_app import create_app
from .runtime_factory import create_runtime_from_config_path


app = create_app()


def main() -> None:
    """Run the development runtime server."""

    parser = argparse.ArgumentParser(description="Run the Pokemon FireRed runtime server.")
    parser.add_argument("--config", type=Path, help="Ignored local runtime config to launch a real emulator.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8765, type=int)
    args = parser.parse_args()
    runtime_app = create_app(create_runtime_from_config_path(args.config)) if args.config else app
    uvicorn.run(runtime_app, host=args.host, port=args.port, reload=False)


if __name__ == "__main__":
    main()
