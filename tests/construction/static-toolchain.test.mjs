// T003. Execute only at stage 45; child processes are recorded, never launched here.
import assert from "node:assert/strict";
import test from "node:test";
import {
  commandPlan,
  main,
  modes,
  offlineEnvironment,
  runPlan,
} from "../../scripts/static-toolchain.mjs";

test("every construction mode has only reviewed compiler commands", () => {
  for (const mode of modes) {
    const plan = commandPlan(mode);
    const calls = [];
    assert.equal(
      runPlan(plan, (command, args, options) => {
        calls.push({ command, args });
        assert.equal(options.shell, false);
        assert.equal(options.env.COREPACK_ENABLE_NETWORK, "0");
        assert.equal(options.env.UV_OFFLINE, "1");
        assert.equal(options.env.NODE_OPTIONS, undefined);
        return { status: 0 };
      }),
      0,
    );
    assert.deepEqual(calls, plan);
    for (const { command, args } of calls) {
      const invocation = [command, ...args].join(" ");
      assert.doesNotMatch(
        invocation,
        /\b(pytest|vitest|playwright|uvicorn|celery|alembic|corepack|pnpm|npm|curl|docker)\b/,
      );
      assert.doesNotMatch(
        invocation,
        /--self-test|next.*(?:build|dev|start)/,
      );
      if (mode !== "api") assert.doesNotMatch(invocation, /export_openapi|api-client\.mjs/);
      if (mode === "api") assert.deepEqual(args, command.includes("python") ? ["-I", "scripts/export_openapi.py"] : ["scripts/api-client.mjs", "write"]);
    }
  }
});

test("unknown commands and arbitrary argument forwarding fail closed", () => {
  for (const mode of [undefined, "test", "quick", "lint", "install", "syntax; pytest"]) {
    assert.throws(() => commandPlan(mode));
  }
  assert.throws(() => main(["syntax", "--self-test"]));
  assert.throws(() => main(["syntax", "--plan", "test"]));
});

test("compiler failure stops the remaining plan", () => {
  let calls = 0;
  const plan = commandPlan("syntax");
  assert.equal(
    runPlan(plan, () => {
      calls += 1;
      return { status: 7 };
    }),
    7,
  );
  assert.equal(calls, 1);
});

test("static compilers do not inherit credentials or startup hooks", () => {
  const environment = offlineEnvironment({
    PATH: "fixture-path",
    SystemRoot: "fixture-root",
    NODE_OPTIONS: "--import fixture-hook",
    PYTHONPATH: "fixture-module",
    ACCOS_DATABASE_URL: "fixture-private",
    OPENAI_API_KEY: "fixture-private",
  });
  assert.equal(environment.PATH, "fixture-path");
  for (const key of ["NODE_OPTIONS", "PYTHONPATH", "ACCOS_DATABASE_URL", "OPENAI_API_KEY"]) {
    assert.equal(environment[key], undefined);
  }
});
