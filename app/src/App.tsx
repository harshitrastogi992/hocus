import { ArrowRight, CircleAlert, CircleCheck, FlipHorizontal2, Image, SlidersHorizontal, Sparkles, WandSparkles, X } from "lucide-react";
import { useCallback, useRef, useState } from "react";
import { BackgroundPanel } from "./components/BackgroundPanel";
import { EffectsPanel } from "./components/EffectsPanel";
import { MeetingSetup } from "./components/MeetingSetup";
import { OutputPanel } from "./components/OutputPanel";
import { Preview, type PreviewHandle } from "./components/Preview";
import { StartupScreen } from "./components/StartupScreen";
import { Button, cx } from "./components/ui";
import { useEngine, type Engine } from "./lib/useEngine";

type Tab = "effects" | "background" | "output";

const TABS: { id: Tab; label: string; icon: typeof Sparkles }[] = [
  { id: "effects", label: "Effects", icon: Sparkles },
  { id: "background", label: "Background", icon: Image },
  { id: "output", label: "Output", icon: SlidersHorizontal },
];

export default function App() {
  const preview = useRef<PreviewHandle>(null);
  const onFrame = useCallback((frame: Blob) => preview.current?.draw(frame), []);
  const engine = useEngine(onFrame);
  const [tab, setTab] = useState<Tab>("effects");
  const [started, setStarted] = useState(false);
  const [meetingSetup, setMeetingSetup] = useState(false);
  const { settings, catalog, status, send } = engine;
  const openMeetingSetup = useCallback(() => setMeetingSetup(true), []);
  const closeMeetingSetup = useCallback(() => setMeetingSetup(false), []);
  const start = useCallback(() => setStarted(true), []);

  const setup = meetingSetup && <MeetingSetup engine={engine} onClose={closeMeetingSetup} />;

  if (!started) {
    return (
      <>
        <StartupScreen engine={engine} onContinue={start} onSetUpMeetings={openMeetingSetup} />
        {setup}
        <Toasts engine={engine} />
      </>
    );
  }

  return (
    <div className="flex h-full flex-col">
      <header className="flex h-14 shrink-0 items-center justify-between border-b border-line px-5">
        <div className="flex items-center gap-2.5">
          <img src="/favicon.png" alt="" className="size-8" />
          <span className="font-display text-[18px] font-semibold tracking-tight">Hocus</span>
        </div>
        <EngineBadge engine={engine} />
      </header>

      <div className="flex min-h-0 flex-1">
        <main className="flex min-w-0 flex-1 flex-col gap-4 overflow-y-auto p-5">
          <Preview
            ref={preview}
            connection={engine.connection}
            engineError={engine.engineError}
            status={status}
            settings={settings}
            catalog={catalog}
            onRestart={engine.restart}
            onCapture={() => send({ type: "capture_plate" })}
            onUseBackdrop={() => {
              send({ type: "update_settings", patch: { background: { mode: "preset" } } });
              setTab("background");
            }}
          />
          {settings && catalog && <StageBar engine={engine} />}
        </main>

        <aside className="flex w-[380px] shrink-0 flex-col border-l border-line bg-surface">
          <nav className="flex gap-1 border-b border-line p-2" aria-label="Sections">
            {TABS.map(({ id, label, icon: Icon }) => (
              <button
                key={id}
                type="button"
                onClick={() => setTab(id)}
                aria-current={tab === id ? "page" : undefined}
                className={cx(
                  "flex h-9 flex-1 items-center justify-center gap-2 rounded-control text-[13px] font-medium transition-colors",
                  tab === id ? "bg-raised text-text" : "text-muted hover:text-text",
                )}
              >
                <Icon className="size-4" strokeWidth={1.75} />
                {label}
              </button>
            ))}
          </nav>
          <div className="min-h-0 flex-1 overflow-y-auto p-5">
            {settings && catalog ? (
              <>
                {tab === "effects" && <EffectsPanel settings={settings} catalog={catalog} status={status} send={send} />}
                {tab === "background" && (
                  <BackgroundPanel settings={settings} catalog={catalog} status={status} send={send} />
                )}
                {tab === "output" && (
                  <OutputPanel
                    settings={settings}
                    catalog={catalog}
                    status={status}
                    send={send}
                    onSetUpMeetings={openMeetingSetup}
                  />
                )}
              </>
            ) : (
              <div className="flex flex-col gap-3">
                {[0, 1, 2].map((i) => (
                  <div key={i} className="h-36 animate-pulse rounded-card bg-raised/60" />
                ))}
              </div>
            )}
          </div>
        </aside>
      </div>

      {setup}
      <Toasts engine={engine} />
    </div>
  );
}

