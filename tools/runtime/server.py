"""Command-line entrypoint for the local runtime server."""

from __future__ import annotations

import argparse

import uvicorn

from .runtime_app import create_app


app = create_app()


def main() -> None:
    """Run the development runtime server."""

    parser = argparse.ArgumentParser(description="Run the Pokemon FireRed runtime server.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8765, type=int)
    args = parser.parse_args()
    uvicorn.run("tools.runtime.server:app", host=args.host, port=args.port, reload=False)


if __name__ == "__main__":
    main()

