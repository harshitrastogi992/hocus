import { invoke } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";
import { useCallback, useEffect, useRef, useState } from "react";
import type { Catalog, Checks, ClientMessage, InstallState, ServerMessage, Settings, Status } from "./protocol";
import { playEffectSound } from "./sounds";

interface EngineInfo {
  url: string | null;
  error: string | null;
}

export interface Notice {
  id: number;
  level: "info" | "error";
  message: string;
}

export type Connection = "starting" | "connected" | "failed";

const EMPTY_STATUS: Status = {
  stage: "loading_models",
  phase: "present",
  effect: null,
  reactions: [],
  hold: null,
  background_ready: false,
  plate: "missing",
  plate_countdown: null,
  camera: { ok: false, error: null },
  virtual_camera: { active: false, device: null, error: null },
  fps: 0,
};

export function useEngine(onFrame: (frame: Blob) => void) {
  const [connection, setConnection] = useState<Connection>("starting");
  const [engineError, setEngineError] = useState<string | null>(null);
  const [settings, setSettings] = useState<Settings | null>(null);
  const [catalog, setCatalog] = useState<Catalog | null>(null);
  const [status, setStatus] = useState<Status>(EMPTY_STATUS);
  const [notices, setNotices] = useState<Notice[]>([]);
  const [checks, setChecks] = useState<Checks | null>(null);
  const [install, setInstall] = useState<InstallState | null>(null);
  const socket = useRef<WebSocket | null>(null);
  const frameHandler = useRef(onFrame);
  frameHandler.current = onFrame;

  const notify = useCallback((level: Notice["level"], message: string) => {
    const id = Date.now() + Math.random();
    setNotices((current) => [...current.slice(-3), { id, level, message }]);
    setTimeout(() => setNotices((current) => current.filter((n) => n.id !== id)), 6000);
  }, []);

  const dismiss = useCallback((id: number) => {
    setNotices((current) => current.filter((n) => n.id !== id));
  }, []);

  useEffect(() => {
    let disposed = false;
    let retry: ReturnType<typeof setTimeout> | undefined;

    const connect = (url: string) => {
      socket.current?.close();
      const ws = new WebSocket(url);
      ws.binaryType = "blob";
      socket.current = ws;
      ws.onopen = () => setConnection("connected");
      ws.onmessage = (event) => {
        if (typeof event.data !== "string") {
          frameHandler.current(event.data as Blob);
          return;
        }
        const message = JSON.parse(event.data) as ServerMessage;
        switch (message.type) {
          case "state":
            setSettings(message.settings);
            setCatalog(message.catalog);
            setStatus((current) => ({ ...current, ...message.status }));
            break;
          case "status": {
            const { type: _type, ...next } = message;
            setStatus(next);
            break;
          }
          case "effect":
            playEffectSound(message.effect, message.direction);
            break;
          case "notice":
            notify(message.level, message.message);
            break;
          case "checks": {
            const { type: _type, ...next } = message;
            setChecks(next);
            break;
          }
          case "install":
            setInstall({ state: message.state, message: message.message });
            if (message.message) notify(message.state === "failed" ? "error" : "info", message.message);
            break;
        }
      };
      ws.onclose = () => {
        if (disposed || socket.current !== ws) return;
        setConnection("starting");
        retry = setTimeout(poll, 800);
      };
    };

    const apply = (info: EngineInfo) => {
      if (info.error) {
        setEngineError(info.error);
        setConnection("failed");
      } else if (info.url) {
        setEngineError(null);
        connect(info.url);
      }
    };

    const poll = async () => {
      if (disposed) return;
      const info = await invoke<EngineInfo>("engine_info");
      if (info.url || info.error) apply(info);
      else retry = setTimeout(poll, 400);
    };

    const unlisten = listen<EngineInfo>("engine", (event) => apply(event.payload));
    poll();
    return () => {
      disposed = true;
      clearTimeout(retry);
      unlisten.then((stop) => stop());
      socket.current?.close();
    };
  }, [notify]);

  const send = useCallback((message: ClientMessage) => {
    if (socket.current?.readyState === WebSocket.OPEN) {
      socket.current.send(JSON.stringify(message));
    }
  }, []);

  const restart = useCallback(async () => {
    setConnection("starting");
    setEngineError(null);
    await invoke("restart_engine");
  }, []);

  return {
    connection,
    engineError,
    settings,
    catalog,
    status,
    checks,
    install,
    notices,
    dismiss,
    send,
    restart,
  };
}

export type Engine = ReturnType<typeof useEngine>;
