import { expect, test, type Page } from "@playwright/test";

const enabled = process.env.ACCOS_FULL_STACK_E2E === "1";
const projectId = process.env.ACCOS_FULL_STACK_PROJECT_ID ?? "";
const token = process.env.ACCOS_DEV_IDENTITY_TOKEN ?? "";
const workspaceId = process.env.ACCOS_DEV_IDENTITY_WORKSPACE_ID ?? "";

async function connect(page: Page) {
  await page.getByLabel("Workspace ID").fill(workspaceId);
  await page.getByLabel("开发 Bearer Token").fill(token);
  await page.getByRole("button", { name: "连接本地身份" }).click();
}

test("live Studio observes SSE terminal state and preserves it after refresh", async ({ page }) => {
  test.skip(!enabled, "requires the live full-stack acceptance profile");
  test.setTimeout(90_000);
  expect(projectId).not.toBe("");
  expect(token).not.toBe("");
  expect(workspaceId).not.toBe("");

  await page.goto(`/projects/${projectId}/workflows`);
  await connect(page);
  await expect(page.getByRole("heading", { name: "技术工作流监控" })).toBeVisible();
  await page.getByRole("button", { name: "提交 framework_smoke" }).click();
  await expect(page.getByRole("heading", { name: "framework_smoke" })).toBeVisible();
  await expect(page.getByText("succeeded", { exact: true }).first()).toBeVisible({
    timeout: 60_000,
  });
  await expect(page.getByText("workflows.run-succeeded", { exact: true })).toBeVisible();

  await page.reload();
  await expect(page.getByRole("heading", { name: "需要登录" })).toBeVisible();
  await connect(page);
  await expect(page.getByText("succeeded", { exact: true }).first()).toBeVisible();
  await expect(page.getByText("workflows.run-succeeded", { exact: true })).toBeVisible();
});