function EngineBadge({ engine }: { engine: Engine }) {
  const label = { starting: "Starting", connected: "Engine ready", failed: "Engine stopped" }[engine.connection];
  const colour = { starting: "bg-accent", connected: "bg-ok", failed: "bg-danger" }[engine.connection];
  return (
    <div className="flex items-center gap-2 text-[12.5px] text-muted">
      <span className={cx("size-2 rounded-full", colour, engine.connection === "starting" && "animate-pulse")} />
      {label}
    </div>
  );
}

function StageBar({ engine }: { engine: Engine }) {
  const { settings, catalog, status, send } = engine;
  if (!settings || !catalog) return null;
  const enabled = catalog.effects.filter((effect) => settings.effects[effect.id].enabled);
  const staged = enabled.filter((effect) => effect.kind !== "reaction");
  const gestureLabel = (id: string) => catalog.gestures.find((g) => g.id === id)?.label ?? id;
  const hidden = status.phase === "hidden";
  const mode = catalog.effects.find((effect) => effect.id === status.effect && effect.kind === "toggle");
  const busy = status.phase === "leaving" || status.phase === "returning";

  return (
    <div className="flex items-center gap-3 rounded-panel border border-line bg-surface p-3 pl-4">
      <div className="flex min-w-0 flex-1 flex-wrap items-center gap-2">
        {enabled.length === 0 && <span className="text-[13px] text-muted">No effects switched on.</span>}
        {enabled.map((effect) => (
          <span
            key={effect.id}
            className={cx(
              "flex h-7 items-center gap-1.5 rounded-full border px-3 text-[12.5px]",
              status.effect === effect.id || status.reactions.includes(effect.id)
                ? "border-accent text-text"
                : "border-line text-muted",
            )}
          >
            <span className="text-text">{gestureLabel(settings.effects[effect.id].gesture)}</span>
            <ArrowRight className="size-3.5 text-faint" strokeWidth={1.75} />
            {effect.name}
          </span>
        ))}
      </div>
      <Button
        variant="ghost"
        aria-label="Mirror preview"
        title="Mirror preview"
        onClick={() => send({ type: "update_settings", patch: { mirror: !settings.mirror } })}
        className={cx("px-2.5", settings.mirror && "text-text")}
      >
        <FlipHorizontal2 className="size-4" strokeWidth={1.75} />
      </Button>
      <Button
        variant="primary"
        disabled={busy || (!hidden && (!status.background_ready || staged.length === 0))}
        onClick={() => send({ type: "toggle", effect: null })}
        className="min-w-28"
      >
        <WandSparkles className="size-4" strokeWidth={1.75} />
        {hidden ? (mode ? `Stop ${mode.name}` : "Reappear") : "Vanish"}
      </Button>
    </div>
  );
}

function Toasts({ engine }: { engine: Engine }) {
  return (
    <div className="pointer-events-none fixed right-5 bottom-5 z-50 flex w-[360px] flex-col gap-2">
      {engine.notices.map((notice) => {
        const Icon = notice.level === "error" ? CircleAlert : CircleCheck;
        return (
          <div
            key={notice.id}
            role={notice.level === "error" ? "alert" : "status"}
            className="animate-rise pointer-events-auto flex items-start gap-3 rounded-card border border-line-strong bg-raised p-3 shadow-lg shadow-black/40"
          >
            <Icon
              className={cx("mt-0.5 size-4 shrink-0", notice.level === "error" ? "text-danger" : "text-ok")}
              strokeWidth={1.75}
            />
            <p className="flex-1 text-[13px] leading-relaxed select-text">{notice.message}</p>
            <button
              type="button"
              aria-label="Dismiss"
              onClick={() => engine.dismiss(notice.id)}
              className="text-faint hover:text-text"
            >
              <X className="size-4" strokeWidth={1.75} />
            </button>
          </div>
        );
      })}
    </div>
  );
}
