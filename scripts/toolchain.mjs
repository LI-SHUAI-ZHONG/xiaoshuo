import { spawnSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";

const repositoryRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const packageManifest = JSON.parse(readFileSync(resolve(repositoryRoot, "package.json"), "utf8"));
const expected = packageManifest.accos.toolchain;
const uvCommand = process.platform === "win32" ? "uv.exe" : "uv";
const corepackCli = resolve(
  dirname(process.execPath),
  "node_modules",
  "corepack",
  "dist",
  "corepack.js",
);

function fail(message, exitCode = 1) {
  process.stderr.write(`${message}\n`);
  process.exit(exitCode);
}

function execute(command, args, options = {}) {
  const result = spawnSync(command, args, {
    cwd: repositoryRoot,
    env: process.env,
    stdio: options.capture ? "pipe" : "inherit",
    encoding: options.capture ? "utf8" : undefined,
  });

  if (result.error) {
    fail(`Unable to run ${command}: ${result.error.message}`);
  }
  if (result.status !== 0) {
    if (options.capture && result.stderr) {
      process.stderr.write(result.stderr);
    }
    fail(`${command} ${args.join(" ")} failed`, result.status ?? 1);
  }
  return options.capture ? result.stdout.trim() : "";
}

function executeCorepack(args, options = {}) {
  if (process.platform === "win32") {
    return execute(process.execPath, [corepackCli, ...args], options);
  }
  return execute("corepack", args, options);
}

function verifyBaseToolchain() {
  const nodeVersionFile = readFileSync(resolve(repositoryRoot, ".node-version"), "utf8").trim();
  const pythonVersionFile = readFileSync(resolve(repositoryRoot, ".python-version"), "utf8").trim();

  if (nodeVersionFile !== expected.node || process.versions.node !== expected.node) {
    fail(
      `Node ${expected.node} is required; active version is ${process.versions.node}. ` +
        "Activate .node-version before running project commands.",
    );
  }
  if (pythonVersionFile !== expected.python) {
    fail(`.python-version must remain pinned to ${expected.python}.`);
  }

  const uvVersion = execute(uvCommand, ["--version"], { capture: true }).split(/\s+/)[1];
  if (uvVersion !== expected.uv) {
    fail(`uv ${expected.uv} is required; active version is ${uvVersion ?? "unknown"}.`);
  }

  const pnpmVersion = executeCorepack(["pnpm", "--version"], {
    capture: true,
  });
  if (pnpmVersion !== expected.pnpm) {
    fail(`pnpm ${expected.pnpm} is required; Corepack selected ${pnpmVersion}.`);
  }
}

function verifyPython() {
  const output = execute(uvCommand, ["run", "--frozen", "python", "--version"], {
    capture: true,
  });
  const activeVersion = output.split(/\s+/)[1];
  if (activeVersion !== expected.python) {
    fail(`Python ${expected.python} is required; uv selected ${activeVersion ?? "unknown"}.`);
  }
}

function runFormatChecks() {
  execute(uvCommand, ["run", "ruff", "format", "--check", "services/core", "scripts"]);
  executeCorepack([
    "pnpm",
    "exec",
    "prettier",
    "--check",
    "package.json",
    "pnpm-workspace.yaml",
    ".pre-commit-config.yaml",
    ".dependency-cruiser.cjs",
    ".prettierrc.json",
    ".github/workflows/*.yml",
    "eslint.config.mjs",
    "vitest.config.ts",
    "tsconfig.json",
    ".vscode/*.json",
    "apps/*/package.json",
    "apps/*/{next-env.d.ts,next.config.ts,postcss.config.mjs,tsconfig.json}",
    "apps/*/src/**/*.{css,ts,tsx}",
    "packages/*/package.json",
    "packages/*/tsconfig.json",
    "packages/api-client/openapi*.json",
    "packages/api-client/src/**/*.ts",
    "packages/ui/src/**/*.{css,ts,tsx}",
    "playwright.config.ts",
    "scripts/**/*.mjs",
    "tests/setup.ts",
    "tests/e2e/**/*.ts",
    "tests/unit/**/*.ts",
    "docs/acceptance-v0.1-skeleton.md",
    "docs/content-layer-entrypoints.md",
    "docs/traceability-v0.1-skeleton.md",
    "docs/handoffs/18.md",
    "docs/handoffs/19.md",
    "docs/handoffs/20.md",
    "docs/handoffs/21.md",
    "docs/handoffs/22.md",
    "docs/handoffs/23.md",
    "docs/architecture/extension-parking-lot.md",
    "docs/runbooks/backup-disaster-recovery.md",
    "docs/runbooks/first-run.md",
    "docs/runbooks/observability-resilience.md",
    "infra/compose.yaml",
    "infra/observability/*.{yaml,yml}",
  ]);
}

function runLinters() {
  execute(uvCommand, ["run", "ruff", "check", "services/core", "scripts"]);
  execute(uvCommand, ["run", "lint-imports"]);
  execute(uvCommand, ["run", "python", "scripts/check_import_boundaries.py"]);
  execute(uvCommand, ["run", "python", "scripts/check_table_ownership.py"]);
  execute(uvCommand, ["run", "--frozen", "python", "scripts/security_checks.py"]);
  execute(uvCommand, ["run", "--frozen", "python", "scripts/export_openapi.py", "--check"]);
  execute(process.execPath, ["scripts/check-openapi.mjs", "--self-test"]);
  executeCorepack(["pnpm", "exec", "eslint", ".", "--max-warnings", "0"]);
  executeCorepack([
    "pnpm",
    "exec",
    "depcruise",
    "--config",
    ".dependency-cruiser.cjs",
    "apps",
    "packages",
    "tests",
  ]);
}

function runTypeChecks() {
  execute(uvCommand, ["run", "mypy", "services/core/src", "services/core/tests", "scripts"]);
  execute(process.execPath, ["scripts/api-client.mjs", "check"]);
  executeCorepack(["pnpm", "exec", "tsc", "--noEmit"]);
  executeCorepack(["pnpm", "-r", "--if-present", "run", "typecheck"]);
}

function runUnitTests() {
  execute(uvCommand, [
    "run",
    "pytest",
    "--basetemp=.tmp-pytest",
    "-o",
    "cache_dir=.tmp-pytest-cache",
  ]);
  executeCorepack(["pnpm", "exec", "vitest", "run"]);
  execute(process.execPath, ["--test", "tests/construction/static-toolchain.test.mjs"]);
}

function runBrowserTests() {
  execute(process.execPath, ["scripts/run-playwright.mjs"]);
}

function runBuildChecks() {
  executeCorepack(["pnpm", "--filter", "@accos/studio", "run", "build"]);
}

function installDependencies() {
  execute(uvCommand, ["sync", "--locked", "--all-packages"]);
  executeCorepack(["pnpm", "install", "--frozen-lockfile"]);
  execute(uvCommand, ["run", "pre-commit", "install"]);
}

const command = process.argv[2];
// Construction stages 24–44 bypass Corepack/uv setup and every runtime gate.
// Keep all historical gates below intact for the final acceptance stage.
if (command === "static") {
  execute(process.execPath, ["scripts/static-toolchain.mjs", ...process.argv.slice(3)]);
  process.exit(0);
}
const supportedCommands = new Set([
  "check",
  "build",
  "e2e",
  "format",
  "install",
  "lint",
  "quick",
  "test",
  "typecheck",
  "verify",
]);

if (!command || !supportedCommands.has(command)) {
  fail(`Usage: node scripts/toolchain.mjs <${[...supportedCommands].join("|")}>`);
}

verifyBaseToolchain();

if (command === "install") {
  installDependencies();
  verifyPython();
} else {
  verifyPython();
  if (command === "format" || command === "quick" || command === "check") {
    runFormatChecks();
  }
  if (command === "lint" || command === "quick" || command === "check") {
    runLinters();
  }
  if (command === "typecheck" || command === "check") {
    runTypeChecks();
  }
  if (command === "test" || command === "check") {
    runUnitTests();
  }
  if (command === "e2e" || command === "check") {
    runBrowserTests();
  }
  if (command === "build" || command === "check") {
    runBuildChecks();
  }
}

process.stdout.write(`Toolchain command '${command}' completed successfully.\n`);
