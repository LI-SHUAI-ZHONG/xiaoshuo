import { defineConfig } from "@playwright/test";

export default defineConfig({
  expect: { timeout: 10_000 },
  fullyParallel: false,
  outputDir: ".tmp-playwright/test-results",
  reporter: [["line"]],
  testDir: "tests/e2e",
  timeout: 45_000,
  use: {
    baseURL: process.env.ACCOS_E2E_BASE_URL ?? "http://127.0.0.1:3100",
    launchOptions: process.platform === "win32" ? { channel: "chrome" } : {},
    screenshot: "only-on-failure",
    trace: "retain-on-failure",
  },
  ...(process.env.ACCOS_E2E_SERVER_MANAGED === "1"
    ? {}
    : {
        webServer: {
          command:
            "pnpm --filter @accos/studio exec next dev --webpack --hostname 127.0.0.1 --port 3100",
          reuseExistingServer: process.env.CI !== "true",
          timeout: 120_000,
          url: "http://127.0.0.1:3100/status",
        },
      }),
  workers: 1,
});
