import type { ReactNode } from "react";

const inputClass =
  "w-full rounded-lg border border-outline-variant bg-surface-container-lowest px-4 py-3 text-body-md focus:outline-none focus:border-primary";

function FieldShell({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="block">
      <span className="block text-label-md text-on-surface mb-1.5">{label}</span>
      {children}
    </label>
  );
}

export function TextField({
  label,
  value,
  onChange,
  type = "text",
  placeholder,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  type?: string;
  placeholder?: string;
}) {
  return (
    <FieldShell label={label}>
      <input
        type={type}
        value={value}
        placeholder={placeholder}
        onChange={(e) => onChange(e.target.value)}
        className={inputClass}
      />
    </FieldShell>
  );
}

export function NumberField({
  label,
  value,
  onChange,
  min,
  max,
}: {
  label: string;
  value: number | "";
  onChange: (v: number | "") => void;
  min?: number;
  max?: number;
}) {
  return (
    <FieldShell label={label}>
      <input
        type="number"
        value={value}
        min={min}
        max={max}
        onChange={(e) => onChange(e.target.value === "" ? "" : Number(e.target.value))}
        className={inputClass}
      />
    </FieldShell>
  );
}

export function SelectField<T extends string>({
  label,
  value,
  onChange,
  options,
}: {
  label: string;
  value: T;
  onChange: (v: T) => void;
  options: { value: T; label: string }[];
}) {
  return (
    <FieldShell label={label}>
      <select value={value} onChange={(e) => onChange(e.target.value as T)} className={inputClass}>
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
    </FieldShell>
  );
}

export function ToggleField({
  label,
  checked,
  onChange,
}: {
  label: string;
  checked: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <button
      type="button"
      onClick={() => onChange(!checked)}
      className="flex items-center justify-between w-full rounded-lg border border-outline-variant bg-surface-container-lowest px-4 py-3"
    >
      <span className="text-body-md text-on-surface">{label}</span>
      <span
        className={`relative w-11 h-6 rounded-full transition-colors ${checked ? "bg-secondary-container" : "bg-surface-container-highest"}`}
      >
        <span
          className={`absolute top-0.5 left-0.5 w-5 h-5 rounded-full bg-white transition-transform ${checked ? "translate-x-5" : ""}`}
        />
      </span>
    </button>
  );
}

// 1..N segmented selector for the habit frequency / cleanliness scales.
export function ScaleField({
  label,
  value,
  onChange,
  max = 5,
  lowHint,
  highHint,
}: {
  label: string;
  value: number;
  onChange: (v: number) => void;
  max?: number;
  lowHint?: string;
  highHint?: string;
}) {
  return (
    <div>
      <span className="block text-label-md text-on-surface mb-1.5">{label}</span>
      <div className="flex gap-2">
        {Array.from({ length: max }, (_, i) => i + 1).map((n) => (
          <button
            type="button"
            key={n}
            onClick={() => onChange(n)}
            className={`flex-1 py-2.5 rounded-lg text-label-md transition-colors ${
              value === n
                ? "bg-primary text-on-primary"
                : "bg-surface-container text-on-surface-variant hover:bg-surface-container-high"
            }`}
          >
            {n}
          </button>
        ))}
      </div>
      {(lowHint || highHint) && (
        <div className="flex justify-between mt-1 text-label-sm text-on-surface-variant">
          <span>{lowHint}</span>
          <span>{highHint}</span>
        </div>
      )}
    </div>
  );
}
