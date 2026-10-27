from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from accos.kernel import ConfigurationError, load_settings

if TYPE_CHECKING:
    from pathlib import Path

_REDACTED = "<redacted>"


def complete_environment() -> dict[str, str]:
    return {
        "ACCOS_DATABASE_URL": (
            "postgresql+psycopg://fixture:fixture-database-secret@127.0.0.1/fixture"
        ),
        "ACCOS_REDIS_URL": "redis://:fixture-redis-secret@127.0.0.1/0",
        "ACCOS_S3_ENDPOINT": "http://127.0.0.1:9000",
        "ACCOS_S3_BUCKET": "fixture-project",
        "ACCOS_S3_ACCESS_KEY": "fixture-access-key",
        "ACCOS_S3_SECRET_KEY": "fixture-object-secret",
    }


def development_identity_environment() -> dict[str, str]:
    return {
        "ACCOS_DEV_IDENTITY_ENABLED": "true",
        "ACCOS_DEV_IDENTITY_TOKEN": "fixture-local-secret-token",
        "ACCOS_DEV_IDENTITY_ACTOR_ID": "11111111-1111-4111-8111-111111111111",
        "ACCOS_DEV_IDENTITY_WORKSPACE_ID": "22222222-2222-4222-8222-222222222222",
    }


