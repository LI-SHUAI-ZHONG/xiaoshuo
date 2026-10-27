/** Compile a local, self-contained schema object. External references are forbidden. */
import { readFileSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";
import openapiTS, { astToString } from "openapi-typescript";

const root = fileURLToPath(new URL("..", import.meta.url));
const schema = JSON.parse(
  readFileSync(resolve(root, "packages/api-client/shared-contracts.json"), "utf8"),
);

function requireLocalReferences(value) {
  if (!value || typeof value !== "object") return;
  for (const [key, child] of Object.entries(value)) {
    if (
      ["$ref", "$dynamicRef", "$recursiveRef"].includes(key) &&
      (typeof child !== "string" || !child.startsWith("#/components/schemas/"))
    ) {
      throw new Error("Shared contracts cannot resolve network or filesystem references.");
    }
    requireLocalReferences(child);
  }
}

requireLocalReferences(schema);
const output = astToString(await openapiTS(schema, { alphabetize: true }));
writeFileSync(
  resolve(root, "packages/api-client/src/generated/shared-contracts.ts"),
  output,
  "utf8",
);
