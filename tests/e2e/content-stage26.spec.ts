// T011–T016: run only against the isolated stage-45 installation. No production fixtures.
import { expect, test, type Page } from "@playwright/test";

async function writingProject(page: Page) {
  const username = process.env.ACCOS_ACCEPTANCE_USERNAME;
  const password = process.env.ACCOS_ACCEPTANCE_PASSWORD;
  test.skip(!username || !password, "Requires stage-45 isolated owner credentials");
  await page.goto("/login");
  await page.getByLabel("账号（至少 3 个英文字母或数字）").fill(username!);
  await page.getByLabel("密码", { exact: true }).fill(password!);
  await page.getByRole("button", { name: "登录", exact: true }).click();
  await expect(page.getByRole("link", { name: "进入创作工作台" })).toBeVisible();
  const session = await (await page.request.get("/api/v1/auth/session")).json();
  const workspace = session.workspaces[0].id as string;
  const headers = {
    "X-Workspace-ID": workspace,
    "X-CSRF-Token": session.csrf_token as string,
    Origin: new URL(page.url()).origin,
  };
  const name = "stage26-" + crypto.randomUUID();
  const project = await page.request.post(`/api/v1/workspaces/${workspace}/projects`, {
    headers: { ...headers, "Idempotency-Key": crypto.randomUUID() },
    data: { name },
  });
  expect(project.status()).toBe(201);
  const projectId = (await project.json()).id as string;
  const artifact = await page.request.post(`/api/v1/projects/${projectId}/artifacts`, {
    headers,
    data: { label: "正文验收", artifact_type: "chapter" },
  });
  expect(artifact.status()).toBe(201);
  const artifactId = (await artifact.json()).id as string;
  const url = `/projects/${projectId}/write/${artifactId}`;
  const api = `/api/v1/projects/${projectId}/artifacts/${artifactId}`;
  await page.goto(url);
  await expect(page.getByRole("textbox", { name: "章节正文" })).toBeVisible();
  return { workspace, projectId, artifactId, url, api, headers, name };
}

test("T011 T013 Chinese text survives reload and restoring creates a new revision", async ({
  page,
}) => {
  const fixture = await writingProject(page);
  const editor = page.getByRole("textbox", { name: "章节正文" });
  await editor.fill("第一版中文🙂，留给未来的作者。");
  await expect(page.getByText("已保存到服务器", { exact: true })).toBeVisible();
  await page.reload();
  await expect(editor).toHaveText("第一版中文🙂，留给未来的作者。");
  const original = await (
    await page.request.get(fixture.api + "/working-copy", { headers: fixture.headers })
  ).json();
  await editor.fill("第二版正文");
  await expect(page.getByText("已保存到服务器", { exact: true })).toBeVisible();
  await page.locator("tbody tr").last().getByRole("button", { name: "恢复为新版本" }).click();
  await expect(editor).toHaveText("第一版中文🙂，留给未来的作者。");
  const current = await (
    await page.request.get(fixture.api + "/working-copy", { headers: fixture.headers })
  ).json();
  expect(current.revision.id).not.toBe(original.revision.id);
  expect(current.revision.parents).toContain(original.revision.id);
});

test("T012 newer keystrokes survive a delayed acknowledgement", async ({ page }) => {
  const fixture = await writingProject(page);
  let release: () => void = () => {};
  const gate = new Promise<void>((resolve) => {
    release = resolve;
  });
  let acknowledged = false;
  let first = true;
  await page.route("**/working-copy?*", async (route) => {
    if (route.request().method() !== "PUT" || !first) {
      await route.continue();
      return;
    }
    first = false;
    const response = await route.fetch();
    acknowledged = true;
    await gate;
    await route.fulfill({ response });
  });
  const editor = page.getByRole("textbox", { name: "章节正文" });
  await editor.fill("已发出的版本");
  await expect.poll(() => acknowledged).toBe(true);
  await editor.fill("保存等待期间继续输入的新正文");
  release();
  await expect(page.getByText("已保存到服务器", { exact: true })).toBeVisible();
  const saved = await (
    await page.request.get(fixture.api + "/working-copy", { headers: fixture.headers })
  ).json();
  expect(saved.text).toBe("保存等待期间继续输入的新正文");
  await page.reload();
  await expect(editor).toHaveText(saved.text);
});

