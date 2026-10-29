import asyncio
import json

import pytest
from websockets.asyncio.client import connect
from websockets.exceptions import ConnectionClosed

from hocus import server
from hocus.settings import SettingsStore


class StubEngine:
    def __init__(self, store, emit, publish):
        self.store, self.emit, self.publish = store, emit, publish
        self.toggled = []

    def start(self):
        pass

    def stop(self):
        pass

    def status(self):
        return {"phase": "present"}

    def update_settings(self, patch):
        self.store.update(patch)

    def capture_plate(self):
        pass

    def toggle(self, effect):
        self.toggled.append(effect)
        self.emit({"type": "effect", "effect": effect, "direction": "out"})
        self.publish(b"\xff\xd8jpeg")


async def start(tmp_path, monkeypatch):
    monkeypatch.setattr(server, "Engine", StubEngine)
    stop = asyncio.Event()
    ready = asyncio.get_running_loop().create_future()

    def capture_port(*args, **kwargs):
        text = " ".join(str(a) for a in args)
        if text.startswith("HOCUS_READY") and not ready.done():
            ready.set_result(int(text.split()[1]))

    monkeypatch.setattr("builtins.print", capture_port)
    task = asyncio.create_task(server.run_server(
        "127.0.0.1", 0, "secret", SettingsStore(tmp_path / "s.json"), stop))
    return await asyncio.wait_for(ready, 5), stop, task


def test_protocol_round_trip(tmp_path, monkeypatch):
    async def scenario():
        port, stop, task = await start(tmp_path, monkeypatch)
        async with connect(f"ws://127.0.0.1:{port}/?token=secret") as ws:
            state = json.loads(await ws.recv())
            assert state["type"] == "state"
            checks = json.loads(await ws.recv())
            assert checks["type"] == "checks" and checks["items"][0]["id"] == "os"
            kinds = {e["id"]: e["kind"] for e in state["catalog"]["effects"]}
            assert kinds["stardust"] == "vanish" and kinds["clones"] == "toggle"
            assert kinds["confetti"] == "reaction"

            await ws.send(json.dumps({"type": "update_settings",
                                      "patch": {"effects": {"blink": {"gesture": "v_sign"}}}}))
            notice = json.loads(await ws.recv())
            assert notice["level"] == "error" and "both use" in notice["message"]
            reverted = json.loads(await ws.recv())
            assert reverted["settings"]["effects"]["blink"]["gesture"] == "forehead_tap"

            await ws.send(json.dumps({"type": "toggle", "effect": "blink"}))
            received = [await ws.recv(), await ws.recv()]
            assert b"\xff\xd8jpeg" in received
            assert any(isinstance(m, str) and json.loads(m)["type"] == "effect"
                       for m in received)
        stop.set()
        await task

    asyncio.run(scenario())


def test_wrong_token_is_refused(tmp_path, monkeypatch):
    async def scenario():
        port, stop, task = await start(tmp_path, monkeypatch)
        async with connect(f"ws://127.0.0.1:{port}/?token=nope") as ws:
            with pytest.raises(ConnectionClosed) as closed:
                await ws.recv()
            assert closed.value.rcvd.code == 4401
        stop.set()
        await task

    asyncio.run(scenario())
