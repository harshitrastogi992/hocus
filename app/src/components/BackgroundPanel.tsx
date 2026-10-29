import { open } from "@tauri-apps/plugin-dialog";
import { Check, Image, ImagePlus, Palette, ScanLine } from "lucide-react";
import type { BackgroundMode, Catalog, ClientMessage, Settings, Status } from "../lib/protocol";
import { Button, Field, Segmented, cx } from "./ui";

interface Props {
  settings: Settings;
  catalog: Catalog;
  status: Status;
  send: (message: ClientMessage) => void;
}

export function BackgroundPanel({ settings, catalog, status, send }: Props) {
  const background = settings.background;
  const setBackground = (patch: Partial<Settings["background"]>) =>
    send({ type: "update_settings", patch: { background: patch } });

  const chooseImage = async () => {
    const path = await open({
      multiple: false,
      directory: false,
      filters: [{ name: "Images", extensions: ["png", "jpg", "jpeg", "webp", "bmp"] }],
    });
    if (typeof path === "string") setBackground({ mode: "image", image: path });
  };

  return (
    <div className="flex flex-col gap-6">
      <Segmented<BackgroundMode>
        value={background.mode}
        onChange={(mode) => {
          if (mode === "image" && !background.image) void chooseImage();
          else setBackground({ mode });
        }}
        options={[
          { value: "room", label: "Your room", icon: <ScanLine className="size-4" strokeWidth={1.75} /> },
          { value: "preset", label: "Backdrop", icon: <Palette className="size-4" strokeWidth={1.75} /> },
          { value: "image", label: "Image", icon: <Image className="size-4" strokeWidth={1.75} /> },
        ]}
      />

      {background.mode === "room" && (
        <Field
          label="Empty room"
          hint="Step out of view when the countdown starts. Capture again if the light changes or the camera moves."
        >
          <div className="flex items-center justify-between gap-3 rounded-card border border-line bg-raised/60 p-4">
            <div className="text-[13px]">
              {status.plate === "ready" ? (
                <span className="flex items-center gap-2 text-ok">
                  <Check className="size-4" strokeWidth={1.75} /> Room captured
                </span>
              ) : status.plate === "capturing" ? (
                <span className="text-accent">Capturing</span>
              ) : (
                <span className="text-muted">Not captured yet</span>
              )}
            </div>
            <Button
              variant={status.plate === "ready" ? "secondary" : "primary"}
              disabled={status.plate === "capturing" || !status.camera.ok}
              onClick={() => send({ type: "capture_plate" })}
            >
              {status.plate === "ready" ? "Capture again" : "Capture room"}
            </Button>
          </div>
        </Field>
      )}

      {background.mode === "preset" && (
        <Field label="Backdrop" hint="Backdrops replace your real room, and you vanish into them.">
          <div className="grid grid-cols-2 gap-3">
            {catalog.presets.map((preset) => (
              <button
                key={preset.id}
                type="button"
                onClick={() => setBackground({ mode: "preset", preset: preset.id })}
                className={cx(
                  "group overflow-hidden rounded-card border-2 text-left transition-colors",
                  background.preset === preset.id ? "border-accent" : "border-transparent hover:border-line-strong",
                )}
              >
                <img src={preset.thumbnail} alt="" className="aspect-video w-full object-cover" />
                <div className="bg-raised px-3 py-2 text-[13px] font-medium">{preset.label}</div>
              </button>
            ))}
          </div>
        </Field>
      )}

      {background.mode === "image" && (
        <Field label="Image" hint="Large images are cropped to fill the frame.">
          <div className="flex items-center gap-3 rounded-card border border-line bg-raised/60 p-4">
            <ImagePlus className="size-5 shrink-0 text-faint" strokeWidth={1.75} />
            <div className="min-w-0 flex-1 truncate text-[13px] text-muted" title={background.image ?? ""}>
              {background.image?.split(/[\\/]/).pop() ?? "No image chosen"}
            </div>
            <Button onClick={chooseImage}>Choose</Button>
          </div>
        </Field>
      )}
    </div>
  );
}
