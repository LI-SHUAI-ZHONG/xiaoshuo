"""Environment-backed runtime configuration with safe diagnostics."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import urlsplit

from accos.kernel.auth_settings import AUTH_DEFAULTS, AuthSettings
from accos.kernel.errors import ConfigurationError
from accos.kernel.features import FeatureFlags
from accos.kernel.ids import parse_id

if TYPE_CHECKING:
    from collections.abc import Mapping
    from uuid import UUID

_DEFAULTS = {
    **AUTH_DEFAULTS,
    "ACCOS_ENV": "development",
    "ACCOS_LOG_LEVEL": "INFO",
    "ACCOS_S3_REGION": "us-east-1",
    "ACCOS_S3_USE_SSL": "false",
    "ACCOS_REAL_PROVIDER_CALLS_ENABLED": "false",
    "ACCOS_MODEL_MODE": "real",
    "ACCOS_LOCAL_MODEL_ENDPOINTS": "http://127.0.0.1:11434,http://localhost:11434",
    "ACCOS_EXTENSION_MULTIMODAL_IMAGE_ENABLED": "false",
    "ACCOS_EXTENSION_MULTIMODAL_AUDIO_ENABLED": "false",
    "ACCOS_EXTENSION_MULTIMODAL_VIDEO_ENABLED": "false",
    "ACCOS_EXTENSION_MULTIMODAL_THREE_D_ENABLED": "false",
    "ACCOS_EXTENSION_GRAPH_ENABLED": "false",
    "ACCOS_EXTENSION_COLLABORATION_ENABLED": "false",
    "ACCOS_EXTENSION_RIGHTS_ENABLED": "false",
    "ACCOS_EXTENSION_MARKETPLACE_ENABLED": "false",
    "ACCOS_EXTENSION_REPUTATION_ENABLED": "false",
    "ACCOS_EXTENSION_GROWTH_ENABLED": "false",
    "ACCOS_EXTENSION_KNOWLEDGE_NETWORK_ENABLED": "false",
    "ACCOS_API_HOST": "127.0.0.1",
    "ACCOS_API_PORT": "8000",
    "ACCOS_HEALTH_TIMEOUT_SECONDS": "2.0",
    "ACCOS_DB_POOL_SIZE": "5",
    "ACCOS_DB_MAX_OVERFLOW": "10",
    "ACCOS_DB_POOL_TIMEOUT_SECONDS": "30.0",
    "ACCOS_DB_POOL_RECYCLE_SECONDS": "1800",
    "ACCOS_AI_PROVIDER": "",
    "ACCOS_METRICS_ENABLED": "true",
    "ACCOS_OTLP_ENDPOINT": "",
    "ACCOS_OTLP_TIMEOUT_SECONDS": "1.0",
    "ACCOS_OTLP_EXPORT_INTERVAL_SECONDS": "5.0",
    "ACCOS_RUNTIME_HEARTBEAT_SECONDS": "5.0",
    "ACCOS_RUNTIME_HEARTBEAT_TTL_SECONDS": "20",
    "ACCOS_EXTERNAL_TIMEOUT_SECONDS": "5.0",
    "ACCOS_EXTERNAL_MAX_ATTEMPTS": "3",
    "ACCOS_EXTERNAL_BACKOFF_SECONDS": "0.1",
    "ACCOS_EXTERNAL_MAX_BACKOFF_SECONDS": "2.0",
    "ACCOS_EXTERNAL_CIRCUIT_FAILURE_THRESHOLD": "5",
    "ACCOS_EXTERNAL_CIRCUIT_COOLDOWN_SECONDS": "30.0",
    "ACCOS_EXTERNAL_CONCURRENCY_LIMIT": "16",
    "ACCOS_RATE_LIMIT_REQUESTS": "120",
    "ACCOS_RATE_LIMIT_WINDOW_SECONDS": "60.0",
    "ACCOS_DEV_IDENTITY_ENABLED": "false",
    "ACCOS_DEV_IDENTITY_TOKEN": "",
    "ACCOS_DEV_IDENTITY_ACTOR_ID": "",
    "ACCOS_DEV_IDENTITY_WORKSPACE_ID": "",
    "ACCOS_DEV_IDENTITY_APPROVER_TOKEN": "",
    "ACCOS_DEV_IDENTITY_APPROVER_ACTOR_ID": "",
}
_REQUIRED = (
    "ACCOS_DATABASE_URL",
    "ACCOS_REDIS_URL",
    "ACCOS_S3_ENDPOINT",
    "ACCOS_S3_BUCKET",
    "ACCOS_S3_ACCESS_KEY",
    "ACCOS_S3_SECRET_KEY",
)
_KNOWN_KEYS = frozenset((*_DEFAULTS, *_REQUIRED))
_TRUE_VALUES = frozenset({"1", "true", "yes", "on"})
_FALSE_VALUES = frozenset({"0", "false", "no", "off"})
_ENVIRONMENTS = frozenset({"development", "test", "production"})
_LOG_LEVELS = frozenset({"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"})
_MIN_QUOTED_LENGTH = 2
_MIN_PRODUCTION_SECRET_LENGTH = 16


@dataclass(frozen=True, slots=True)
class RequiredSettings:
    """Configuration without which API and worker must fail fast."""

    database_url: str
    redis_url: str
    s3_endpoint: str
    s3_bucket: str
    s3_access_key: str
    s3_secret_key: str


@dataclass(frozen=True, slots=True)
class OptionalSettings:
    """Non-secret runtime tuning with safe local defaults."""

    environment: str
    log_level: str
    s3_region: str
    s3_use_ssl: bool
    api_host: str
    api_port: int
    health_timeout_seconds: float
    db_pool_size: int
    db_max_overflow: int
    db_pool_timeout_seconds: float
    db_pool_recycle_seconds: int
    ai_provider: str | None


@dataclass(frozen=True, slots=True)
class SecuritySettings:
    """Explicit local identity settings; the credential is always secret."""

    dev_identity_enabled: bool
    dev_identity_token: str | None
    dev_identity_actor_id: UUID | None
    dev_identity_workspace_id: UUID | None
    dev_identity_approver_token: str | None = None
    dev_identity_approver_actor_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class ObservabilitySettings:
    """Optional telemetry export and cross-process runtime reporting settings."""

    metrics_enabled: bool = True
    otlp_endpoint: str | None = None
    otlp_timeout_seconds: float = 1.0
    otlp_export_interval_seconds: float = 5.0
    runtime_heartbeat_seconds: float = 5.0
    runtime_heartbeat_ttl_seconds: int = 20


@dataclass(frozen=True, slots=True)
class ResilienceSettings:
    """Central limits for external I/O and inbound request rate limiting."""

    timeout_seconds: float = 5.0
    max_attempts: int = 3
    backoff_seconds: float = 0.1
    max_backoff_seconds: float = 2.0
    circuit_failure_threshold: int = 5
    circuit_cooldown_seconds: float = 30.0
    concurrency_limit: int = 16
    rate_limit_requests: int = 120
    rate_limit_window_seconds: float = 60.0


@dataclass(frozen=True, slots=True)
class ModelSettings:
    """Provider mode and installation-controlled local endpoint allowlist."""

    mode: str = "real"
    local_endpoints: tuple[str, ...] = ("http://127.0.0.1:11434", "http://localhost:11434")


@dataclass(frozen=True, slots=True)
class RuntimeSettings:
    """Validated settings shared by the API and worker composition roots."""

    required: RequiredSettings
    optional: OptionalSettings
    features: FeatureFlags
    security: SecuritySettings
    observability: ObservabilitySettings = field(default_factory=ObservabilitySettings)
    resilience: ResilienceSettings = field(default_factory=ResilienceSettings)
    auth: AuthSettings = field(default_factory=AuthSettings)
    models: ModelSettings = field(default_factory=lambda: ModelSettings())

    def safe_summary(self) -> dict[str, object]:
        """Return grouped fields suitable for logs without credentials."""
        return {
            "required": {
                "database_url": "<redacted>",
                "redis_url": "<redacted>",
                "s3_endpoint": self.required.s3_endpoint,
                "s3_bucket": self.required.s3_bucket,
                "s3_access_key": "<redacted>",
                "s3_secret_key": "<redacted>",
            },
            "optional": {
                "environment": self.optional.environment,
                "log_level": self.optional.log_level,
                "s3_region": self.optional.s3_region,
                "s3_use_ssl": self.optional.s3_use_ssl,
                "api_host": self.optional.api_host,
                "api_port": self.optional.api_port,
                "health_timeout_seconds": self.optional.health_timeout_seconds,
                "db_pool_size": self.optional.db_pool_size,
                "db_max_overflow": self.optional.db_max_overflow,
                "db_pool_timeout_seconds": self.optional.db_pool_timeout_seconds,
                "db_pool_recycle_seconds": self.optional.db_pool_recycle_seconds,
                "ai_provider": self.optional.ai_provider or "<not-configured>",
            },
            "features": {
                "real_provider_calls_enabled": self.features.real_provider_calls_enabled,
                **self.features.extension_values(),
            },
            "security": {
                "dev_identity_enabled": self.security.dev_identity_enabled,
                "dev_identity_token": "<redacted>",
                "dev_identity_actor_configured": self.security.dev_identity_actor_id is not None,
                "dev_identity_workspace_configured": (
                    self.security.dev_identity_workspace_id is not None
                ),
                "dev_identity_approver_token": "<redacted>",
                "dev_identity_approver_configured": (
                    self.security.dev_identity_approver_actor_id is not None
                ),
            },
            "observability": {
                "metrics_enabled": self.observability.metrics_enabled,
                "otlp_configured": self.observability.otlp_endpoint is not None,
                "otlp_timeout_seconds": self.observability.otlp_timeout_seconds,
                "otlp_export_interval_seconds": (self.observability.otlp_export_interval_seconds),
                "runtime_heartbeat_seconds": self.observability.runtime_heartbeat_seconds,
                "runtime_heartbeat_ttl_seconds": (self.observability.runtime_heartbeat_ttl_seconds),
            },
            "resilience": {
                "timeout_seconds": self.resilience.timeout_seconds,
                "max_attempts": self.resilience.max_attempts,
                "backoff_seconds": self.resilience.backoff_seconds,
                "max_backoff_seconds": self.resilience.max_backoff_seconds,
                "circuit_failure_threshold": self.resilience.circuit_failure_threshold,
                "circuit_cooldown_seconds": self.resilience.circuit_cooldown_seconds,
                "concurrency_limit": self.resilience.concurrency_limit,
                "rate_limit_requests": self.resilience.rate_limit_requests,
                "rate_limit_window_seconds": self.resilience.rate_limit_window_seconds,
            },
        }


def load_settings(
    *,
    env_file: Path = Path(".env"),
    environ: Mapping[str, str] | None = None,
) -> RuntimeSettings:
    """Load defaults, .env, optional private identity file, then process overrides."""
    values = {**_DEFAULTS, **_read_env_file(env_file)}
    process_environment = os.environ if environ is None else environ
    identity_file = process_environment.get(
        "ACCOS_IDENTITY_CONFIG_FILE", values.get("ACCOS_IDENTITY_CONFIG_FILE", "")
    ).strip()
    if identity_file:
        private_path = Path(identity_file)
        if not private_path.is_absolute():
            private_path = env_file.resolve().parent / private_path
        if not private_path.is_file():
            raise ConfigurationError("The configured private identity file is unavailable.")
        private_values = _read_env_file(private_path)
        if set(private_values) - set(AUTH_DEFAULTS):
            raise ConfigurationError("The private identity file may contain only auth settings.")
        values.update(private_values)
    values.update(
        {key: process_environment[key] for key in _KNOWN_KEYS if key in process_environment}
    )

    missing = tuple(key for key in _REQUIRED if not values.get(key, "").strip())
    if missing:
        names = ", ".join(missing)
        raise ConfigurationError(f"Missing required environment variables: {names}")

    environment = values["ACCOS_ENV"].strip().lower()
    if environment not in _ENVIRONMENTS:
        raise ConfigurationError("ACCOS_ENV must be development, test, or production")
    log_level = values["ACCOS_LOG_LEVEL"].strip().upper()
    if log_level not in _LOG_LEVELS:
        raise ConfigurationError("ACCOS_LOG_LEVEL is invalid")
    security = _load_security_settings(values, environment)
    if environment == "production":
        _validate_production_credentials(values)

    required = RequiredSettings(
        database_url=_validated_url(
            "ACCOS_DATABASE_URL",
            values["ACCOS_DATABASE_URL"],
            {"postgresql", "postgresql+psycopg"},
        ),
        redis_url=_validated_url("ACCOS_REDIS_URL", values["ACCOS_REDIS_URL"], {"redis", "rediss"}),
        s3_endpoint=_validated_url(
            "ACCOS_S3_ENDPOINT", values["ACCOS_S3_ENDPOINT"], {"http", "https"}
        ),
        s3_bucket=values["ACCOS_S3_BUCKET"],
        s3_access_key=values["ACCOS_S3_ACCESS_KEY"],
        s3_secret_key=values["ACCOS_S3_SECRET_KEY"],
    )
    optional = OptionalSettings(
        environment=environment,
        log_level=log_level,
        s3_region=values["ACCOS_S3_REGION"],
        s3_use_ssl=_parse_boolean("ACCOS_S3_USE_SSL", values["ACCOS_S3_USE_SSL"]),
        api_host=values["ACCOS_API_HOST"],
        api_port=_parse_positive_int("ACCOS_API_PORT", values["ACCOS_API_PORT"], maximum=65535),
        health_timeout_seconds=_parse_positive_float(
            "ACCOS_HEALTH_TIMEOUT_SECONDS", values["ACCOS_HEALTH_TIMEOUT_SECONDS"]
        ),
        db_pool_size=_parse_positive_int(
            "ACCOS_DB_POOL_SIZE", values["ACCOS_DB_POOL_SIZE"], maximum=100
        ),
        db_max_overflow=_parse_non_negative_int(
            "ACCOS_DB_MAX_OVERFLOW", values["ACCOS_DB_MAX_OVERFLOW"], maximum=100
        ),
        db_pool_timeout_seconds=_parse_positive_float(
            "ACCOS_DB_POOL_TIMEOUT_SECONDS", values["ACCOS_DB_POOL_TIMEOUT_SECONDS"]
        ),
        db_pool_recycle_seconds=_parse_positive_int(
            "ACCOS_DB_POOL_RECYCLE_SECONDS",
            values["ACCOS_DB_POOL_RECYCLE_SECONDS"],
            maximum=86400,
        ),
        ai_provider=values["ACCOS_AI_PROVIDER"].strip() or None,
    )
    model_mode = values["ACCOS_MODEL_MODE"].strip()
    if model_mode not in {"real", "test", "demo"} or (environment == "production" and model_mode != "real"):
        raise ConfigurationError("ACCOS_MODEL_MODE must be real; test/demo are explicit non-production modes.")
    local_endpoints = tuple(value.strip().rstrip("/") for value in values["ACCOS_LOCAL_MODEL_ENDPOINTS"].split(",") if value.strip())
    for endpoint in local_endpoints:
        _validated_url("ACCOS_LOCAL_MODEL_ENDPOINTS", endpoint, {"http", "https"})
        parsed = urlsplit(endpoint)
        if parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ConfigurationError("Local model allowlist must contain credential-free endpoints.")
    return RuntimeSettings(
        required=required,
        optional=optional,
        features=FeatureFlags(
            real_provider_calls_enabled=_parse_boolean(
                "ACCOS_REAL_PROVIDER_CALLS_ENABLED",
                values["ACCOS_REAL_PROVIDER_CALLS_ENABLED"],
            ),
            multimodal_image_enabled=_parse_boolean(
                "ACCOS_EXTENSION_MULTIMODAL_IMAGE_ENABLED",
                values["ACCOS_EXTENSION_MULTIMODAL_IMAGE_ENABLED"],
            ),
            multimodal_audio_enabled=_parse_boolean(
                "ACCOS_EXTENSION_MULTIMODAL_AUDIO_ENABLED",
                values["ACCOS_EXTENSION_MULTIMODAL_AUDIO_ENABLED"],
            ),
            multimodal_video_enabled=_parse_boolean(
                "ACCOS_EXTENSION_MULTIMODAL_VIDEO_ENABLED",
                values["ACCOS_EXTENSION_MULTIMODAL_VIDEO_ENABLED"],
            ),
            multimodal_three_d_enabled=_parse_boolean(
                "ACCOS_EXTENSION_MULTIMODAL_THREE_D_ENABLED",
                values["ACCOS_EXTENSION_MULTIMODAL_THREE_D_ENABLED"],
            ),
            graph_enabled=_parse_boolean(
                "ACCOS_EXTENSION_GRAPH_ENABLED",
                values["ACCOS_EXTENSION_GRAPH_ENABLED"],
            ),
            collaboration_enabled=_parse_boolean(
                "ACCOS_EXTENSION_COLLABORATION_ENABLED",
                values["ACCOS_EXTENSION_COLLABORATION_ENABLED"],
            ),
            rights_enabled=_parse_boolean(
                "ACCOS_EXTENSION_RIGHTS_ENABLED",
                values["ACCOS_EXTENSION_RIGHTS_ENABLED"],
            ),
            marketplace_enabled=_parse_boolean(
                "ACCOS_EXTENSION_MARKETPLACE_ENABLED",
                values["ACCOS_EXTENSION_MARKETPLACE_ENABLED"],
            ),
            reputation_enabled=_parse_boolean(
                "ACCOS_EXTENSION_REPUTATION_ENABLED",
                values["ACCOS_EXTENSION_REPUTATION_ENABLED"],
            ),
            growth_enabled=_parse_boolean(
                "ACCOS_EXTENSION_GROWTH_ENABLED",
                values["ACCOS_EXTENSION_GROWTH_ENABLED"],
            ),
            knowledge_network_enabled=_parse_boolean(
                "ACCOS_EXTENSION_KNOWLEDGE_NETWORK_ENABLED",
                values["ACCOS_EXTENSION_KNOWLEDGE_NETWORK_ENABLED"],
            ),
        ),
        security=security,
        auth=AuthSettings.from_values(values),
        models=ModelSettings(mode=model_mode, local_endpoints=local_endpoints),
        observability=ObservabilitySettings(
            metrics_enabled=_parse_boolean(
                "ACCOS_METRICS_ENABLED", values["ACCOS_METRICS_ENABLED"]
            ),
            otlp_endpoint=_optional_http_url("ACCOS_OTLP_ENDPOINT", values["ACCOS_OTLP_ENDPOINT"]),
            otlp_timeout_seconds=_parse_positive_float(
                "ACCOS_OTLP_TIMEOUT_SECONDS", values["ACCOS_OTLP_TIMEOUT_SECONDS"]
            ),
            otlp_export_interval_seconds=_parse_positive_float(
                "ACCOS_OTLP_EXPORT_INTERVAL_SECONDS",
                values["ACCOS_OTLP_EXPORT_INTERVAL_SECONDS"],
            ),
            runtime_heartbeat_seconds=_parse_positive_float(
                "ACCOS_RUNTIME_HEARTBEAT_SECONDS",
                values["ACCOS_RUNTIME_HEARTBEAT_SECONDS"],
            ),
            runtime_heartbeat_ttl_seconds=_parse_positive_int(
                "ACCOS_RUNTIME_HEARTBEAT_TTL_SECONDS",
                values["ACCOS_RUNTIME_HEARTBEAT_TTL_SECONDS"],
                maximum=3600,
            ),
        ),
        resilience=ResilienceSettings(
            timeout_seconds=_parse_positive_float(
                "ACCOS_EXTERNAL_TIMEOUT_SECONDS", values["ACCOS_EXTERNAL_TIMEOUT_SECONDS"]
            ),
            max_attempts=_parse_positive_int(
                "ACCOS_EXTERNAL_MAX_ATTEMPTS",
                values["ACCOS_EXTERNAL_MAX_ATTEMPTS"],
                maximum=10,
            ),
            backoff_seconds=_parse_non_negative_float(
                "ACCOS_EXTERNAL_BACKOFF_SECONDS", values["ACCOS_EXTERNAL_BACKOFF_SECONDS"]
            ),
            max_backoff_seconds=_parse_positive_float(
                "ACCOS_EXTERNAL_MAX_BACKOFF_SECONDS",
                values["ACCOS_EXTERNAL_MAX_BACKOFF_SECONDS"],
            ),
            circuit_failure_threshold=_parse_positive_int(
                "ACCOS_EXTERNAL_CIRCUIT_FAILURE_THRESHOLD",
                values["ACCOS_EXTERNAL_CIRCUIT_FAILURE_THRESHOLD"],
                maximum=100,
            ),
            circuit_cooldown_seconds=_parse_positive_float(
                "ACCOS_EXTERNAL_CIRCUIT_COOLDOWN_SECONDS",
                values["ACCOS_EXTERNAL_CIRCUIT_COOLDOWN_SECONDS"],
            ),
            concurrency_limit=_parse_positive_int(
                "ACCOS_EXTERNAL_CONCURRENCY_LIMIT",
                values["ACCOS_EXTERNAL_CONCURRENCY_LIMIT"],
                maximum=1000,
            ),
            rate_limit_requests=_parse_positive_int(
                "ACCOS_RATE_LIMIT_REQUESTS",
                values["ACCOS_RATE_LIMIT_REQUESTS"],
                maximum=1_000_000,
            ),
            rate_limit_window_seconds=_parse_positive_float(
                "ACCOS_RATE_LIMIT_WINDOW_SECONDS",
                values["ACCOS_RATE_LIMIT_WINDOW_SECONDS"],
            ),
        ),
    )


def _read_env_file(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}

    values: dict[str, str] = {}
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line.removeprefix("export ").lstrip()
        key, separator, raw_value = line.partition("=")
        key = key.strip()
        if not separator or not key:
            raise ConfigurationError(f"Invalid .env entry at line {line_number}")
        if key not in _KNOWN_KEYS:
            continue
        value = raw_value.strip()
        if len(value) >= _MIN_QUOTED_LENGTH and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        values[key] = value
    return values


def _validated_url(name: str, value: str, allowed_schemes: set[str]) -> str:
    parsed = urlsplit(value)
    if parsed.scheme not in allowed_schemes or parsed.hostname is None:
        raise ConfigurationError(f"{name} has an unsupported or missing URL scheme or host")
    return value


def _parse_boolean(name: str, value: str) -> bool:
    normalized = value.strip().lower()
    if normalized in _TRUE_VALUES:
        return True
    if normalized in _FALSE_VALUES:
        return False
    raise ConfigurationError(f"{name} must be a boolean")


def _parse_positive_int(name: str, value: str, *, maximum: int) -> int:
    try:
        parsed = int(value)
    except ValueError as error:
        raise ConfigurationError(f"{name} must be a positive integer") from error
    if not 1 <= parsed <= maximum:
        raise ConfigurationError(f"{name} must be between 1 and {maximum}")
    return parsed


def _parse_positive_float(name: str, value: str) -> float:
    try:
        parsed = float(value)
    except ValueError as error:
        raise ConfigurationError(f"{name} must be a positive number") from error
    if parsed <= 0:
        raise ConfigurationError(f"{name} must be a positive number")
    return parsed


def _parse_non_negative_int(name: str, value: str, *, maximum: int) -> int:
    try:
        parsed = int(value)
    except ValueError as error:
        raise ConfigurationError(f"{name} must be a non-negative integer") from error
    if not 0 <= parsed <= maximum:
        raise ConfigurationError(f"{name} must be between 0 and {maximum}")
    return parsed


def _parse_non_negative_float(name: str, value: str) -> float:
    try:
        parsed = float(value)
    except ValueError as error:
        raise ConfigurationError(f"{name} must be a non-negative number") from error
    if parsed < 0:
        raise ConfigurationError(f"{name} must be a non-negative number")
    return parsed


def _optional_http_url(name: str, value: str) -> str | None:
    normalized = value.strip().rstrip("/")
    if not normalized:
        return None
    parsed = urlsplit(normalized)
    if (
        parsed.scheme not in {"http", "https"}
        or parsed.hostname is None
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
    ):
        raise ConfigurationError(f"{name} must be a credential-free HTTP(S) endpoint")
    return normalized


def _validate_production_credentials(values: Mapping[str, str]) -> None:
    credentials = (
        ("ACCOS_DATABASE_URL", urlsplit(values["ACCOS_DATABASE_URL"]).password or ""),
        ("ACCOS_REDIS_URL", urlsplit(values["ACCOS_REDIS_URL"]).password or ""),
        ("ACCOS_S3_ACCESS_KEY", values["ACCOS_S3_ACCESS_KEY"]),
        ("ACCOS_S3_SECRET_KEY", values["ACCOS_S3_SECRET_KEY"]),
    )
    weak_names = tuple(
        name
        for name, value in credentials
        if len(value) < _MIN_PRODUCTION_SECRET_LENGTH or "replace-with-" in value.lower()
    )
    if weak_names:
        raise ConfigurationError(
            "Production configuration rejects weak or placeholder credentials for: "
            + ", ".join(weak_names)
        )


def _load_security_settings(values: Mapping[str, str], environment: str) -> SecuritySettings:
    enabled = _parse_boolean("ACCOS_DEV_IDENTITY_ENABLED", values["ACCOS_DEV_IDENTITY_ENABLED"])
    if environment == "production" and enabled:
        raise ConfigurationError("Development identity cannot be enabled in production.")
    if not enabled:
        return SecuritySettings(
            dev_identity_enabled=False,
            dev_identity_token=None,
            dev_identity_actor_id=None,
            dev_identity_workspace_id=None,
            dev_identity_approver_token=None,
            dev_identity_approver_actor_id=None,
        )

    token = values["ACCOS_DEV_IDENTITY_TOKEN"].strip()
    actor_id = values["ACCOS_DEV_IDENTITY_ACTOR_ID"].strip()
    workspace_id = values["ACCOS_DEV_IDENTITY_WORKSPACE_ID"].strip()
    missing = tuple(
        name
        for name, value in (
            ("ACCOS_DEV_IDENTITY_TOKEN", token),
            ("ACCOS_DEV_IDENTITY_ACTOR_ID", actor_id),
            ("ACCOS_DEV_IDENTITY_WORKSPACE_ID", workspace_id),
        )
        if not value
    )
    if missing:
        raise ConfigurationError(
            "Development identity requires explicit configuration for: " + ", ".join(missing)
        )
    if len(token) < _MIN_PRODUCTION_SECRET_LENGTH:
        raise ConfigurationError("ACCOS_DEV_IDENTITY_TOKEN must be at least 16 characters")
    try:
        parsed_actor = parse_id(actor_id)
        parsed_workspace = parse_id(workspace_id)
    except ValueError as error:
        raise ConfigurationError(
            "Development identity IDs must be canonical UUIDv4 values"
        ) from error
    approver_token = values["ACCOS_DEV_IDENTITY_APPROVER_TOKEN"].strip()
    approver_actor_id = values["ACCOS_DEV_IDENTITY_APPROVER_ACTOR_ID"].strip()
    if bool(approver_token) != bool(approver_actor_id):
        raise ConfigurationError(
            "Development approver requires both ACCOS_DEV_IDENTITY_APPROVER_TOKEN "
            "and ACCOS_DEV_IDENTITY_APPROVER_ACTOR_ID"
        )
    parsed_approver = None
    if approver_token:
        if len(approver_token) < _MIN_PRODUCTION_SECRET_LENGTH:
            raise ConfigurationError(
                "ACCOS_DEV_IDENTITY_APPROVER_TOKEN must be at least 16 characters"
            )
        if approver_token == token:
            raise ConfigurationError("Development identity and approver tokens must differ")
        try:
            parsed_approver = parse_id(approver_actor_id)
        except ValueError as error:
            raise ConfigurationError(
                "Development approver ID must be a canonical UUIDv4 value"
            ) from error
        if parsed_approver == parsed_actor:
            raise ConfigurationError("Development identity and approver actor IDs must differ")
    return SecuritySettings(
        dev_identity_enabled=True,
        dev_identity_token=token,
        dev_identity_actor_id=parsed_actor,
        dev_identity_workspace_id=parsed_workspace,
        dev_identity_approver_token=approver_token or None,
        dev_identity_approver_actor_id=parsed_approver,
    )
