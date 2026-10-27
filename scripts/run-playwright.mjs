import { spawn, spawnSync } from "node:child_process";
import { dirname, resolve } from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";

const repositoryRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const serverUrl = "http://127.0.0.1:3100/status";
const nextCli = resolve(
  repositoryRoot,
  "apps",
  "studio",
  "node_modules",
  "next",
  "dist",
  "bin",
  "next",
);
const playwrightCli = resolve(repositoryRoot, "node_modules", "@playwright", "test", "cli.js");

function delay(milliseconds) {
  return new Promise((resolveDelay) => setTimeout(resolveDelay, milliseconds));
}

async function serverIsReady() {
  try {
    const response = await fetch(serverUrl, { signal: AbortSignal.timeout(1_000) });
    await response.arrayBuffer();
    return response.ok;
  } catch {
    return false;
  }
}

async function waitForServer(server) {
  const deadline = Date.now() + 120_000;
  while (Date.now() < deadline) {
    if (server.exitCode !== null) {
      throw new Error(`Studio test server exited with code ${server.exitCode}.`);
    }
    if (await serverIsReady()) {
      return;
    }
    await delay(250);
  }
  throw new Error(`Studio test server did not become ready at ${serverUrl}.`);
}

function stopServer(server) {
  if (server === null || server.exitCode !== null || server.pid === undefined) {
    return;
  }
  if (process.platform === "win32") {
    spawnSync("taskkill.exe", ["/PID", String(server.pid), "/T", "/F"], {
      stdio: "ignore",
      windowsHide: true,
    });
  } else {
    try {
      process.kill(-server.pid, "SIGTERM");
    } catch {
      server.kill("SIGTERM");
    }
  }
  server.unref();
}

let server = null;
let exitCode;

try {
  if (!(await serverIsReady())) {
    server = spawn(
      process.execPath,
      [nextCli, "dev", "apps/studio", "--webpack", "--hostname", "127.0.0.1", "--port", "3100"],
      {
        cwd: repositoryRoot,
        detached: process.platform !== "win32",
        env: process.env,
        stdio: "inherit",
        windowsHide: true,
      },
    );
    await waitForServer(server);
  }

  const result = spawnSync(process.execPath, [playwrightCli, "test"], {
    cwd: repositoryRoot,
    env: { ...process.env, ACCOS_E2E_SERVER_MANAGED: "1" },
    stdio: "inherit",
  });
  if (result.error) {
    throw result.error;
  }
  exitCode = result.status ?? 1;
} finally {
  stopServer(server);
}

process.exitCode = exitCode;
