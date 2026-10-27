"use client";

import { ErrorState } from "@accos/ui";
import { useEffect } from "react";

export default function ErrorBoundary({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // Client telemetry adapter is intentionally deferred; do not expose the error body.
  }, [error]);
  return (
    <main className="studio-state-wrap" id="main-content">
      <ErrorState
        correlationId={error.digest}
        description="Studio 无法完成本次渲染。可以安全重试。"
        onRetry={reset}
        title="页面发生错误"
      />
    </main>
  );
}