test("T012 failed saves recover from IndexedDB after reload and reconnect", async ({
  page,
  context,
}) => {
  await writingProject(page);
  const editor = page.getByRole("textbox", { name: "章节正文" });
  await editor.fill("已同步基线");
  await expect(page.getByText("已保存到服务器", { exact: true })).toBeVisible();
  await page.route("**/working-copy?*", async (route) => {
    if (route.request().method() === "PUT") await route.abort("internetdisconnected");
    else await route.continue();
  });
  await context.setOffline(true);
  await editor.fill("断网时的本机稿");
  await expect(page.getByText(/本机草稿已保留|离线：仅保存在本机/)).toBeVisible();
  await context.setOffline(false);
  page.on("dialog", (dialog) => void dialog.accept());
  await page.reload();
  await expect(page.getByRole("button", { name: "恢复此本机稿" }).first()).toBeVisible();
  await page.unroute("**/working-copy?*");
  await page.getByRole("button", { name: "恢复此本机稿" }).first().click();
  await expect(editor).toHaveText("断网时的本机稿");
  await expect(page.getByText("已保存到服务器", { exact: true })).toBeVisible();
});

test("T012 T014 two tabs retain same-block conflicts until the author chooses", async ({
  page,
  context,
}) => {
  const fixture = await writingProject(page);
  const editor = page.getByRole("textbox", { name: "章节正文" });
  await editor.fill("共同基线");
  await expect(page.getByText("已保存到服务器", { exact: true })).toBeVisible();
  const other = await context.newPage();
  await other.goto(fixture.url);
  const otherEditor = other.getByRole("textbox", { name: "章节正文" });
  await expect(otherEditor).toHaveText("共同基线");
  await editor.fill("第一窗口新稿");
  await expect(page.getByText("已保存到服务器", { exact: true })).toBeVisible();
  await otherEditor.fill("第二窗口保留稿");
  await expect(other.getByRole("heading", { name: "合并本机与服务器稿件" })).toBeVisible();
  await expect(other.getByText("第一窗口新稿", { exact: true })).toBeVisible();
  await other.getByLabel("保留哪一方").selectOption("theirs");
  await other.getByRole("button", { name: "确认合并并继续保存" }).click();
  await expect(other.getByText("已保存到服务器", { exact: true })).toBeVisible();
  await other.reload();
  await expect(otherEditor).toHaveText("第二窗口保留稿");
});

test("T012 IME composition does not submit an incomplete phrase", async ({ page }) => {
  await writingProject(page);
  let saves = 0;
  page.on("request", (request) => {
    if (request.method() === "PUT" && request.url().includes("working-copy")) saves++;
  });
  const editor = page.getByRole("textbox", { name: "章节正文" });
  await editor.dispatchEvent("compositionstart", { data: "中" });
  await editor.fill("中文输入法");
  // Intentional acceptance timing window: longer than the 1.2s autosave debounce.
  await page.waitForTimeout(1500);
  expect(saves).toBe(0);
  await editor.dispatchEvent("compositionend", { data: "中文输入法" });
  await expect(page.getByText("已保存到服务器", { exact: true })).toBeVisible();
  expect(saves).toBeGreaterThan(0);
});

test("T016 project archive is reversible without losing text", async ({ page }) => {
  const fixture = await writingProject(page);
  const editor = page.getByRole("textbox", { name: "章节正文" });
  await editor.fill("归档之后仍然存在");
  await expect(page.getByText("已保存到服务器", { exact: true })).toBeVisible();
  await page.goto("/projects");
  await page.getByLabel("搜索项目").fill(fixture.name);
  await page.getByRole("button", { name: "归档项目" }).click();
  await page.getByLabel("查看已归档").check();
  await page.getByRole("button", { name: "恢复项目" }).click();
  await page.goto(fixture.url);
  await expect(editor).toHaveText("归档之后仍然存在");
});
