import { cx } from "./utils.ts";

export interface SkeletonProps {
  className?: string;
  label?: string;
  lines?: number;
}

export function Skeleton({ className, label = "正在加载", lines = 3 }: SkeletonProps) {
  return (
    <div aria-busy="true" aria-label={label} className={cx("ui-skeleton", className)} role="status">
      {Array.from({ length: lines }, (_, index) => (
        <span key={index} aria-hidden="true" className="ui-skeleton__line" />
      ))}
    </div>
  );
}
