import { GLYPHS, type IconName } from "../lib/icons";

// Material Symbols, rendered by codepoint from a subset font (src/assets +
// index.css). `name` is typed to the subset, so referencing an icon we didn't
// bundle is a compile error rather than a missing-glyph box at runtime.
interface IconProps {
  name: IconName;
  className?: string;
  filled?: boolean;
}

export function Icon({ name, className = "", filled = false }: IconProps) {
  return (
    <span aria-hidden className={`material-symbols-outlined ${filled ? "icon-filled" : ""} ${className}`}>
      {String.fromCodePoint(GLYPHS[name])}
    </span>
  );
}

export type { IconName };
