import type { ReactNode } from "react";

import { Button } from "./button.tsx";

interface StateProps {
  action?: ReactNode | undefined;
  description: string;
  title: string;
}

export function EmptyState({ action, description, title }: StateProps) {
  return (
    <section className="ui-state ui-state--empty">
      <span aria-hidden="true" className="ui-state__mark">
        ◇
      </span>
      <h2>{title}</h2>
      <p>{description}</p>
      {action ? <div className="ui-state__action">{action}</div> : null}
    </section>
  );
}

export interface ErrorStateProps extends StateProps {
  correlationId?: string | undefined;
  onRetry?: (() => void) | undefined;
}

export function ErrorState({
  action,
  correlationId,
  description,
  onRetry,
  title,
}: ErrorStateProps) {
  return (
    <section aria-live="assertive" className="ui-state ui-state--error" role="alert">
      <span aria-hidden="true" className="ui-state__mark">
        !
      </span>
      <h2>{title}</h2>
      <p>{description}</p>
      {correlationId ? <p className="ui-state__meta">关联 ID：{correlationId}</p> : null}
      {onRetry || action ? (
        <div className="ui-state__action">
          {onRetry ? <Button onClick={onRetry}>重试</Button> : null}
          {action}
        </div>
      ) : null}
    </section>
  );
}
