// Effect sounds are synthesised with Web Audio, so the app ships no audio files.
// They play on this computer only; meeting apps hear your microphone as usual.

const STORAGE_KEY = "hocus.sound";

export interface SoundPrefs {
  enabled: boolean;
  volume: number;
}

export function loadSoundPrefs(): SoundPrefs {
  try {
    const stored = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? "null");
    if (stored && typeof stored.enabled === "boolean" && typeof stored.volume === "number") {
      return stored;
    }
  } catch {
    // Storage can be unavailable; fall back to defaults.
  }
  return { enabled: true, volume: 0.6 };
}

export function saveSoundPrefs(prefs: SoundPrefs) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(prefs));
  } catch {
    // Not critical.
  }
}

let context: AudioContext | null = null;

function audio(): AudioContext {
  context ??= new AudioContext();
  if (context.state === "suspended") void context.resume();
  return context;
}

function noise(ctx: AudioContext, seconds: number): AudioBufferSourceNode {
  const buffer = ctx.createBuffer(1, Math.ceil(ctx.sampleRate * seconds), ctx.sampleRate);
  const data = buffer.getChannelData(0);
  for (let i = 0; i < data.length; i++) data[i] = Math.random() * 2 - 1;
  const source = ctx.createBufferSource();
  source.buffer = buffer;
  return source;
}

function envelope(ctx: AudioContext, out: AudioNode, peak: number, attack: number, decay: number, at = 0) {
  const gain = ctx.createGain();
  const start = ctx.currentTime + at;
  gain.gain.setValueAtTime(0.0001, start);
  gain.gain.exponentialRampToValueAtTime(peak, start + attack);
  gain.gain.exponentialRampToValueAtTime(0.0001, start + attack + decay);
  gain.connect(out);
  return gain;
}

function sparkle(ctx: AudioContext, out: AudioNode, rising: boolean) {
  const notes = [1318.5, 1568, 1975.5, 2349.3, 2637, 3136];
  const order = rising ? notes : [...notes].reverse();
  order.forEach((frequency, i) => {
    const osc = ctx.createOscillator();
    osc.type = "triangle";
    osc.frequency.value = frequency;
    osc.connect(envelope(ctx, out, 0.18, 0.01, 0.35, i * 0.07));
    osc.start(ctx.currentTime + i * 0.07);
    osc.stop(ctx.currentTime + i * 0.07 + 0.4);
  });
  const hiss = noise(ctx, 1.2);
  const filter = ctx.createBiquadFilter();
  filter.type = "bandpass";
  filter.Q.value = 2;
  filter.frequency.setValueAtTime(rising ? 2000 : 9000, ctx.currentTime);
  filter.frequency.exponentialRampToValueAtTime(rising ? 9000 : 2000, ctx.currentTime + 1.1);
  hiss.connect(filter).connect(envelope(ctx, out, 0.12, 0.2, 0.9));
  hiss.start();
}

function poof(ctx: AudioContext, out: AudioNode) {
  const burst = noise(ctx, 0.8);
  const filter = ctx.createBiquadFilter();
  filter.type = "lowpass";
  filter.frequency.setValueAtTime(4200, ctx.currentTime);
  filter.frequency.exponentialRampToValueAtTime(260, ctx.currentTime + 0.6);
  burst.connect(filter).connect(envelope(ctx, out, 0.7, 0.008, 0.6));
  burst.start();
  const thump = ctx.createOscillator();
  thump.frequency.setValueAtTime(150, ctx.currentTime);
  thump.frequency.exponentialRampToValueAtTime(45, ctx.currentTime + 0.25);
  thump.connect(envelope(ctx, out, 0.6, 0.005, 0.3));
  thump.start();
  thump.stop(ctx.currentTime + 0.35);
}

function squeak(ctx: AudioContext, out: AudioNode) {
  const osc = ctx.createOscillator();
  osc.type = "square";
  osc.frequency.setValueAtTime(900, ctx.currentTime + 0.35);
  osc.frequency.exponentialRampToValueAtTime(1400, ctx.currentTime + 0.42);
  osc.frequency.exponentialRampToValueAtTime(800, ctx.currentTime + 0.55);
  const filter = ctx.createBiquadFilter();
  filter.type = "lowpass";
  filter.frequency.value = 2400;
  osc.connect(filter).connect(envelope(ctx, out, 0.08, 0.02, 0.18, 0.35));
  osc.start(ctx.currentTime + 0.35);
  osc.stop(ctx.currentTime + 0.6);
}

function zap(ctx: AudioContext, out: AudioNode, rising: boolean) {
  const osc = ctx.createOscillator();
  osc.type = "sawtooth";
  const [from, to] = rising ? [180, 2600] : [2600, 180];
  osc.frequency.setValueAtTime(from, ctx.currentTime);
  osc.frequency.exponentialRampToValueAtTime(to, ctx.currentTime + 0.5);
  const filter = ctx.createBiquadFilter();
  filter.type = "lowpass";
  filter.frequency.value = 3200;
  osc.connect(filter).connect(envelope(ctx, out, 0.22, 0.02, 0.6));
  osc.start();
  osc.stop(ctx.currentTime + 0.7);
  const crack = noise(ctx, 0.2);
  const high = ctx.createBiquadFilter();
  high.type = "highpass";
  high.frequency.value = 3000;
  crack.connect(high).connect(envelope(ctx, out, 0.5, 0.004, 0.15, rising ? 0.68 : 0));
  crack.start(ctx.currentTime + (rising ? 0.68 : 0));
}

