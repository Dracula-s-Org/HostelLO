import type { ReactNode } from "react";
import { Icon, type IconName } from "./Icon";

// Level-1 surface card (DESIGN.md §Elevation): white, rounded-xl, ambient indigo shadow.
export function Card({
  children,
  className = "",
  hover = false,
}: {
  children: ReactNode;
  className?: string;
  hover?: boolean;
}) {
  return (
    <div
      className={[
        "bg-surface-container-lowest rounded-xl p-stack-md border border-outline-variant/30",
        hover ? "shadow-card-hover" : "shadow-card",
        className,
      ].join(" ")}
    >
      {children}
    </div>
  );
}

// Pill chip for habits/amenities (DESIGN.md §Components — light indigo bg, dark indigo text).
export function Chip({
  children,
  tone = "primary",
}: {
  children: ReactNode;
  tone?: "primary" | "secondary" | "neutral";
}) {
  const tones = {
    primary: "bg-primary-fixed text-on-primary-fixed-variant",
    secondary: "bg-secondary-fixed text-on-secondary-fixed-variant",
    neutral: "bg-surface-container text-on-surface-variant",
  } as const;
  return (
    <span className={`inline-flex items-center rounded-full px-3 py-1 text-label-sm ${tones[tone]}`}>
      {children}
    </span>
  );
}

// Verified / status badge with a teal check (DESIGN.md §Verified Badges).
export function Badge({
  children,
  tone = "tertiary",
  icon,
}: {
  children: ReactNode;
  tone?: "tertiary" | "neutral";
  icon?: IconName;
}) {
  const tones = {
    tertiary: "bg-tertiary-fixed text-on-tertiary-fixed-variant",
    neutral: "bg-surface-container text-on-surface-variant",
  } as const;
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-label-sm ${tones[tone]}`}>
      {icon && <Icon name={icon} className="text-[16px]" filled />}
      {children}
    </span>
  );
}

// KYC status dot (DESIGN.md §KYC Indicators — green verified, amber pending).
export function StatusDot({ status }: { status: "VERIFIED" | "PENDING" | "REJECTED" | "NONE" }) {
  const map = {
    VERIFIED: "bg-tertiary-container",
    PENDING: "bg-secondary-container",
    REJECTED: "bg-error",
    NONE: "bg-outline-variant",
  } as const;
  return <span className={`inline-block w-2 h-2 rounded-full ${map[status]}`} />;
}

// Compatibility / progress bar with rounded end-caps (DESIGN.md §Compatibility Bars).
export function CompatibilityBar({
  label,
  value,
  tone = "primary",
}: {
  label: string;
  value: number; // 0..100
  tone?: "primary" | "secondary";
}) {
  const fill = tone === "secondary" ? "bg-secondary-container" : "bg-primary-container";
  return (
    <div>
      <div className="flex justify-between mb-1">
        <span className="text-label-md text-on-surface">{label}</span>
        <span className="text-label-md text-primary">{Math.round(value)}%</span>
      </div>
      <div className="h-2 w-full bg-surface-container rounded-full overflow-hidden">
        <div
          className={`h-full ${fill} rounded-full transition-all duration-1000`}
          style={{ width: `${Math.max(0, Math.min(100, value))}%` }}
        />
      </div>
    </div>
  );
}

// Thin progress stepper for the onboarding wizard (DESIGN.md §Progress Steppers).
export function Stepper({ steps, current }: { steps: string[]; current: number }) {
  return (
    <div className="flex items-center gap-2">
      {steps.map((label, i) => (
        <div key={label} className="flex-1">
          <div
            className={`h-1 rounded-full transition-colors ${
              i < current ? "bg-primary" : i === current ? "bg-secondary-container" : "bg-surface-container"
            }`}
          />
        </div>
      ))}
    </div>
  );
}

export function Spinner({ className = "" }: { className?: string }) {
  return <Icon name="progress_activity" className={`animate-spin ${className}`} />;
}

// Inline error / empty / loading states reused across screens.
export function ErrorNote({ message }: { message: string }) {
  return (
    <div className="flex items-center gap-2 rounded-lg bg-error-container text-on-error-container p-3 text-label-md">
      <Icon name="error" className="text-[18px]" filled />
      {message}
    </div>
  );
}

export function EmptyState({ icon, title, hint }: { icon: IconName; title: string; hint?: string }) {
  return (
    <div className="flex flex-col items-center text-center py-stack-lg text-on-surface-variant">
      <Icon name={icon} className="text-4xl mb-3 text-outline" />
      <p className="text-body-md text-on-surface">{title}</p>
      {hint && <p className="text-label-md mt-1">{hint}</p>}
    </div>
  );
}
