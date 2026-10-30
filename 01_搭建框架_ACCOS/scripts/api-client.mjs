import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";

import openapiTS, { astToString } from "openapi-typescript";

const root = resolve(fileURLToPath(new URL("..", import.meta.url)));
const input = resolve(root, "packages/api-client/openapi.json");
const output = resolve(root, "packages/api-client/src/generated/schema.ts");

async function generate() {
  const document = JSON.parse(readFileSync(input, "utf8"));
  const pending = [document];
  while (pending.length) {
    const value = pending.pop();
    if (value === null || typeof value !== "object") continue;
    if ("$ref" in value && (typeof value.$ref !== "string" || !value.$ref.startsWith("#/")))
      throw new Error("OpenAPI client generation permits only local document references.");
    pending.push(...Object.values(value));
  }
  const nodes = await openapiTS(document, { alphabetize: true });
  return astToString(nodes);
}

async function main() {
  const mode = process.argv[2];
  if (!new Set(["write", "check"]).has(mode)) {
    process.stderr.write("Usage: node scripts/api-client.mjs <write|check>\n");
    return 2;
  }
  const first = await generate();
  if (mode === "write") {
    mkdirSync(resolve(output, ".."), { recursive: true });
    writeFileSync(output, first, "utf8");
    return 0;
  }
  const second = await generate();
  if (first !== second) {
    process.stderr.write("OpenAPI TypeScript generation is not repeatable\n");
    return 1;
  }
  if (!existsSync(output) || readFileSync(output, "utf8") !== first) {
    process.stderr.write("Generated API client types are stale\n");
    return 1;
  }
  process.stdout.write("API client generation reproducibility: PASS\n");
  return 0;
}

process.exitCode = await main();
