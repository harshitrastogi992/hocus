import { openUrl } from "@tauri-apps/plugin-opener";
import { Check, CircleAlert, LoaderCircle, RotateCcw, TriangleAlert } from "lucide-react";
import { useEffect, useRef } from "react";
import type { Engine } from "../lib/useEngine";
import { Button, cx } from "./ui";

type RowState = "pending" | "ok" | "warn" | "fail";

interface CheckRow {
  id: string;
  label: string;
  state: RowState;
  detail: string;
  optional?: boolean;
  action?: { label: string; run: () => void };
}

const AUTO_CONTINUE_MS = 900;

export function StartupScreen({
  engine,
  onContinue,
  onSetUpMeetings,
}: {
  engine: Engine;
  onContinue: () => void;
  onSetUpMeetings: () => void;
}) {
  const { connection, status, checks, restart } = engine;
  const running = connection === "connected" && status.stage === "running";
  const os = checks?.items.find((item) => item.id === "os");
  const obs = checks?.items.find((item) => item.id === "obs");

  const rows: CheckRow[] = [
    {
      id: "engine",
      label: "Engine",
      state: connection === "connected" ? "ok" : connection === "failed" ? "fail" : "pending",
      detail:
        connection === "failed"
          ? (engine.engineError ?? "The engine stopped.")
          : connection === "connected"
            ? "Running on this computer"
            : "Starting",
      action: connection === "failed" ? { label: "Restart", run: restart } : undefined,
    },
    {
      id: "os",
      label: "System",
      state: os ? os.state : "pending",
      detail: os?.detail ?? "Checking",
    },
    {
      id: "models",
      label: "Vision models",
      state:
        connection !== "connected"
          ? "pending"
          : status.stage === "failed"
            ? "fail"
            : status.stage === "loading_models"
              ? "pending"
              : "ok",
      detail:
        status.stage === "failed"
          ? "The models could not be loaded. Check your internet connection for the first run, then restart."
          : status.stage === "loading_models"
            ? "Loading. The first run downloads about 12 MB."
            : "Hands, face and person segmentation ready",
      action: status.stage === "failed" ? { label: "Restart", run: restart } : undefined,
    },
    {
      id: "camera",
      label: "Camera access",
      state: !running ? "pending" : status.camera.ok ? "ok" : "fail",
      detail: !running
        ? "Waiting for the models"
        : status.camera.ok
          ? "Camera connected"
          : "No picture yet. Allow camera access for Hocus, or close other apps using the camera. Hocus retries every few seconds.",
      action:
        running && !status.camera.ok && checks?.camera_settings_url
          ? { label: "Open camera settings", run: () => openUrl(checks.camera_settings_url as string) }
          : undefined,
    },
    {
      id: "obs",
      label: "Meeting apps (optional)",
      state: obs ? (obs.state === "ok" ? "ok" : "warn") : "pending",
      detail: obs?.detail ?? "Checking",
      optional: true,
      action: obs && obs.state !== "ok" ? { label: "Set up", run: onSetUpMeetings } : undefined,
    },
  ];

  const required = rows.filter((row) => !row.optional);
  const ready = required.every((row) => row.state === "ok");
  const blocked = required.some((row) => row.state === "fail" && row.id !== "camera");
  const everything = rows.every((row) => row.state === "ok");

  const continued = useRef(false);
  useEffect(() => {
    if (!everything || continued.current) return;
    const timer = setTimeout(() => {
      continued.current = true;
      onContinue();
    }, AUTO_CONTINUE_MS);
    return () => clearTimeout(timer);
  }, [everything, onContinue]);

  return (
    <div className="flex h-full items-center justify-center p-6">
      <div className="animate-rise w-full max-w-[560px]">
        <div className="mb-8 flex items-center gap-3">
          <img src="/favicon.png" alt="" className="size-11" />
          <div>
            <h1 className="font-display text-[24px] font-semibold tracking-tight">Getting Hocus ready</h1>
            <p className="text-[13.5px] text-muted">Checking your system, camera and meeting setup.</p>
          </div>
        </div>

        <ol className="overflow-hidden rounded-panel border border-line bg-surface">
          {rows.map((row) => (
            <li key={row.id} className="flex items-start gap-3.5 border-b border-line p-4 last:border-b-0">
              <StateIcon state={row.state} />
              <div className="min-w-0 flex-1">
                <div className="text-[14px] font-medium">{row.label}</div>
                <div className="mt-0.5 text-[12.5px] leading-relaxed whitespace-pre-line text-muted select-text">
                  {row.detail}
                </div>
              </div>
              {row.action && (
                <Button variant={row.optional ? "secondary" : "primary"} onClick={row.action.run} className="shrink-0">
                  {row.action.label === "Restart" && <RotateCcw className="size-4" strokeWidth={1.75} />}
                  {row.action.label}
                </Button>
              )}
            </li>
          ))}
        </ol>

        <div className="mt-6 flex items-center justify-between gap-3">
          <p className="text-[12.5px] text-faint">
            {everything
              ? "All set."
              : ready
                ? "Ready. You can set up meeting apps now or later from Output."
                : blocked
                  ? "Hocus cannot start until the issue above is fixed."
                  : "This takes a few seconds."}
          </p>
          <Button variant="primary" disabled={blocked || !running} onClick={onContinue}>
            {ready ? "Continue" : "Continue anyway"}
          </Button>
        </div>
      </div>
    </div>
  );
}

function StateIcon({ state }: { state: RowState }) {
  const shared = "size-[22px] shrink-0 mt-px";
  if (state === "pending") return <LoaderCircle className={cx(shared, "animate-spin text-muted")} strokeWidth={1.75} />;
  if (state === "ok")
    return (
      <span className={cx(shared, "flex items-center justify-center rounded-full bg-ok/15 text-ok")}>
        <Check className="size-3.5" strokeWidth={2.25} />
      </span>
    );
  if (state === "warn") return <TriangleAlert className={cx(shared, "text-accent")} strokeWidth={1.75} />;
  return <CircleAlert className={cx(shared, "text-danger")} strokeWidth={1.75} />;
}
