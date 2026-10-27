import { Badge } from "@accos/ui";

import { toneForStatus } from "./status";

export function StatusBadge({ status }: { status: string }) {
  return <Badge tone={toneForStatus(status)}>{status}</Badge>;
}
