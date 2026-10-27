import type { HTMLAttributes } from "react";

import { cx } from "./utils.ts";

export interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  tone?: "neutral" | "success" | "warning" | "danger" | "info";
}

const symbols = {
  danger: "!",
  info: "i",
  neutral: "•",
  success: "✓",
  warning: "△",
} as const;

export function Badge({ children, className, tone = "neutral", ...props }: BadgeProps) {
  return (
    <span className={cx("ui-badge", `ui-badge--${tone}`, className)} {...props}>
      <span aria-hidden="true">{symbols[tone]}</span>
      {children}
    </span>
  );
}
