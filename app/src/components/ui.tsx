import type { ButtonHTMLAttributes, ReactNode } from "react";

export function cx(...classes: (string | false | null | undefined)[]) {
  return classes.filter(Boolean).join(" ");
}

type Variant = "primary" | "secondary" | "ghost";

export function Button({
  variant = "secondary",
  className,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant }) {
  return (
    <button
      type="button"
      className={cx(
        "inline-flex h-9 items-center justify-center gap-2 rounded-control px-3.5 text-[13px] font-medium",
        "transition-colors disabled:cursor-not-allowed disabled:opacity-40",
        variant === "primary" && "bg-accent text-accent-ink hover:bg-accent-strong",
        variant === "secondary" && "border border-line-strong bg-raised text-text hover:bg-hover",
        variant === "ghost" && "text-muted hover:bg-raised hover:text-text",
        className,
      )}
      {...props}
    />
  );
}

export function Switch({
  checked,
  onChange,
  disabled,
  label,
}: {
  checked: boolean;
  onChange: (value: boolean) => void;
  disabled?: boolean;
  label: string;
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={label}
      disabled={disabled}
      onClick={() => onChange(!checked)}
      className={cx(
        "relative h-[22px] w-[38px] shrink-0 rounded-full border transition-colors",
        "disabled:cursor-not-allowed disabled:opacity-40",
        checked ? "border-accent bg-accent" : "border-line-strong bg-raised",
      )}
    >
      <span
        className={cx(
          "absolute top-[2px] size-4 rounded-full transition-all",
          checked ? "left-[18px] bg-accent-ink" : "left-[2px] bg-muted",
        )}
      />
    </button>
  );
}

export function Segmented<T extends string>({
  value,
  options,
  onChange,
}: {
  value: T;
  options: { value: T; label: string; icon?: ReactNode }[];
  onChange: (value: T) => void;
}) {
  return (
    <div className="grid auto-cols-fr grid-flow-col gap-1 rounded-card border border-line bg-ink p-1">
      {options.map((option) => (
        <button
          key={option.value}
          type="button"
          onClick={() => onChange(option.value)}
          className={cx(
            "flex h-8 items-center justify-center gap-1.5 rounded-control text-[13px] font-medium transition-colors",
            value === option.value ? "bg-raised text-text shadow-sm" : "text-muted hover:text-text",
          )}
        >
          {option.icon}
          {option.label}
        </button>
      ))}
    </div>
  );
}

export function Field({ label, hint, children }: { label: string; hint?: ReactNode; children: ReactNode }) {
  return (
    <div className="flex flex-col gap-2">
      <div className="text-[12px] font-medium tracking-wide text-muted uppercase">{label}</div>
      {children}
      {hint && <div className="text-[12px] leading-relaxed text-faint">{hint}</div>}
    </div>
  );
}

export function Select({
  value,
  onChange,
  options,
  label,
}: {
  value: string;
  onChange: (value: string) => void;
  options: { value: string; label: string; disabled?: boolean }[];
  label: string;
}) {
  return (
    <select
      aria-label={label}
      value={value}
      onChange={(event) => onChange(event.target.value)}
      className="h-9 w-full appearance-none rounded-control border border-line-strong bg-raised bg-[length:14px] bg-[right_10px_center] bg-no-repeat px-3 pr-8 text-[13px] text-text hover:bg-hover"
      style={{
        backgroundImage:
          "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%238c93a3' stroke-width='2'%3E%3Cpath d='m6 9 6 6 6-6'/%3E%3C/svg%3E\")",
      }}
    >
      {options.map((option) => (
        <option key={option.value} value={option.value} disabled={option.disabled}>
          {option.label}
        </option>
      ))}
    </select>
  );
}

export function Row({ title, detail, children }: { title: string; detail?: ReactNode; children: ReactNode }) {
  return (
    <div className="flex items-start justify-between gap-4">
      <div className="min-w-0">
        <div className="text-[14px] font-medium text-text">{title}</div>
        {detail && <div className="mt-0.5 text-[12.5px] leading-relaxed text-muted">{detail}</div>}
      </div>
      <div className="pt-0.5">{children}</div>
    </div>
  );
}
