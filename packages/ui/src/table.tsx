import type { HTMLAttributes, ReactNode, TableHTMLAttributes } from "react";

import { cx } from "./utils.ts";

export interface TableProps extends TableHTMLAttributes<HTMLTableElement> {
  caption?: string;
  children: ReactNode;
}

export function Table({ caption, children, className, ...props }: TableProps) {
  return (
    <div className="ui-table-wrap" role="region" tabIndex={0}>
      <table className={cx("ui-table", className)} {...props}>
        {caption ? <caption>{caption}</caption> : null}
        {children}
      </table>
    </div>
  );
}

export function TableHead(props: HTMLAttributes<HTMLTableSectionElement>) {
  return <thead {...props} />;
}

export function TableBody(props: HTMLAttributes<HTMLTableSectionElement>) {
  return <tbody {...props} />;
}