def test_loads_grouped_defaults_file_and_process_overrides_with_safe_summary(
    tmp_path: Path,
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            (
                "# fixture configuration",
                "",
                "ACCOS_DATABASE_URL=postgresql://fixture:file-database-secret@db/fixture",
                "ACCOS_REDIS_URL=redis://:file-redis-secret@redis/0",
                "ACCOS_S3_ENDPOINT=http://minio:9000",
                "ACCOS_S3_BUCKET=fixture-document",
                'export ACCOS_S3_ACCESS_KEY="fixture-file-access"',
                "ACCOS_S3_SECRET_KEY='fixture-file-secret'",
                "ACCOS_S3_USE_SSL=yes",
                "IGNORED_SETTING=fixture-ignored",
            )
        ),
        encoding="utf-8",
    )
    process_environment = {
        "ACCOS_LOG_LEVEL": "debug",
        "ACCOS_S3_BUCKET": "fixture-project",
        "ACCOS_REAL_PROVIDER_CALLS_ENABLED": "on",
        "ACCOS_AI_PROVIDER": "fixture-provider",
        "ACCOS_EXTENSION_GRAPH_ENABLED": "true",
        "ACCOS_EXTENSION_RIGHTS_ENABLED": "1",
        "ACCOS_METRICS_ENABLED": "off",
        "ACCOS_OTLP_ENDPOINT": "http://collector:4318/",
        "ACCOS_OTLP_TIMEOUT_SECONDS": "0.5",
        "ACCOS_OTLP_EXPORT_INTERVAL_SECONDS": "2",
        "ACCOS_RUNTIME_HEARTBEAT_SECONDS": "3",
        "ACCOS_RUNTIME_HEARTBEAT_TTL_SECONDS": "15",
        "ACCOS_EXTERNAL_TIMEOUT_SECONDS": "4",
        "ACCOS_EXTERNAL_MAX_ATTEMPTS": "2",
        "ACCOS_EXTERNAL_BACKOFF_SECONDS": "0",
        "ACCOS_EXTERNAL_MAX_BACKOFF_SECONDS": "1",
        "ACCOS_EXTERNAL_CIRCUIT_FAILURE_THRESHOLD": "3",
        "ACCOS_EXTERNAL_CIRCUIT_COOLDOWN_SECONDS": "10",
        "ACCOS_EXTERNAL_CONCURRENCY_LIMIT": "8",
        "ACCOS_RATE_LIMIT_REQUESTS": "50",
        "ACCOS_RATE_LIMIT_WINDOW_SECONDS": "30",
    }

    settings = load_settings(env_file=env_file, environ=process_environment)

    assert settings.optional.environment == "development"
    assert settings.optional.log_level == "DEBUG"
    assert settings.required.database_url == "postgresql://fixture:file-database-secret@db/fixture"
    assert settings.required.redis_url == "redis://:file-redis-secret@redis/0"
    assert settings.required.s3_endpoint == "http://minio:9000"
    assert settings.required.s3_bucket == "fixture-project"
    assert settings.required.s3_access_key == "fixture-file-access"
    assert settings.required.s3_secret_key == "fixture-file-secret"
    assert settings.optional.s3_region == "us-east-1"
    assert settings.optional.s3_use_ssl is True
    assert settings.optional.api_host == "127.0.0.1"
    assert settings.optional.api_port == 8000
    assert settings.optional.health_timeout_seconds == 2.0
    assert settings.optional.db_pool_size == 5
    assert settings.optional.db_max_overflow == 10
    assert settings.optional.db_pool_timeout_seconds == 30.0
    assert settings.optional.db_pool_recycle_seconds == 1800
    assert settings.optional.ai_provider == "fixture-provider"
    assert settings.features.real_provider_calls_enabled is True
    assert settings.features.graph_enabled is True
    assert settings.features.rights_enabled is True
    assert settings.features.extension_values()["collaboration"] is False
    assert settings.security.dev_identity_enabled is False
    assert settings.observability.metrics_enabled is False
    assert settings.observability.otlp_endpoint == "http://collector:4318"
    assert settings.observability.otlp_timeout_seconds == 0.5
    assert settings.observability.otlp_export_interval_seconds == 2
    assert settings.observability.runtime_heartbeat_seconds == 3
    assert settings.observability.runtime_heartbeat_ttl_seconds == 15
    assert settings.resilience.timeout_seconds == 4
    assert settings.resilience.max_attempts == 2
    assert settings.resilience.backoff_seconds == 0
    assert settings.resilience.max_backoff_seconds == 1
    assert settings.resilience.circuit_failure_threshold == 3
    assert settings.resilience.circuit_cooldown_seconds == 10
    assert settings.resilience.concurrency_limit == 8
    assert settings.resilience.rate_limit_requests == 50
    assert settings.resilience.rate_limit_window_seconds == 30
    safe_summary = settings.safe_summary()
    assert safe_summary["required"] == {
        "database_url": _REDACTED,
        "redis_url": _REDACTED,
        "s3_endpoint": "http://minio:9000",
        "s3_bucket": "fixture-project",
        "s3_access_key": _REDACTED,
        "s3_secret_key": _REDACTED,
    }
    for hidden_value in (
        settings.required.database_url,
        settings.required.redis_url,
        settings.required.s3_access_key,
        settings.required.s3_secret_key,
    ):
        assert hidden_value not in repr(safe_summary)
    assert safe_summary["security"] == {
        "dev_identity_enabled": False,
        "dev_identity_token": _REDACTED,
        "dev_identity_actor_configured": False,
        "dev_identity_workspace_configured": False,
        "dev_identity_approver_token": _REDACTED,
        "dev_identity_approver_configured": False,
    }
    assert safe_summary["observability"] == {
        "metrics_enabled": False,
        "otlp_configured": True,
        "otlp_timeout_seconds": 0.5,
        "otlp_export_interval_seconds": 2.0,
        "runtime_heartbeat_seconds": 3.0,
        "runtime_heartbeat_ttl_seconds": 15,
    }
    assert safe_summary["resilience"] == {
        "timeout_seconds": 4.0,
        "max_attempts": 2,
        "backoff_seconds": 0.0,
        "max_backoff_seconds": 1.0,
        "circuit_failure_threshold": 3,
        "circuit_cooldown_seconds": 10.0,
        "concurrency_limit": 8,
        "rate_limit_requests": 50,
        "rate_limit_window_seconds": 30.0,
    }


