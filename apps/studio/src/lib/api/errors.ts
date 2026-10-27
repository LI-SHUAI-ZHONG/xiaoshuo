import type { components } from "@accos/api-client";

type ErrorEnvelope = components["schemas"]["ErrorEnvelope"];

export type ApiProblemKind =
  "unauthenticated" | "forbidden" | "not-found" | "conflict" | "offline" | "degraded" | "unknown";

export class ApiProblem extends Error {
  readonly code: string;
  readonly correlationId: string | null;
  readonly kind: ApiProblemKind;
  readonly status: number | null;

  constructor(options: {
    code: string;
    correlationId?: string;
    kind: ApiProblemKind;
    message: string;
    status?: number;
  }) {
    super(options.message);
    this.name = "ApiProblem";
    this.code = options.code;
    this.correlationId = options.correlationId ?? null;
    this.kind = options.kind;
    this.status = options.status ?? null;
  }
}

function isErrorEnvelope(value: unknown): value is ErrorEnvelope {
  if (typeof value !== "object" || value === null || !("error" in value)) return false;
  const error = value.error;
  return (
    typeof error === "object" &&
    error !== null &&
    "code" in error &&
    typeof error.code === "string" &&
    "message" in error &&
    typeof error.message === "string"
  );
}

function kindFor(code: string, status: number): ApiProblemKind {
  if (status === 401 || code === "authentication_required") return "unauthenticated";
  if (status === 403 || code === "permission_denied" || code === "scope_violation") {
    return "forbidden";
  }
  if (status === 404 || code === "resource_not_found") return "not-found";
  if (status === 409 || code.endsWith("conflict")) return "conflict";
  if (status === 503 || code === "dependency_unavailable") return "degraded";
  return "unknown";
}

export function mapApiError(error: unknown, response?: Response): ApiProblem {
  if (error instanceof ApiProblem) return error;
  if (isErrorEnvelope(error)) {
    return new ApiProblem({
      code: error.error.code,
      correlationId: error.error.correlation_id,
      kind: kindFor(error.error.code, response?.status ?? 500),
      message: error.error.message,
      ...(response ? { status: response.status } : {}),
    });
  }
  if (error instanceof TypeError || (typeof navigator !== "undefined" && !navigator.onLine)) {
    return new ApiProblem({
      code: "network_unavailable",
      kind: "offline",
      message: "无法连接到 ACCOS API。",
    });
  }
  return new ApiProblem({
    code: "unknown_error",
    kind: "unknown",
    message: "请求失败，请稍后重试。",
    ...(response ? { status: response.status } : {}),
  });
}

export function asApiProblem(error: unknown): ApiProblem {
  return error instanceof ApiProblem ? error : mapApiError(error);
}
