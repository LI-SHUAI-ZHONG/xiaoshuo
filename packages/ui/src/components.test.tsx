// @vitest-environment jsdom

import { render, screen } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, it } from "vitest";

import { Button } from "./button.tsx";
import { Dialog } from "./dialog.tsx";
import { EmptyState, ErrorState } from "./states.tsx";
import { Tabs } from "./tabs.tsx";

function DialogHarness() {
  const [open, setOpen] = useState(false);
  return (
    <>
      <Button
        onClick={() => {
          setOpen(true);
        }}
      >
        打开
      </Button>
      <Dialog onOpenChange={setOpen} open={open} title="设置">
        <Button
          onClick={() => {
            setOpen(false);
          }}
        >
          完成
        </Button>
      </Dialog>
    </>
  );
}

describe("design system accessibility", () => {
  it("restores focus after a dialog closes", async () => {
    const user = userEvent.setup();
    render(<DialogHarness />);
    const opener = screen.getByRole("button", { name: "打开" });
    await user.click(opener);
    await user.click(screen.getByRole("button", { name: "完成" }));
    expect(opener).toHaveFocus();
  });

  it("moves tabs with arrow keys", async () => {
    const user = userEvent.setup();
    render(
      <Tabs
        label="fixture-tabs"
        tabs={[
          { id: "one", label: "第一项", panel: "fixture-one" },
          { id: "two", label: "第二项", panel: "fixture-two" },
        ]}
      />,
    );
    const first = screen.getByRole("tab", { name: "第一项" });
    first.focus();
    await user.keyboard("{ArrowRight}");
    expect(screen.getByRole("tab", { name: "第二项" })).toHaveAttribute("aria-selected", "true");
  });

  it("announces empty and error states with non-color cues", () => {
    render(
      <>
        <EmptyState description="fixture-empty" title="空状态" />
        <ErrorState description="fixture-error" title="错误状态" />
      </>,
    );
    expect(screen.getByRole("heading", { name: "空状态" })).toBeVisible();
    expect(screen.getByRole("alert")).toHaveTextContent("!");
  });
});
