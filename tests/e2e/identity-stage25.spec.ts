// T004/T005/T006/T008/T009/T010: execute against the isolated stage-45 installation only.
import { expect, test } from "@playwright/test";

test("T005 cancelled team login explains recovery without rendering provider text", async ({
  page,
}) => {
  // UI fixture only; real OIDC acceptance has its own configured IdP requirement.
  await page.route("**/api/v1/auth/session", (route) =>
    route.fulfill({
      json: {
        authenticated: false,
        bootstrap_required: false,
        oidc_configured: true,
        workspaces: [],
      },
    }),
  );
  await page.goto("/login?auth_error=cancelled&error_description=untrusted-provider-text");
  await expect(page.getByRole("status").filter({ hasText: "已取消团队登录" })).toBeVisible();
  await expect(page.getByRole("link", { name: "使用团队身份登录" })).toBeVisible();
  await expect(page.getByLabel("密码", { exact: true })).toBeVisible();
  await expect(page.getByText("untrusted-provider-text")).toHaveCount(0);
  await page.goto("/login?auth_error=untrusted-provider-text");
  await expect(page.getByText("untrusted-provider-text")).toHaveCount(0);
});

test("local login, CAS settings, write-only tokens and durable logout", async ({ page }) => {
  const username = process.env.ACCOS_ACCEPTANCE_USERNAME;
  const password = process.env.ACCOS_ACCEPTANCE_PASSWORD;
  test.skip(!username || !password, "Requires stage-45 isolated local owner credentials");
  await page.goto("/login");
  await page.getByLabel("账号（至少 3 个英文字母或数字）").fill(username!);
  await page.getByLabel("密码", { exact: true }).fill(password!);
  await page.getByRole("button", { name: "登录", exact: true }).click();
  await page.getByRole("link", { name: "进入创作工作台" }).click();
  await page.goto("/settings");
  await expect(page.getByRole("heading", { name: "账号与工作区设置" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "能力状态" })).toBeVisible();
  await page.getByLabel("令牌用途").fill("isolated-acceptance-reader");
  await page.getByRole("button", { name: "创建令牌", exact: true }).click();
  const once = page.getByLabel("新 API 令牌");
  await expect(once).toHaveValue(/^accos_pat_/);
  await page.getByRole("button", { name: "已保存，关闭显示" }).click();
  await page.reload();
  await expect(once).toHaveCount(0);
  const row = page.locator("li").filter({ hasText: "isolated-acceptance-reader" });
  await row.getByRole("button", { name: "撤销", exact: true }).click();
  await expect(row.getByRole("button", { name: "已撤销", exact: true })).toBeDisabled();
  await page.getByLabel("打开用户与 Workspace 菜单").click();
  await page.getByRole("button", { name: "退出当前会话" }).click();
  await page.reload();
  await expect(page.getByRole("heading", { name: "登录创作空间" })).toBeVisible();
});
