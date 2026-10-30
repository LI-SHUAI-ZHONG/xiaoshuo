import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";

const root = resolve(fileURLToPath(new URL("..", import.meta.url)));
const schemaPath = resolve(root, "packages/api-client/openapi.json");
const baselinePath = resolve(root, "packages/api-client/openapi.snapshot.json");
const httpMethods = new Set(["get", "post", "put", "patch", "delete", "options", "head"]);
const requiredErrors = ["400", "401", "403", "404", "409", "415", "422", "428", "429"];
const requiredStage17Operations = [
  "listWorkflowDefinitions",
  "createDirectorAgentRun",
  "getModelStatus",
  "getToolStatus",
  "createKnowledgeIngestionRun",
  "createMemory",
  "createWorld",
  "createConsistencyCheck",
  "createQualityEvaluation",
  "createFeedback",
  "createImprovementProposal",
  "streamWorkflowEvents",
];

function readJson(path) {
  return JSON.parse(readFileSync(path, "utf8"));
}

export function lintSchema(schema) {
  const failures = [];
  if (!String(schema.openapi).startsWith("3.1.")) failures.push("OpenAPI 3.1 is required");
  if (schema.info?.["x-api-version"] !== "v1") failures.push("x-api-version must be v1");
  if (!schema.components?.schemas?.ErrorEnvelope) failures.push("ErrorEnvelope is required");
  if (!schema.components?.schemas?.AsyncOperationReference) {
    failures.push("AsyncOperationReference is required");
  }
  if (!schema.components?.schemas?.SseEventData) failures.push("SseEventData is required");
  const operationIds = new Set();
  for (const [path, pathItem] of Object.entries(schema.paths ?? {})) {
    for (const [method, operation] of Object.entries(pathItem)) {
      if (!httpMethods.has(method)) continue;
      if (!operation.operationId)
        failures.push(`${method.toUpperCase()} ${path} has no operationId`);
      if (operationIds.has(operation.operationId))
        failures.push(`duplicate ${operation.operationId}`);
      operationIds.add(operation.operationId);
      if (path.startsWith("/api/v1/") && !operation.deprecated) {
        if (!operation.security?.length)
          failures.push(`${method.toUpperCase()} ${path} is unsecured`);
        const parameters = [...(pathItem.parameters ?? []), ...(operation.parameters ?? [])];
        if (
          !parameters.some(
            (parameter) => parameter.in === "header" && parameter.name === "X-Workspace-ID",
          )
        ) {
          failures.push(`${method.toUpperCase()} ${path} lacks X-Workspace-ID`);
        }
        for (const code of requiredErrors) {
          if (!operation.responses?.[code])
            failures.push(`${method.toUpperCase()} ${path} lacks ${code}`);
        }
      }
      const bodyTypes = Object.keys(operation.requestBody?.content ?? {});
      if (bodyTypes.some((mediaType) => mediaType !== "application/json")) {
        failures.push(`${method.toUpperCase()} ${path} has a non-JSON request body`);
      }
    }
  }
  for (const operationId of requiredStage17Operations) {
    if (!operationIds.has(operationId)) {
      failures.push(`execution 17 operation ${operationId} is required`);
    }
  }
  const eventOperation = schema.paths?.["/api/v1/events"]?.get;
  const eventContent = eventOperation?.responses?.["200"]?.content?.["text/event-stream"];
  if (!eventContent) {
    failures.push("execution 17 event stream must expose text/event-stream");
  }
  if (eventContent?.["x-accos-event-data-schema"]?.$ref !== "#/components/schemas/SseEventData") {
    failures.push("execution 17 event stream must reference SseEventData");
  }
  const eventParameters = eventOperation?.parameters ?? [];
  if (
    !eventParameters.some(
      (parameter) => parameter.in === "header" && parameter.name === "Last-Event-ID",
    )
  ) {
    failures.push("execution 17 event stream must accept Last-Event-ID");
  }
  const publicText = JSON.stringify(schema.components?.schemas ?? {}).toLowerCase();
  for (const forbidden of ["sqlalchemy", "object_key", "secret_key", "password", "stack trace"]) {
    if (publicText.includes(forbidden)) failures.push(`public schema leaks ${forbidden}`);
  }
  return failures;
}

function operations(schema) {
  const result = new Map();
  for (const [path, pathItem] of Object.entries(schema.paths ?? {})) {
    for (const [method, operation] of Object.entries(pathItem)) {
      if (httpMethods.has(method)) result.set(`${method} ${path}`, operation);
    }
  }
  return result;
}

export function breakingChanges(baseline, candidate) {
  const failures = [];
  const current = operations(candidate);
  for (const [key, operation] of operations(baseline)) {
    const replacement = current.get(key);
    if (!replacement) {
      failures.push(`removed operation ${key}`);
      continue;
    }
    for (const responseCode of Object.keys(operation.responses ?? {})) {
      if (!replacement.responses?.[responseCode])
        failures.push(`removed response ${responseCode} from ${key}`);
    }
  }
  const candidateSchemas = candidate.components?.schemas ?? {};
  for (const [name, schema] of Object.entries(baseline.components?.schemas ?? {})) {
    const replacement = candidateSchemas[name];
    if (!replacement) {
      failures.push(`removed schema ${name}`);
      continue;
    }
    const oldRequired = new Set(schema.required ?? []);
    const newRequired = new Set(replacement.required ?? []);
    for (const field of oldRequired) {
      if (!newRequired.has(field))
        failures.push(`removed required response field ${name}.${field}`);
    }
    const oldEnum = new Set(schema.enum ?? []);
    const newEnum = new Set(replacement.enum ?? []);
    for (const value of oldEnum) {
      if (!newEnum.has(value)) failures.push(`removed enum value ${name}.${value}`);
    }
  }
  return failures;
}

function main() {
  const schema = readJson(schemaPath);
  const baseline = readJson(baselinePath);
  const failures = [...lintSchema(schema), ...breakingChanges(baseline, schema)];
  if (failures.length) {
    process.stderr.write(`${failures.join("\n")}\n`);
    return 1;
  }
  if (process.argv.includes("--self-test")) {
    const broken = structuredClone(schema);
    delete broken.paths["/api/v1/identity/me"];
    if (!breakingChanges(schema, broken).some((item) => item.includes("removed operation"))) {
      process.stderr.write("breaking-change self-test did not detect a removed operation\n");
      return 1;
    }
  }
  process.stdout.write("OpenAPI lint and compatibility: PASS\n");
  return 0;
}

process.exitCode = main();