def test_process_environment_is_used_when_no_mapping_is_supplied(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    for name, value in complete_environment().items():
        monkeypatch.setenv(name, value)
    monkeypatch.setenv("ACCOS_S3_USE_SSL", "0")
    monkeypatch.setenv("ACCOS_REAL_PROVIDER_CALLS_ENABLED", "off")
    monkeypatch.setenv("ACCOS_AI_PROVIDER", " ")

    settings = load_settings(env_file=tmp_path / "missing.env")

    assert settings.optional.s3_use_ssl is False
    assert settings.optional.ai_provider is None
    assert settings.features.real_provider_calls_enabled is False
    assert settings.observability.otlp_endpoint is None


def test_missing_required_values_fails_without_values(tmp_path: Path) -> None:
    with pytest.raises(ConfigurationError) as error:
        load_settings(env_file=tmp_path / "missing.env", environ={})

    message = str(error.value)
    assert "ACCOS_DATABASE_URL" in message
    assert "ACCOS_S3_SECRET_KEY" in message
    assert "secret@" not in message


@pytest.mark.parametrize("entry", ["missing-separator", "=missing-name"])
def test_invalid_env_lines_fail_without_echoing_content(tmp_path: Path, entry: str) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(entry, encoding="utf-8")

    with pytest.raises(ConfigurationError, match=r"Invalid \.env entry at line 1") as error:
        load_settings(env_file=env_file, environ=complete_environment())

    assert entry not in str(error.value)


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("ACCOS_DATABASE_URL", "mysql://fixture"),
        ("ACCOS_REDIS_URL", "http://fixture"),
        ("ACCOS_S3_ENDPOINT", "ftp://fixture"),
        ("ACCOS_S3_ENDPOINT", "http:///missing-host"),
    ],
)
def test_rejects_unsupported_or_incomplete_urls(tmp_path: Path, name: str, value: str) -> None:
    environment = complete_environment()
    environment[name] = value

    with pytest.raises(ConfigurationError, match=f"^{name} has an unsupported"):
        load_settings(env_file=tmp_path / "missing.env", environ=environment)


@pytest.mark.parametrize(
    "name",
    [
        "ACCOS_S3_USE_SSL",
        "ACCOS_REAL_PROVIDER_CALLS_ENABLED",
        "ACCOS_EXTENSION_GRAPH_ENABLED",
        "ACCOS_METRICS_ENABLED",
    ],
)
def test_rejects_invalid_boolean_values(tmp_path: Path, name: str) -> None:
    environment = complete_environment()
    environment[name] = "not-a-boolean"

    with pytest.raises(ConfigurationError, match=f"^{name} must be a boolean$"):
        load_settings(env_file=tmp_path / "missing.env", environ=environment)


@pytest.mark.parametrize(
    ("name", "value", "message"),
    [
        ("ACCOS_ENV", "fixture", "ACCOS_ENV must be"),
        ("ACCOS_LOG_LEVEL", "verbose", "ACCOS_LOG_LEVEL is invalid"),
        ("ACCOS_API_PORT", "fixture", "must be a positive integer"),
        ("ACCOS_API_PORT", "0", "must be between"),
        ("ACCOS_API_PORT", "65536", "must be between"),
        ("ACCOS_HEALTH_TIMEOUT_SECONDS", "fixture", "must be a positive number"),
        ("ACCOS_HEALTH_TIMEOUT_SECONDS", "0", "must be a positive number"),
        ("ACCOS_DB_POOL_SIZE", "fixture", "must be a positive integer"),
        ("ACCOS_DB_POOL_SIZE", "0", "must be between"),
        ("ACCOS_DB_MAX_OVERFLOW", "fixture", "must be a non-negative integer"),
        ("ACCOS_DB_MAX_OVERFLOW", "-1", "must be between"),
        ("ACCOS_DB_POOL_TIMEOUT_SECONDS", "fixture", "must be a positive number"),
        ("ACCOS_DB_POOL_TIMEOUT_SECONDS", "0", "must be a positive number"),
        ("ACCOS_DB_POOL_RECYCLE_SECONDS", "0", "must be between"),
        ("ACCOS_OTLP_TIMEOUT_SECONDS", "0", "must be a positive number"),
        ("ACCOS_OTLP_EXPORT_INTERVAL_SECONDS", "bad", "must be a positive number"),
        ("ACCOS_RUNTIME_HEARTBEAT_SECONDS", "0", "must be a positive number"),
        ("ACCOS_RUNTIME_HEARTBEAT_TTL_SECONDS", "0", "must be between"),
        ("ACCOS_EXTERNAL_TIMEOUT_SECONDS", "0", "must be a positive number"),
        ("ACCOS_EXTERNAL_MAX_ATTEMPTS", "0", "must be between"),
        ("ACCOS_EXTERNAL_BACKOFF_SECONDS", "bad", "must be a non-negative number"),
        ("ACCOS_EXTERNAL_BACKOFF_SECONDS", "-1", "must be a non-negative number"),
        ("ACCOS_EXTERNAL_MAX_BACKOFF_SECONDS", "0", "must be a positive number"),
        ("ACCOS_EXTERNAL_CIRCUIT_FAILURE_THRESHOLD", "0", "must be between"),
        ("ACCOS_EXTERNAL_CIRCUIT_COOLDOWN_SECONDS", "0", "must be a positive number"),
        ("ACCOS_EXTERNAL_CONCURRENCY_LIMIT", "0", "must be between"),
        ("ACCOS_RATE_LIMIT_REQUESTS", "0", "must be between"),
        ("ACCOS_RATE_LIMIT_WINDOW_SECONDS", "0", "must be a positive number"),
    ],
)
def test_rejects_invalid_runtime_options(
    tmp_path: Path, name: str, value: str, message: str
) -> None:
    environment = complete_environment()
    environment[name] = value

    with pytest.raises(ConfigurationError, match=message):
        load_settings(env_file=tmp_path / "missing.env", environ=environment)


