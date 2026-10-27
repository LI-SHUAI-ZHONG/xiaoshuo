/** Offline construction entry. No package manager, test, application or service startup. */
import { spawnSync } from "node:child_process";
import { existsSync, readFileSync, readdirSync } from "node:fs";
import { dirname, resolve } from "node:path";
import process from "node:process";
import { fileURLToPath, pathToFileURL } from "node:url";

export const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
export const modes = Object.freeze(["syntax", "format", "types", "contracts", "api"]);

export function commandPlan(mode, platform = process.platform) {
  const python = resolve(root, ".venv", platform === "win32" ? "Scripts/python.exe" : "bin/python");
  const ruff = resolve(root, ".venv", platform === "win32" ? "Scripts/ruff.exe" : "bin/ruff");
  const node = process.execPath;
  const tsc = resolve(root, "node_modules/typescript/bin/tsc");
  const prettier = resolve(root, "node_modules/prettier/bin/prettier.cjs");
  switch (mode) {
    case "syntax":
      return [
        { command: python, args: ["-I", "scripts/static_syntax.py"] },
        ...readdirSync(resolve(root, "scripts"))
          .filter((name) => name.endsWith(".mjs"))
          .sort()
          .map((name) => ({ command: node, args: ["--check", `scripts/${name}`] })),
      ];
    case "format":
      return [
        { command: ruff, args: ["format", "--check", "services/core", "scripts"] },
        {
          command: node,
          args: [
            prettier,
            "--check",
            "--config",
            ".prettierrc.json",
            "--ignore-path",
            ".prettierignore",
            "--no-editorconfig",
            "package.json",
            "scripts/*.mjs",
            "packages/*/src/**/*.{ts,tsx,css}",
            "apps/studio/src/**/*.{ts,tsx,css}",
          ],
        },
      ];
    case "types":
      return [
        {
          command: python,
          args: [
            "-I",
            "-m",
            "mypy",
            "--config-file",
            "scripts/static-mypy.ini",
            "services/core/src",
          ],
        },
        ...[
          "tsconfig.json",
          "packages/api-client/tsconfig.json",
          "packages/ui/tsconfig.json",
          "apps/studio/tsconfig.json",
        ].map((config) => ({
          command: node,
          args: [tsc, "--noEmit", "--incremental", "false", "--project", config],
        })),
      ];
    case "contracts":
      return [
        { command: python, args: ["-I", "scripts/export_shared_contracts.py"] },
        { command: node, args: ["scripts/shared-contracts.mjs"] },
      ];
    case "api":
      return [
        { command: python, args: ["-I", "scripts/export_openapi.py"] },
        { command: node, args: ["scripts/api-client.mjs", "write"] },
      ];
    default:
      throw new Error(`Usage: node scripts/static-toolchain.mjs <${modes.join("|")}> [--plan]`);
  }
}

export function offlineEnvironment(environment = process.env) {
  const permitted = new Set([
    "path",
    "systemroot",
    "windir",
    "comspec",
    "pathext",
    "temp",
    "tmp",
    "home",
    "userprofile",
    "appdata",
    "localappdata",
    "lang",
    "lc_all",
  ]);
  return {
    ...Object.fromEntries(
      Object.entries(environment).filter(([name]) => permitted.has(name.toLowerCase())),
    ),
    PYTHONUTF8: "1",
    PYTHONDONTWRITEBYTECODE: "1",
    PYTHONNOUSERSITE: "1",
    PIP_NO_INDEX: "1",
    UV_OFFLINE: "1",
    UV_PYTHON_DOWNLOADS: "never",
    COREPACK_ENABLE_NETWORK: "0",
    npm_config_offline: "true",
    NEXT_TELEMETRY_DISABLED: "1",
  };
}

export function runPlan(plan, runner = spawnSync) {
  for (const { command, args } of plan) {
    if (!existsSync(command))
      throw new Error(`Local compiler is missing: ${command}. No install attempted.`);
    const result = runner(command, args, {
      cwd: root,
      env: offlineEnvironment(),
      stdio: "inherit",
      shell: false,
    });
    if (result.error) throw result.error;
    if (result.status !== 0) return result.status ?? 1;
  }
  return 0;
}

export function main(argv = process.argv.slice(2)) {
  if (argv.length > 2 || (argv.length === 2 && argv[1] !== "--plan")) {
    throw new Error("Only a named static mode and --plan are accepted; no command passthrough.");
  }
  const plan = commandPlan(argv[0]);
  if (argv[1] === "--plan") {
    process.stdout.write(`${JSON.stringify(plan, null, 2)}\n`);
    return 0;
  }
  if (argv[0] === "format") {
    const config = JSON.parse(readFileSync(resolve(root, ".prettierrc.json"), "utf8"));
    const allowed = new Set([
      "arrowParens",
      "endOfLine",
      "printWidth",
      "semi",
      "singleQuote",
      "tabWidth",
      "trailingComma",
      "useTabs",
    ]);
    if (Object.keys(config).some((key) => !allowed.has(key))) {
      throw new Error(
        "Static formatting permits only inert formatting options; review new options first.",
      );
    }
  }
  const code = runPlan(plan);
  if (code === 0)
    process.stdout.write(`Static ${argv[0]} completed; runtime validation remains NOT_RUN.\n`);
  return code;
}

if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) {
  try {
    process.exitCode = main();
  } catch (error) {
    process.stderr.write(`${error.message}\n`);
    process.exitCode = 1;
  }
}
