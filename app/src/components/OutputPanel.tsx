import { useState } from "react";
import type { Catalog, ClientMessage, Settings, Status } from "../lib/protocol";
import { loadSoundPrefs, playEffectSound, saveSoundPrefs, type SoundPrefs } from "../lib/sounds";
import { Button, Field, Row, Select, Switch } from "./ui";

interface Props {
  settings: Settings;
  catalog: Catalog;
  status: Status;
  send: (message: ClientMessage) => void;
  onSetUpMeetings: () => void;
}

export function OutputPanel({ settings, catalog, status, send, onSetUpMeetings }: Props) {
  const [sound, setSound] = useState<SoundPrefs>(loadSoundPrefs);
  const update = (patch: Partial<Settings>) => send({ type: "update_settings", patch });
  const changeSound = (next: SoundPrefs) => {
    setSound(next);
    saveSoundPrefs(next);
  };
  const virtual = status.virtual_camera;

  return (
    <div className="flex flex-col gap-7">
      <Field label="Meetings">
        <Row
          title="Send to meeting apps"
          detail={
            virtual.active
              ? `Live on ${virtual.device ?? "the virtual camera"}. In Teams, Zoom or Meet, pick "OBS Virtual Camera" as your camera and turn off their own background effects.`
              : "Uses the OBS Virtual Camera driver. Install OBS Studio, start its virtual camera once, then quit OBS."
          }
        >
          <Switch
            label="Send to meeting apps"
            checked={settings.virtual_camera}
            onChange={(virtual_camera) => update({ virtual_camera })}
          />
        </Row>
        <Button onClick={onSetUpMeetings} className="self-start">
          Set up meeting apps
        </Button>
        {virtual.error && (
          <div className="rounded-card border border-danger/40 bg-danger/10 p-3 text-[12.5px] leading-relaxed text-text select-text">
            {virtual.error}
          </div>
        )}
      </Field>

      <Field label="Camera">
        <Select
          label="Camera"
          value={String(settings.camera_index)}
          onChange={(value) => update({ camera_index: Number(value) })}
          options={[0, 1, 2, 3].map((index) => ({
            value: String(index),
            label: index === 0 ? "Camera 1 (default)" : `Camera ${index + 1}`,
          }))}
        />
        <div className="grid grid-cols-2 gap-2">
          <Select
            label="Resolution"
            value={settings.resolution.join("x")}
            onChange={(value) => update({ resolution: value.split("x").map(Number) as [number, number] })}
            options={catalog.resolutions.map(([w, h]) => ({ value: `${w}x${h}`, label: `${h}p` }))}
          />
          <Select
            label="Frame rate"
            value={String(settings.fps)}
            onChange={(value) => update({ fps: Number(value) })}
            options={[15, 24, 30].map((fps) => ({ value: String(fps), label: `${fps} fps` }))}
          />
        </div>
        <Row title="Mirror preview" detail="Flip the picture so it behaves like a mirror. Gestures still read correctly.">
          <Switch label="Mirror" checked={settings.mirror} onChange={(mirror) => update({ mirror })} />
        </Row>
      </Field>

      <Field label="Sound" hint="Sounds play on this computer only. Meeting guests do not hear them.">
        <Row title="Effect sounds">
          <Switch
            label="Effect sounds"
            checked={sound.enabled}
            onChange={(enabled) => changeSound({ ...sound, enabled })}
          />
        </Row>
        <input
          type="range"
          aria-label="Volume"
          min={0}
          max={1}
          step={0.05}
          value={sound.volume}
          disabled={!sound.enabled}
          onChange={(event) => changeSound({ ...sound, volume: Number(event.target.value) })}
          onPointerUp={() => playEffectSound("switcheroo", "in")}
          className="w-full accent-[var(--color-accent)] disabled:opacity-40"
        />
      </Field>
    </div>
  );
}