def test_production_accepts_explicit_strong_credentials(tmp_path: Path) -> None:
    environment = complete_environment()
    environment["ACCOS_ENV"] = "production"

    settings = load_settings(env_file=tmp_path / "missing.env", environ=environment)

    assert settings.optional.environment == "production"


@pytest.mark.parametrize(
    "value",
    [
        "ftp://collector",
        "http:///missing-host",
        "http://user:password@collector",
        "http://collector?query=yes",
        "http://collector#fragment",
    ],
)
def test_rejects_unsafe_otlp_endpoints(tmp_path: Path, value: str) -> None:
    environment = complete_environment()
    environment["ACCOS_OTLP_ENDPOINT"] = value

    with pytest.raises(ConfigurationError, match="credential-free HTTP"):
        load_settings(env_file=tmp_path / "missing.env", environ=environment)


def test_explicit_development_identity_configuration_is_loaded_and_redacted(
    tmp_path: Path,
) -> None:
    environment = complete_environment()
    environment.update(development_identity_environment())

    settings = load_settings(env_file=tmp_path / "missing.env", environ=environment)

    assert settings.security.dev_identity_enabled is True
    assert (
        str(settings.security.dev_identity_actor_id) == environment["ACCOS_DEV_IDENTITY_ACTOR_ID"]
    )
    assert (
        str(settings.security.dev_identity_workspace_id)
        == environment["ACCOS_DEV_IDENTITY_WORKSPACE_ID"]
    )
    assert environment["ACCOS_DEV_IDENTITY_TOKEN"] not in repr(settings.safe_summary())


def test_explicit_development_approver_is_loaded_and_redacted(tmp_path: Path) -> None:
    environment = complete_environment()
    environment.update(development_identity_environment())
    environment.update(
        {
            "ACCOS_DEV_IDENTITY_APPROVER_TOKEN": "fixture-local-approver-token",
            "ACCOS_DEV_IDENTITY_APPROVER_ACTOR_ID": ("33333333-3333-4333-8333-333333333333"),
        }
    )

    settings = load_settings(env_file=tmp_path / "missing.env", environ=environment)

    assert (
        str(settings.security.dev_identity_approver_actor_id)
        == (environment["ACCOS_DEV_IDENTITY_APPROVER_ACTOR_ID"])
    )
    summary = repr(settings.safe_summary())
    assert environment["ACCOS_DEV_IDENTITY_APPROVER_TOKEN"] not in summary
    assert settings.safe_summary()["security"] == {
        "dev_identity_enabled": True,
        "dev_identity_token": "<redacted>",
        "dev_identity_actor_configured": True,
        "dev_identity_workspace_configured": True,
        "dev_identity_approver_token": "<redacted>",
        "dev_identity_approver_configured": True,
    }


