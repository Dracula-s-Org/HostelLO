import type { ButtonHTMLAttributes } from "react";

type Variant = "primary" | "secondary" | "ghost";
type Size = "md" | "lg";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  fullWidth?: boolean;
}

// Design system §Components: primary uses the coral accent with a 2px tactile
// bottom shadow; secondary is an indigo ghost. Buttons use rounded-lg.
const variants: Record<Variant, string> = {
  primary:
    "bg-secondary-container text-white shadow-[0_2px_0_0_#ac3509] hover:scale-[1.02] active:scale-[0.98]",
  secondary: "border-2 border-primary text-primary hover:bg-primary/5",
  ghost: "border-2 border-outline-variant text-on-surface-variant hover:bg-surface-variant",
};

const sizes: Record<Size, string> = {
  md: "py-2.5 px-4 text-label-md",
  lg: "py-3 px-6 text-label-md",
};

export function Button({
  variant = "primary",
  size = "md",
  fullWidth = false,
  className = "",
  disabled,
  children,
  ...rest
}: ButtonProps) {
  return (
    <button
      {...rest}
      disabled={disabled}
      className={[
        "inline-flex items-center justify-center gap-2 rounded-lg font-heading transition-all",
        "disabled:opacity-60 disabled:pointer-events-none",
        variants[variant],
        sizes[size],
        fullWidth ? "w-full" : "",
        className,
      ].join(" ")}
    >
      {children}
    </button>
  );
}