function popper(ctx: AudioContext, out: AudioNode) {
  for (const at of [0, 0.06]) {
    const bang = noise(ctx, 0.3);
    const band = ctx.createBiquadFilter();
    band.type = "bandpass";
    band.frequency.value = 1800;
    bang.connect(band).connect(envelope(ctx, out, 0.9, 0.003, 0.18, at));
    bang.start(ctx.currentTime + at);
  }
  const crackle = noise(ctx, 1.6);
  const high = ctx.createBiquadFilter();
  high.type = "highpass";
  high.frequency.value = 5000;
  const flutter = ctx.createGain();
  flutter.gain.value = 0;
  const lfo = ctx.createOscillator();
  lfo.type = "square";
  lfo.frequency.value = 23;
  lfo.connect(flutter.gain);
  crackle.connect(high).connect(flutter).connect(envelope(ctx, out, 0.12, 0.1, 1.4, 0.1));
  lfo.start();
  lfo.stop(ctx.currentTime + 1.8);
  crackle.start(ctx.currentTime + 0.1);
}

function chime(ctx: AudioContext, out: AudioNode, notes: number[], gap: number, type: OscillatorType = "sine") {
  notes.forEach((frequency, i) => {
    const osc = ctx.createOscillator();
    osc.type = type;
    osc.frequency.value = frequency;
    osc.connect(envelope(ctx, out, 0.2, 0.01, 0.7, i * gap));
    osc.start(ctx.currentTime + i * gap);
    osc.stop(ctx.currentTime + i * gap + 0.8);
  });
}

function storm(ctx: AudioContext, out: AudioNode) {
  const rain = noise(ctx, 3.8);
  const band = ctx.createBiquadFilter();
  band.type = "bandpass";
  band.frequency.value = 3500;
  band.Q.value = 0.6;
  rain.connect(band).connect(envelope(ctx, out, 0.16, 0.4, 3.2, 0.2));
  rain.start(ctx.currentTime + 0.2);
  const thunder = noise(ctx, 2.0);
  const low = ctx.createBiquadFilter();
  low.type = "lowpass";
  low.frequency.setValueAtTime(900, ctx.currentTime + 1.7);
  low.frequency.exponentialRampToValueAtTime(120, ctx.currentTime + 3.2);
  thunder.connect(low).connect(envelope(ctx, out, 0.9, 0.02, 1.6, 1.7));
  thunder.start(ctx.currentTime + 1.7);
}

function shimmer(ctx: AudioContext, out: AudioNode, rising: boolean) {
  const air = noise(ctx, 1.2);
  const band = ctx.createBiquadFilter();
  band.type = "bandpass";
  band.Q.value = 6;
  const [from, to] = rising ? [600, 7000] : [7000, 600];
  band.frequency.setValueAtTime(from, ctx.currentTime);
  band.frequency.exponentialRampToValueAtTime(to, ctx.currentTime + 0.9);
  air.connect(band).connect(envelope(ctx, out, 0.5, 0.15, 0.85));
  air.start();
  chime(ctx, out, rising ? [2093, 2637, 3136] : [3136, 2637, 2093], 0.12, "triangle");
}

function lamp(ctx: AudioContext, out: AudioNode, on: boolean) {
  const clunk = ctx.createOscillator();
  clunk.frequency.setValueAtTime(on ? 120 : 90, ctx.currentTime);
  clunk.frequency.exponentialRampToValueAtTime(40, ctx.currentTime + 0.12);
  clunk.connect(envelope(ctx, out, 0.7, 0.003, 0.15));
  clunk.start();
  clunk.stop(ctx.currentTime + 0.2);
  if (!on) return;
  const hum = ctx.createOscillator();
  hum.type = "sawtooth";
  hum.frequency.value = 100;
  const low = ctx.createBiquadFilter();
  low.type = "lowpass";
  low.frequency.value = 400;
  hum.connect(low).connect(envelope(ctx, out, 0.05, 0.1, 0.8, 0.05));
  hum.start();
  hum.stop(ctx.currentTime + 1.0);
}

export function playEffectSound(effect: string, direction: "out" | "in") {
  const prefs = loadSoundPrefs();
  if (!prefs.enabled || prefs.volume <= 0) return;
  const ctx = audio();
  const master = ctx.createGain();
  master.gain.value = prefs.volume;
  master.connect(ctx.destination);
  if (effect === "stardust") sparkle(ctx, master, direction === "out");
  else if (effect === "switcheroo") {
    poof(ctx, master);
    if (direction === "out") squeak(ctx, master);
  } else if (effect === "blink") zap(ctx, master, direction === "out");
  else if (effect === "cloak") shimmer(ctx, master, direction === "out");
  else if (effect === "clones") {
    poof(ctx, master);
    setTimeout(() => poof(ctx, master), 90);
  } else if (effect === "spotlight") lamp(ctx, master, direction === "out");
  else if (effect === "confetti") popper(ctx, master);
  else if (effect === "hearts") chime(ctx, master, [784, 988, 1175, 1568], 0.11);
  else if (effect === "raincloud") storm(ctx, master);
}
