"""Local WebSocket bridge between the desktop UI and the engine.

Text messages carry JSON (see docs/protocol.md); binary messages are JPEG preview frames.
"""

from __future__ import annotations

import asyncio
import hmac
import json
import logging
from typing import Any
from urllib.parse import parse_qs, urlparse

from websockets.asyncio.server import ServerConnection, serve

from . import system
from .backgrounds import PRESETS, preset_thumbnail
from .engine import Engine
from .gestures.catalog import GESTURES
from .settings import ALL_TYPES, RESOLUTIONS, SettingsError, SettingsStore

log = logging.getLogger(__name__)


def catalog() -> dict[str, Any]:
    return {
        "effects": [{"id": e.id, "name": e.name, "description": e.description,
                     "default_gesture": e.default_gesture, "kind": e.kind,
                     "active_label": e.active_label} for e in ALL_TYPES],
        "gestures": [{"id": g.id, "label": g.label, "hint": g.hint,
                      "hold_seconds": g.hold_seconds} for g in GESTURES.values()],
        "presets": [{"id": key, "label": label, "thumbnail": preset_thumbnail(key)}
                    for key, (label, _) in PRESETS.items()],
        "resolutions": [list(r) for r in RESOLUTIONS],
    }


class Client:
    def __init__(self, connection: ServerConnection) -> None:
        self.connection = connection
        self.frame: bytes | None = None
        self.frame_ready = asyncio.Event()

    async def pump_frames(self) -> None:
        """Send only the newest frame, so a slow client drops frames instead of lagging."""
        while True:
            await self.frame_ready.wait()
            self.frame_ready.clear()
            frame, self.frame = self.frame, None
            if frame is not None:
                await self.connection.send(frame)


class Bridge:
    def __init__(self, store: SettingsStore, token: str, demo: bool = False) -> None:
        self.store = store
        self.token = token
        self.clients: set[Client] = set()
        self.installing = False
        self.loop = asyncio.get_running_loop()
        sources = {}
        if demo:
            from .demo import DemoVision, open_demo_camera

            sources = {"vision_factory": DemoVision, "camera_factory": open_demo_camera}
        self.engine = Engine(store, self._emit_threadsafe, self._publish_threadsafe, **sources)

    def _emit_threadsafe(self, message: dict[str, Any]) -> None:
        self.loop.call_soon_threadsafe(self._broadcast, json.dumps(message))

    def _publish_threadsafe(self, frame: bytes) -> None:
        self.loop.call_soon_threadsafe(self._offer_frame, frame)

    def _broadcast(self, text: str) -> None:
        for client in list(self.clients):
            asyncio.ensure_future(_safe_send(client.connection, text))

    def _offer_frame(self, frame: bytes) -> None:
        for client in self.clients:
            client.frame = frame
            client.frame_ready.set()

    def state(self) -> str:
        return json.dumps({"type": "state", "settings": self.store.current,
                           "catalog": catalog(), "status": self.engine.status()})

    def authorised(self, connection: ServerConnection) -> bool:
        query = parse_qs(urlparse(connection.request.path).query)
        offered = query.get("token", [""])[0]
        return hmac.compare_digest(offered.encode(), self.token.encode())

    async def handle(self, connection: ServerConnection) -> None:
        if not self.authorised(connection):
            await connection.close(code=4401, reason="Invalid token")
            return
        client = Client(connection)
        self.clients.add(client)
        pump = asyncio.create_task(client.pump_frames())
        try:
            await connection.send(self.state())
            await self._send_checks(connection)
            async for raw in connection:
                if isinstance(raw, str):
                    await self._command(connection, raw)
        finally:
            pump.cancel()
            self.clients.discard(client)

    async def _send_checks(self, connection: ServerConnection | None = None) -> None:
        checks = await asyncio.to_thread(system.run_checks)
        text = json.dumps({"type": "checks", **checks})
        if connection is None:
            self._broadcast(text)
        else:
            await connection.send(text)

    async def _install_obs(self) -> None:
        if self.installing:
            return
        self.installing = True
        self._broadcast(json.dumps({"type": "install", "state": "running"}))
        try:
            ok, message = await asyncio.to_thread(system.install_obs)
        finally:
            self.installing = False
        self._broadcast(json.dumps({"type": "install", "state": "done" if ok else "failed",
                                    "message": message}))
        await self._send_checks()

    async def _command(self, connection: ServerConnection, raw: str) -> None:
        try:
            message = json.loads(raw)
            kind = message.get("type")
            if kind == "update_settings":
                self.engine.update_settings(message.get("patch", {}))
                self._broadcast(self.state())
            elif kind == "capture_plate":
                self.engine.capture_plate()
            elif kind == "toggle":
                self.engine.toggle(message.get("effect"))
            elif kind == "get_state":
                await connection.send(self.state())
            elif kind == "run_checks":
                await self._send_checks(connection)
            elif kind == "install_obs":
                asyncio.ensure_future(self._install_obs())
            elif kind == "open_obs":
                ok, message = system.open_obs()
                await connection.send(json.dumps(
                    {"type": "notice", "level": "info" if ok else "error", "message": message}))
            else:
                raise SettingsError(f"Unknown command: {kind}")
        except (SettingsError, ValueError, TypeError, KeyError) as error:
            await connection.send(json.dumps(
                {"type": "notice", "level": "error", "message": str(error)}))
            await connection.send(self.state())


async def _safe_send(connection: ServerConnection, text: str) -> None:
    try:
        await connection.send(text)
    except Exception:  # noqa: BLE001 - a closed client must not break the broadcast
        log.debug("Dropped message to a closed client")


async def run_server(host: str, port: int, token: str, store: SettingsStore,
                     stop: asyncio.Event, demo: bool = False) -> None:
    bridge = Bridge(store, token, demo)
    async with serve(bridge.handle, host, port, max_size=2**20) as server:
        actual_port = server.sockets[0].getsockname()[1]
        print(f"HOCUS_READY {actual_port}", flush=True)
        bridge.engine.start()
        try:
            await stop.wait()
        finally:
            bridge.engine.stop()
