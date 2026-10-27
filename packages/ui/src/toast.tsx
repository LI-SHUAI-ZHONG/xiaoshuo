import type { HTMLAttributes, ReactNode } from "react";

import { Button } from "./button.tsx";
import { cx } from "./utils.ts";

export interface ToastProps extends HTMLAttributes<HTMLDivElement> {
  action?: ReactNode;
  onDismiss?: () => void;
  title: string;
  tone?: "info" | "success" | "warning" | "danger";
}

export function Toast({
  action,
  children,
  className,
  onDismiss,
  title,
  tone = "info",
  ...props
}: ToastProps) {
  return (
    <div
      aria-atomic="true"
      className={cx("ui-toast", `ui-toast--${tone}`, className)}
      role={tone === "danger" ? "alert" : "status"}
      {...props}
    >
      <div>
        <strong>{title}</strong>
        {children ? <div className="ui-toast__body">{children}</div> : null}
      </div>
      <div className="ui-toast__actions">
        {action}
        {onDismiss ? (
          <Button aria-label="关闭通知" onClick={onDismiss} variant="ghost">
            ×
          </Button>
        ) : null}
      </div>
    </div>
  );
}

export function ToastRegion({ children }: { children: ReactNode }) {
  return (
    <div aria-label="通知" aria-live="polite" className="ui-toast-region">
      {children}
    </div>
  );
}
