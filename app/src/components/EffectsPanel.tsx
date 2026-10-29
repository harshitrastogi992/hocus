import {
  CloudFog,
  CloudRain,
  Flashlight,
  Ghost,
  Hand,
  Heart,
  PartyPopper,
  Play,
  Sparkles,
  Users,
  Zap,
  type LucideIcon,
} from "lucide-react";
import {
  gestureOwners,
  type Catalog,
  type ClientMessage,
  type EffectInfo,
  type EffectKind,
  type Settings,
  type Status,
} from "../lib/protocol";
import { Button, Select, Switch, cx } from "./ui";

const ICONS: Record<string, LucideIcon> = {
  stardust: Sparkles,
  switcheroo: CloudFog,
  blink: Zap,
  cloak: Ghost,
  clones: Users,
  spotlight: Flashlight,
  confetti: PartyPopper,
  hearts: Heart,
  raincloud: CloudRain,
};

const GROUPS: { kind: EffectKind; title: string; detail: string }[] = [
  { kind: "vanish", title: "Vanish", detail: "Make the gesture to disappear. Make it again to come back." },
  { kind: "toggle", title: "Modes", detail: "Make the gesture to switch a mode on. Make it again to switch it off." },
  {
    kind: "reaction",
    title: "Reactions",
    detail: "Play once, any time. Reactions work before you capture a room.",
  },
];

interface Props {
  settings: Settings;
  catalog: Catalog;
  status: Status;
  send: (message: ClientMessage) => void;
}

export function EffectsPanel({ settings, catalog, status, send }: Props) {
  const enabledCount = Object.values(settings.effects).filter((e) => e.enabled).length;

  return (
    <div className="flex flex-col gap-7">
      <p className="text-[13px] leading-relaxed text-muted">
        Everything switched on runs together. Each effect needs its own gesture.
      </p>
      {GROUPS.map((group) => (
        <section key={group.kind} className="flex flex-col gap-3">
          <div>
            <h2 className="text-[11.5px] font-semibold tracking-[0.08em] text-faint uppercase">{group.title}</h2>
            <p className="mt-1 text-[12.5px] text-muted">{group.detail}</p>
          </div>
          {catalog.effects
            .filter((effect) => effect.kind === group.kind)
            .map((effect) => (
              <EffectCard key={effect.id} effect={effect} settings={settings} catalog={catalog} status={status} send={send} />
            ))}
        </section>
      ))}
      {enabledCount === 0 && (
        <p className="rounded-card border border-dashed border-line p-4 text-center text-[13px] text-muted">
          Switch on at least one effect to use gestures.
        </p>
      )}
    </div>
  );
}

function EffectCard({ effect, settings, catalog, status, send }: Props & { effect: EffectInfo }) {
  const owners = gestureOwners(settings);
  const effectName = (id: string) => catalog.effects.find((e) => e.id === id)?.name ?? id;
  const gestureLabel = (id: string) => catalog.gestures.find((g) => g.id === id)?.label ?? id;
  const current = settings.effects[effect.id];
  const Icon = ICONS[effect.id] ?? Sparkles;
  const owner = owners[current.gesture];
  const blocked = !current.enabled && owner !== undefined && owner !== effect.id;
  const gesture = catalog.gestures.find((g) => g.id === current.gesture);
  const reaction = effect.kind === "reaction";
  const active = reaction ? status.reactions.includes(effect.id) : status.effect === effect.id;
  const canTry = reaction
    ? status.camera.ok && !active
    : status.background_ready && status.phase === "present";
  const update = (patch: Partial<Settings["effects"][string]>) =>
    send({ type: "update_settings", patch: { effects: { [effect.id]: patch } } });

  return (
    <section
      className={cx(
        "rounded-card border bg-raised/60 p-4 transition-colors",
        active ? "border-accent" : "border-line",
      )}
    >
      <div className="flex items-start gap-3">
        <div
          className={cx(
            "flex size-10 shrink-0 items-center justify-center rounded-card",
            current.enabled ? "bg-accent/15 text-accent" : "bg-hover text-faint",
          )}
        >
          <Icon className="size-5" strokeWidth={1.75} />
        </div>
        <div className="min-w-0 flex-1">
          <h3 className="font-display text-[15px] font-semibold">{effect.name}</h3>
          <p className="mt-0.5 text-[12.5px] leading-relaxed text-muted">{effect.description}</p>
        </div>
        <Switch
          label={`Use ${effect.name}`}
          checked={current.enabled}
          disabled={blocked}
          onChange={(enabled) => update({ enabled })}
        />
      </div>

      <div className="mt-4 flex items-center gap-2">
        <Hand className="size-4 shrink-0 text-faint" strokeWidth={1.75} />
        <div className="flex-1">
          <Select
            label={`Gesture for ${effect.name}`}
            value={current.gesture}
            onChange={(gesture) => update({ gesture })}
            options={catalog.gestures.map((g) => {
              const takenBy = owners[g.id];
              const taken = current.enabled && takenBy !== undefined && takenBy !== effect.id;
              return {
                value: g.id,
                label: taken ? `${g.label} (used by ${effectName(takenBy)})` : g.label,
                disabled: taken,
              };
            })}
          />
        </div>
        <Button
          variant="ghost"
          aria-label={`Try ${effect.name}`}
          title={canTry ? `Try ${effect.name}` : reaction ? "Available when the camera is on" : "Available when you are on stage"}
          disabled={!current.enabled || !canTry}
          onClick={() => send({ type: "toggle", effect: effect.id })}
          className="px-2.5"
        >
          <Play className="size-4" strokeWidth={1.75} />
          Try
        </Button>
      </div>

      <div className="mt-2 text-[12px] text-faint">
        {blocked
          ? `${gestureLabel(current.gesture)} is used by ${effectName(owner)}. Pick another gesture to switch this on.`
          : gesture && `${gesture.hint}${gesture.hold_seconds >= 0.5 ? `, held for ${gesture.hold_seconds} s` : ""}.`}
      </div>
    </section>
  );
}
