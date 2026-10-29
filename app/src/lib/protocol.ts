// Mirrors engine/src/hocus/server.py and docs/protocol.md.

export type Phase = "present" | "leaving" | "hidden" | "returning";
export type BackgroundMode = "room" | "preset" | "image";

export interface EffectSetting {
  enabled: boolean;
  gesture: string;
}

export interface Settings {
  camera_index: number;
  resolution: [number, number];
  fps: number;
  mirror: boolean;
  virtual_camera: boolean;
  background: { mode: BackgroundMode; preset: string; image: string | null };
  effects: Record<string, EffectSetting>;
}

export type EffectKind = "vanish" | "toggle" | "reaction";

export interface EffectInfo {
  id: string;
  name: string;
  description: string;
  default_gesture: string;
  kind: EffectKind;
  active_label: string;
}

export interface GestureInfo {
  id: string;
  label: string;
  hint: string;
  hold_seconds: number;
}

export interface Catalog {
  effects: EffectInfo[];
  gestures: GestureInfo[];
  presets: { id: string; label: string; thumbnail: string }[];
  resolutions: [number, number][];
}

export type Stage = "loading_models" | "opening_camera" | "running" | "failed";

export interface CheckItem {
  id: string;
  label: string;
  state: "ok" | "warn" | "fail";
  detail: string;
  required: boolean;
  action_label: string | null;
  action_url: string | null;
}

export interface Checks {
  items: CheckItem[];
  camera_settings_url: string | null;
  can_install_obs: boolean;
  platform: string;
}

export interface InstallState {
  state: "running" | "done" | "failed";
  message?: string;
}

export interface Status {
  stage: Stage;
  phase: Phase;
  effect: string | null;
  reactions: string[];
  hold: { gesture: string; progress: number } | null;
  background_ready: boolean;
  plate: "missing" | "capturing" | "ready";
  plate_countdown: number | null;
  camera: { ok: boolean; error: string | null };
  virtual_camera: { active: boolean; device: string | null; error: string | null };
  fps: number;
}

export type ServerMessage =
  | { type: "state"; settings: Settings; catalog: Catalog; status: Partial<Status> }
  | ({ type: "status" } & Status)
  | { type: "effect"; effect: string; direction: "out" | "in" }
  | { type: "notice"; level: "info" | "error"; message: string }
  | ({ type: "checks" } & Checks)
  | ({ type: "install" } & InstallState);

export type DeepPartial<T> = { [K in keyof T]?: T[K] extends object ? DeepPartial<T[K]> : T[K] };

export type ClientMessage =
  | { type: "update_settings"; patch: DeepPartial<Settings> }
  | { type: "capture_plate" }
  | { type: "toggle"; effect?: string | null }
  | { type: "get_state" }
  | { type: "run_checks" }
  | { type: "install_obs" }
  | { type: "open_obs" };

/** Effect ids of enabled effects, keyed by gesture. Used to block clashing choices. */
export function gestureOwners(settings: Settings): Record<string, string> {
  const owners: Record<string, string> = {};
  for (const [id, effect] of Object.entries(settings.effects)) {
    if (effect.enabled) owners[effect.gesture] = id;
  }
  return owners;
}
