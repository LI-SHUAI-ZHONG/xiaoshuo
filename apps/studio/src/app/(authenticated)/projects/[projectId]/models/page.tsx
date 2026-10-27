import { Suspense } from "react";
import { ModelWorkspace } from "../../../../../features/models/model-workspace";

export default function ModelCallsPage() {
  return (
    <Suspense fallback={<p>正在读取调用记录…</p>}>
      <ModelWorkspace />
    </Suspense>
  );
}
