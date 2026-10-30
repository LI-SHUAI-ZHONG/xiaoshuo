"use client";

export default function GlobalError({
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <html lang="zh-CN">
      <body>
        <main id="main-content">
          <h1>Studio 暂时不可用</h1>
          <p>根布局未能加载，请重试。</p>
          <button onClick={reset} type="button">
            重试
          </button>
        </main>
      </body>
    </html>
  );
}