@pytest.mark.parametrize(
    ("updates", "message"),
    [
        (
            {"ACCOS_ENV": "production", "ACCOS_DEV_IDENTITY_ENABLED": "true"},
            "cannot be enabled in production",
        ),
        (
            {"ACCOS_DEV_IDENTITY_ENABLED": "true"},
            "requires explicit configuration",
        ),
        (
            {
                "ACCOS_DEV_IDENTITY_ENABLED": "true",
                "ACCOS_DEV_IDENTITY_TOKEN": "short",
                "ACCOS_DEV_IDENTITY_ACTOR_ID": "11111111-1111-4111-8111-111111111111",
                "ACCOS_DEV_IDENTITY_WORKSPACE_ID": "22222222-2222-4222-8222-222222222222",
            },
            "must be at least 16 characters",
        ),
        (
            {
                "ACCOS_DEV_IDENTITY_ENABLED": "true",
                "ACCOS_DEV_IDENTITY_TOKEN": "fixture-local-secret-token",
                "ACCOS_DEV_IDENTITY_ACTOR_ID": "invalid",
                "ACCOS_DEV_IDENTITY_WORKSPACE_ID": "22222222-2222-4222-8222-222222222222",
            },
            "canonical UUIDv4",
        ),
        (
            {
                **development_identity_environment(),
                "ACCOS_DEV_IDENTITY_APPROVER_TOKEN": "fixture-local-approver-token",
            },
            "requires both",
        ),
        (
            {
                **development_identity_environment(),
                "ACCOS_DEV_IDENTITY_APPROVER_TOKEN": "short",
                "ACCOS_DEV_IDENTITY_APPROVER_ACTOR_ID": ("33333333-3333-4333-8333-333333333333"),
            },
            "APPROVER_TOKEN must be at least 16 characters",
        ),
        (
            {
                **development_identity_environment(),
                "ACCOS_DEV_IDENTITY_APPROVER_TOKEN": "fixture-local-approver-token",
                "ACCOS_DEV_IDENTITY_APPROVER_ACTOR_ID": "invalid",
            },
            "approver ID must be a canonical UUIDv4",
        ),
        (
            {
                **development_identity_environment(),
                "ACCOS_DEV_IDENTITY_APPROVER_TOKEN": "fixture-local-secret-token",
                "ACCOS_DEV_IDENTITY_APPROVER_ACTOR_ID": ("33333333-3333-4333-8333-333333333333"),
            },
            "identity and approver tokens must differ",
        ),
        (
            {
                **development_identity_environment(),
                "ACCOS_DEV_IDENTITY_APPROVER_TOKEN": "fixture-local-approver-token",
                "ACCOS_DEV_IDENTITY_APPROVER_ACTOR_ID": ("11111111-1111-4111-8111-111111111111"),
            },
            "identity and approver actor IDs must differ",
        ),
    ],
)
def test_development_identity_configuration_fails_closed(
    tmp_path: Path, updates: dict[str, str], message: str
) -> None:
    environment = complete_environment()
    environment.update(updates)

    with pytest.raises(ConfigurationError, match=message):
        load_settings(env_file=tmp_path / "missing.env", environ=environment)


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("ACCOS_S3_ACCESS_KEY", "short"),
        ("ACCOS_S3_SECRET_KEY", "replace-with-local-secret"),
        (
            "ACCOS_DATABASE_URL",
            "postgresql+psycopg://fixture:short@127.0.0.1/fixture",
        ),
        (
            "ACCOS_REDIS_URL",
            "redis://:replace-with-local-redis-password@127.0.0.1/0",
        ),
    ],
)
def test_production_rejects_weak_credentials_without_echoing_values(
    tmp_path: Path, name: str, value: str
) -> None:
    environment = complete_environment()
    environment["ACCOS_ENV"] = "production"
    environment[name] = value

    with pytest.raises(ConfigurationError, match="Production configuration rejects") as error:
        load_settings(env_file=tmp_path / "missing.env", environ=environment)

    assert name in str(error.value)
    assert value not in str(error.value)
