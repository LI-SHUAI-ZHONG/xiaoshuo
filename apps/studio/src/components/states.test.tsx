// @vitest-environment jsdom

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { NetworkStatus } from "./network-status";
import { StateResolver } from "./state-resolver";

describe("Studio states", () => {
  it.each([
    ["unauthenticated", "需要登录"],
    ["forbidden", "无权访问"],
    ["offline", "当前离线"],
    ["degraded", "服务降级"],
    ["empty-workspaces", "暂无 Workspace"],
    ["empty-projects", "暂无 Project"],
  ] as const)("renders %s independently", (state, heading) => {
    const { unmount } = render(<StateResolver state={state} />);
    expect(screen.getByRole("heading", { name: heading })).toBeVisible();
    unmount();
  });

  it("distinguishes offline and degraded banners with text", () => {
    const { rerender } = render(<NetworkStatus state="offline" />);
    expect(screen.getByRole("alert")).toHaveTextContent("离线");
    rerender(<NetworkStatus state="degraded" />);
    expect(screen.getByRole("status")).toHaveTextContent("降级");
  });
});
