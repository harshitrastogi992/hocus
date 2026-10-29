import { openUrl } from "@tauri-apps/plugin-opener";
import { Check, Download, ExternalLink, LoaderCircle, RefreshCw, X } from "lucide-react";
import { useEffect, useState } from "react";
import type { Engine } from "../lib/useEngine";
import { Button, Segmented, Switch, cx } from "./ui";

type MeetingApp = "teams" | "zoom" | "meet";

const OBS_DOWNLOAD = "https://obsproject.com/download";

const GUIDES: Record<MeetingApp, string[]> = {
  teams: [
    "Open Teams, then Settings and more (…) > Settings > Devices.",
    "Under Camera, choose OBS Virtual Camera.",
    "In a meeting, open Video effects and set Background to None, so Teams does not paint over Hocus.",
  ],
  zoom: [
    "Open Zoom, then Settings > Video.",
    "Under Camera, choose OBS Virtual Camera.",
    "Under Background & effects, choose None.",
  ],
  meet: [
    "In a Google Meet call, open More options (⋮) > Settings > Video.",
    "Under Camera, choose OBS Virtual Camera.",
    "Turn off Visual effects (backgrounds and blur).",
  ],
};

export function MeetingSetup({ engine, onClose }: { engine: Engine; onClose: () => void }) {
  const { checks, install, settings, status, send } = engine;
  const [app, setApp] = useState<MeetingApp>("teams");
  const obs = checks?.items.find((item) => item.id === "obs");
  const driverReady = obs?.state === "ok";
  const installed = driverReady || (obs?.state === "warn" && obs.action_url === null);
  const installing = install?.state === "running";
  const mac = checks?.platform === "Darwin";

  useEffect(() => {
    send({ type: "run_checks" });
    const onKey = (event: KeyboardEvent) => event.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [send, onClose]);

  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-ink/70 p-6" onMouseDown={onClose}>
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="meeting-setup-title"
        className="animate-rise max-h-full w-full max-w-[600px] overflow-y-auto rounded-panel border border-line-strong bg-surface shadow-2xl shadow-black/50"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-4 border-b border-line p-5">
          <div>
            <h2 id="meeting-setup-title" className="font-display text-[19px] font-semibold">
              Use Hocus in meetings
            </h2>
            <p className="mt-1 text-[13px] text-muted">
              Teams, Zoom and Meet see Hocus through the free OBS Virtual Camera driver.
            </p>
          </div>
          <button type="button" aria-label="Close" onClick={onClose} className="text-faint hover:text-text">
            <X className="size-5" strokeWidth={1.75} />
          </button>
        </div>

        <ol className="flex flex-col">
          <Step number={1} title="Install OBS Studio" done={installed}>
            {installed ? (
              <p>OBS Studio is installed.</p>
            ) : installing ? (
              <p className="flex items-center gap-2">
                <LoaderCircle className="size-4 animate-spin text-accent" strokeWidth={1.75} />
                Installing OBS Studio. This can take a few minutes.
              </p>
            ) : (
              <>
                <p>
                  {checks?.can_install_obs
                    ? `Hocus can install it for you with ${mac ? "Homebrew" : "winget"}, or you can download it yourself.`
                    : "Download and install OBS Studio 30 or later."}
                </p>
                <div className="mt-3 flex gap-2">
                  {checks?.can_install_obs && (
                    <Button variant="primary" onClick={() => send({ type: "install_obs" })}>
                      <Download className="size-4" strokeWidth={1.75} />
                      Install OBS
                    </Button>
                  )}
                  <Button onClick={() => openUrl(OBS_DOWNLOAD)}>
                    <ExternalLink className="size-4" strokeWidth={1.75} />
                    Download page
                  </Button>
                </div>
              </>
            )}
          </Step>

          <Step number={2} title="Switch on the virtual camera driver" done={driverReady} disabled={!installed}>
            {driverReady ? (
              <p>The OBS Virtual Camera driver is active.</p>
            ) : (
              <>
                <p>
                  Open OBS, click <b className="text-text">Start Virtual Camera</b>, then{" "}
                  <b className="text-text">Stop Virtual Camera</b> and quit OBS.
                  {mac &&
                    " If macOS asks, allow the OBS system extension in System Settings > General > Login Items & Extensions."}
                </p>
                <div className="mt-3 flex gap-2">
                  <Button variant="primary" disabled={!installed} onClick={() => send({ type: "open_obs" })}>
                    Open OBS
                  </Button>
                  <Button onClick={() => send({ type: "run_checks" })}>
                    <RefreshCw className="size-4" strokeWidth={1.75} />
                    Check again
                  </Button>
                </div>
              </>
            )}
          </Step>

          <Step
            number={3}
            title="Send Hocus to meeting apps"
            done={Boolean(settings?.virtual_camera && status.virtual_camera.active)}
            disabled={!driverReady}
          >
            <div className="flex items-center justify-between gap-4 rounded-card border border-line bg-raised/60 p-3">
              <span>
                {status.virtual_camera.active
                  ? "Hocus video is live on OBS Virtual Camera."
                  : "Quit OBS first: only one app can drive the virtual camera."}
              </span>
              <Switch
                label="Send to meeting apps"
                checked={Boolean(settings?.virtual_camera)}
                disabled={!driverReady}
                onChange={(virtual_camera) => send({ type: "update_settings", patch: { virtual_camera } })}
              />
            </div>
          </Step>

          <Step number={4} title="Pick the camera in your meeting app" disabled={!driverReady}>
            <Segmented<MeetingApp>
              value={app}
              onChange={setApp}
              options={[
                { value: "teams", label: "Microsoft Teams" },
                { value: "zoom", label: "Zoom" },
                { value: "meet", label: "Google Meet" },
              ]}
            />
            <ol className="mt-3 flex list-decimal flex-col gap-1.5 pl-5">
              {GUIDES[app].map((line) => (
                <li key={line}>{line}</li>
              ))}
            </ol>
            <p className="mt-3 text-faint">
              If OBS Virtual Camera is missing from the list, quit and reopen the meeting app. Apps read the camera
              list when they start.
            </p>
          </Step>
        </ol>
      </div>
    </div>
  );
}

function Step({
  number,
  title,
  done,
  disabled,
  children,
}: {
  number: number;
  title: string;
  done?: boolean;
  disabled?: boolean;
  children: React.ReactNode;
}) {
  return (
    <li className={cx("flex gap-4 border-b border-line p-5 last:border-b-0", disabled && "opacity-45")}>
      <span
        className={cx(
          "flex size-7 shrink-0 items-center justify-center rounded-full font-mono text-[12.5px] font-semibold",
          done ? "bg-ok/15 text-ok" : "bg-raised text-muted",
        )}
      >
        {done ? <Check className="size-4" strokeWidth={2.25} /> : number}
      </span>
      <div className="min-w-0 flex-1 text-[13px] leading-relaxed text-muted">
        <h3 className="mb-1.5 text-[14px] font-medium text-text">{title}</h3>
        {children}
      </div>
    </li>
  );
}
