from __future__ import annotations

import argparse
import asyncio
import logging
import os
import secrets
import signal
import sys
import threading

from .paths import config_file
from .settings import SettingsStore


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="hocus-engine", description="Hocus effects engine")
    sub = parser.add_subparsers(dest="command", required=True)
    serve = sub.add_parser("serve", help="Run the engine and its local WebSocket server")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=0, help="0 picks a free port")
    serve.add_argument("--exit-with-stdin", action="store_true",
                       help="Quit when stdin closes (the desktop app owns stdin)")
    serve.add_argument("--demo", action="store_true",
                       help="Use a drawn placeholder person instead of the camera")
    sub.add_parser("models", help="Download the vision models and exit")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(level=os.environ.get("HOCUS_LOG", "WARNING"),
                        format="%(levelname)s %(name)s: %(message)s")
    if args.command == "models":
        from .vision.models import ensure_all

        for name, path in ensure_all().items():
            print(f"{name}: {path}")
        return 0

    from .server import run_server

    # The desktop app passes the token through the environment so it never shows up
    # in process listings.
    token = os.environ.get("HOCUS_TOKEN") or secrets.token_urlsafe(24)
    if "HOCUS_TOKEN" not in os.environ:
        print(f"HOCUS_TOKEN {token}", flush=True)

    async def runner() -> None:
        stop = asyncio.Event()
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, stop.set)
            except NotImplementedError:
                pass
        if args.exit_with_stdin:
            def watch_stdin() -> None:
                while sys.stdin.read(1024):
                    pass
                loop.call_soon_threadsafe(stop.set)

            threading.Thread(target=watch_stdin, daemon=True).start()
        await run_server(args.host, args.port, token, SettingsStore(config_file()), stop,
                         demo=args.demo)

    try:
        asyncio.run(runner())
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
