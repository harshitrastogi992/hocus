import { Camera, CircleAlert, LoaderCircle, RotateCcw, ScanLine } from "lucide-react";
import { forwardRef, useImperativeHandle, useRef } from "react";
import type { Connection } from "../lib/useEngine";
import type { Catalog, Settings, Status } from "../lib/protocol";
import { Button, cx } from "./ui";

export interface PreviewHandle {
  draw: (frame: Blob) => void;
}

const PHASE_LABEL: Record<Status["phase"], string> = {
  present: "On stage",
  leaving: "Vanishing",
  hidden: "Hidden",
  returning: "Returning",
};

interface Props {
  connection: Connection;
  engineError: string | null;
  status: Status;
  settings: Settings | null;
  catalog: Catalog | null;
  onRestart: () => void;
  onCapture: () => void;
  onUseBackdrop: () => void;
}

export const Preview = forwardRef<PreviewHandle, Props>(function Preview(
  { connection, engineError, status, settings, catalog, onRestart, onCapture, onUseBackdrop },
  ref,
) {
  const canvas = useRef<HTMLCanvasElement>(null);
  const decoding = useRef(false);
  const hasFrame = useRef(false);

  useImperativeHandle(ref, () => ({
    draw(frame: Blob) {
      // Skip frames while the previous one decodes, so the preview never lags behind.
      if (decoding.current || !canvas.current) return;
      decoding.current = true;
      createImageBitmap(frame)
        .then((bitmap) => {
          const target = canvas.current;
          if (!target) return;
          if (target.width !== bitmap.width || target.height !== bitmap.height) {
            target.width = bitmap.width;
            target.height = bitmap.height;
          }
          target.getContext("2d")?.drawImage(bitmap, 0, 0);
          bitmap.close();
          if (!hasFrame.current) {
            hasFrame.current = true;
            target.dataset.live = "true";
          }
        })
        .catch(() => undefined)
        .finally(() => {
          decoding.current = false;
        });
    },
  }));

  const gesture = status.hold && catalog?.gestures.find((g) => g.id === status.hold?.gesture);
  const activeEffect = catalog?.effects.find((e) => e.id === status.effect);
  const mode = activeEffect?.kind === "toggle" ? activeEffect : null;
  const phaseLabel = mode
    ? { present: "On stage", leaving: mode.active_label, hidden: mode.active_label, returning: "On stage" }[status.phase]
    : PHASE_LABEL[status.phase];
  const live = connection === "connected" && status.camera.ok;
  const roomMode = settings?.background.mode === "room";

  return (
    <div className="relative aspect-video w-full overflow-hidden rounded-panel border border-line bg-surface">
      <canvas
        ref={canvas}
        className={cx("absolute inset-0 size-full object-contain transition-opacity", live ? "opacity-100" : "opacity-0")}
      />

      {connection === "connected" && (
        <div className="absolute top-3 left-3 flex items-center gap-2">
          <span className="flex h-7 items-center gap-2 rounded-full bg-ink/80 px-3 text-[12px] font-medium">
            <span
              className={cx(
                "size-2 rounded-full",
                status.phase === "present" ? "bg-ok" : "bg-accent",
                status.phase !== "present" && status.phase !== "hidden" && "animate-pulse",
              )}
            />
            {phaseLabel}
          </span>
          {status.virtual_camera.active && (
            <span className="flex h-7 items-center gap-1.5 rounded-full bg-ink/80 px-3 text-[12px] font-medium text-text">
              <span className="size-2 rounded-full bg-danger" />
              Sending to meetings
            </span>
          )}
        </div>
      )}

      {live && (
        <span className="absolute top-3 right-3 rounded-full bg-ink/70 px-2.5 py-1 font-mono text-[11px] text-muted tabular-nums">
          {status.fps} fps
        </span>
      )}

      {status.hold && gesture && <HoldRing label={gesture.label} progress={status.hold.progress} />}

      {status.plate === "capturing" && (
        <Overlay>
          <div className="font-display text-7xl font-semibold tabular-nums text-text">
            {status.plate_countdown && status.plate_countdown > 0 ? Math.ceil(status.plate_countdown) : ""}
          </div>
          <div className="mt-3 text-[15px] text-muted">
            {status.plate_countdown && status.plate_countdown > 0
              ? "Step out of the frame"
              : "Capturing the empty room. Stay out of view."}
          </div>
        </Overlay>
      )}

      {connection === "starting" && (
        <Overlay>
          <LoaderCircle className="size-7 animate-spin text-accent" strokeWidth={1.75} />
          <div className="mt-4 text-[15px] font-medium">Starting the engine</div>
          <div className="mt-1 max-w-sm text-center text-[13px] text-muted">
            The first start downloads about 12 MB of vision models.
          </div>
        </Overlay>
      )}

      {connection === "failed" && (
        <Overlay>
          <CircleAlert className="size-7 text-danger" strokeWidth={1.75} />
          <div className="mt-4 text-[15px] font-medium">The engine is not running</div>
          <pre className="mt-2 max-h-40 max-w-xl overflow-auto rounded-card bg-ink p-3 text-left text-[12px] whitespace-pre-wrap text-muted select-text">
            {engineError}
          </pre>
          <Button variant="primary" className="mt-4" onClick={onRestart}>
            <RotateCcw className="size-4" strokeWidth={1.75} />
            Restart engine
          </Button>
        </Overlay>
      )}

      {connection === "connected" && !status.camera.ok && (
        <Overlay>
          <Camera className="size-7 text-muted" strokeWidth={1.75} />
          <div className="mt-4 text-[15px] font-medium">No camera picture</div>
          <div className="mt-1 max-w-md text-center text-[13px] text-muted">
            {status.camera.error ?? "Waiting for the camera."} Choose another camera under Output if needed.
          </div>
        </Overlay>
      )}

      {live && roomMode && status.plate === "missing" && (
        <div className="animate-rise absolute inset-x-3 bottom-3 flex items-center gap-4 rounded-card border border-line bg-ink/90 p-3 pl-4">
          <ScanLine className="size-5 shrink-0 text-accent" strokeWidth={1.75} />
          <div className="min-w-0 flex-1 text-[13px] leading-snug">
            <div className="font-medium">Capture your empty room to start vanishing</div>
            <div className="text-muted">Hocus needs one shot of the room without you in it. Or pick a backdrop instead.</div>
          </div>
          <Button variant="ghost" onClick={onUseBackdrop}>
            Use a backdrop
          </Button>
          <Button variant="primary" onClick={onCapture}>
            Capture room
          </Button>
        </div>
      )}
    </div>
  );
});

function Overlay({ children }: { children: React.ReactNode }) {
  return (
    <div className="animate-rise absolute inset-0 flex flex-col items-center justify-center bg-surface/85 p-6">
      {children}
    </div>
  );
}

function HoldRing({ label, progress }: { label: string; progress: number }) {
  const radius = 20;
  const circumference = 2 * Math.PI * radius;
  return (
    <div className="absolute bottom-4 left-1/2 flex -translate-x-1/2 items-center gap-3 rounded-full bg-ink/85 py-1.5 pr-4 pl-1.5">
      <svg width="48" height="48" viewBox="0 0 48 48" className="-rotate-90">
        <circle cx="24" cy="24" r={radius} fill="none" stroke="var(--color-line-strong)" strokeWidth="4" />
        <circle
          cx="24"
          cy="24"
          r={radius}
          fill="none"
          stroke="var(--color-accent)"
          strokeWidth="4"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={circumference * (1 - progress)}
          style={{ transition: "stroke-dashoffset 120ms linear" }}
        />
      </svg>
      <div className="text-[13px]">
        <div className="font-medium">Hold it</div>
        <div className="text-muted">{label}</div>
      </div>
    </div>
  );
}
