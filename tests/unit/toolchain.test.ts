import { describe, expect, it } from "vitest";

describe("TypeScript test harness", () => {
  it("runs deterministic fixtures", () => {
    expect("fixture-project").toBe("fixture-project");
  });
});
