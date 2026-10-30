import { forwardRef, useId, type SelectHTMLAttributes } from "react";

import { cx } from "./utils.ts";

export interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  description?: string;
  error?: string;
  label: string;
}

export const Select = forwardRef<HTMLSelectElement, SelectProps>(function Select(
  { children, className, description, error, id: providedId, label, ...props },
  ref,
) {
  const generatedId = useId();
  const id = providedId ?? generatedId;
  const descriptionId = description ? `${id}-description` : undefined;
  const errorId = error ? `${id}-error` : undefined;
  const describedBy = [descriptionId, errorId].filter(Boolean).join(" ") || undefined;

  return (
    <label className="ui-field" htmlFor={id}>
      <span className="ui-field__label">{label}</span>
      {description ? (
        <span className="ui-field__description" id={descriptionId}>
          {description}
        </span>
      ) : null}
      <span className="ui-select-wrap">
        <select
          ref={ref}
          aria-describedby={describedBy}
          aria-invalid={Boolean(error)}
          className={cx("ui-select", className)}
          id={id}
          {...props}
        >
          {children}
        </select>
      </span>
      {error ? (
        <span className="ui-field__error" id={errorId} role="alert">
          {error}
        </span>
      ) : null}
    </label>
  );
});
