import { forwardRef, type ButtonHTMLAttributes } from "react";

import { cx } from "./utils.ts";

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  busy?: boolean;
  variant?: "primary" | "secondary" | "ghost" | "danger";
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { busy = false, children, className, disabled, type = "button", variant = "primary", ...props },
  ref,
) {
  return (
    <button
      ref={ref}
      aria-busy={busy || undefined}
      className={cx("ui-button", `ui-button--${variant}`, className)}
      disabled={busy ? true : disabled}
      type={type}
      {...props}
    >
      {busy ? <span aria-hidden="true" className="ui-button__spinner" /> : null}
      <span>{children}</span>
    </button>
  );
});
