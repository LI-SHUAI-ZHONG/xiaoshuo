import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

const repositoryRoot = fileURLToPath(new URL("../../", import.meta.url));
const compose = readFileSync(new URL("../../infra/compose.yaml", import.meta.url), "utf8");
const environmentExample = readFileSync(new URL("../../.env.example", import.meta.url), "utf8");
const powershellWrapper = readFileSync(new URL("../../scripts/infra.ps1", import.meta.url), "utf8");
const posixWrapper = readFileSync(new URL("../../scripts/infra.sh", import.meta.url), "utf8");

describe("local infrastructure contract", () => {
  it("pins every image and binds published ports to loopback", () => {
    expect(repositoryRoot).not.toBe("");
    expect(compose).toContain("pgvector/pgvector:0.8.6-pg17-bookworm");
    expect(compose).toContain("redis:7.4.11-bookworm");
    expect(compose).toContain("minio/minio:RELEASE.2025-09-07T16-13-09Z");
    expect(compose).toContain("minio/mc:RELEASE.2025-08-13T08-35-41Z");
    expect(compose).toContain("otel/opentelemetry-collector-contrib:0.136.0");
    expect(compose).toContain("jaegertracing/all-in-one:1.76.0");
    expect(compose).toContain("prom/prometheus:v3.6.0");
    expect(compose).not.toMatch(/image:\s+\S+:latest(?:\s|$)/u);
    expect(compose.match(/^\s+- "127\.0\.0\.1:/gmu)).toHaveLength(10);
    expect(compose).toContain('"127.0.0.1:${ACCOS_API_PORT:-8000}:8000"');
    expect(compose).toContain('"127.0.0.1:${ACCOS_STUDIO_PORT:-3000}:3000"');
  });

  it("declares persistent volumes and guarded credentials", () => {
    expect(compose).toContain("postgres-data:/var/lib/postgresql/data");
    expect(compose).toContain("redis-data:/data");
    expect(compose).toContain("minio-data:/data");
    expect(compose).toContain("prometheus-data:/prometheus");
    expect(compose).toContain("ACCOS_POSTGRES_PASSWORD:?");
    expect(compose).toContain("ACCOS_REDIS_PASSWORD:?");
    expect(compose).toContain("ACCOS_S3_SECRET_KEY:?");
  });

  it("documents every runtime setting in the tracked example", () => {
    for (const name of [
      "ACCOS_DATABASE_URL",
      "ACCOS_REDIS_URL",
      "ACCOS_S3_ENDPOINT",
      "ACCOS_S3_BUCKET",
      "ACCOS_S3_ACCESS_KEY",
      "ACCOS_S3_SECRET_KEY",
      "ACCOS_LOG_LEVEL",
      "ACCOS_REAL_PROVIDER_CALLS_ENABLED",
    ]) {
      expect(environmentExample).toMatch(new RegExp(`^${name}=`, "mu"));
    }
  });

  it("keeps normal shutdown non-destructive in both wrappers", () => {
    expect(powershellWrapper).toContain("@('down', '--remove-orphans')");
    expect(posixWrapper).toContain("compose down --remove-orphans");
    expect(powershellWrapper).not.toMatch(/down[^\r\n]*--volumes/u);
    expect(posixWrapper).not.toMatch(/compose down[^\r\n]*--volumes/u);
  });
});
