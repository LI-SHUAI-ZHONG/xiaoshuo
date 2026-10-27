"""Export the deterministic ACCOS OpenAPI document without starting network services."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import cast

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "services" / "core" / "src"))

from accos.entrypoints.api import create_app
from accos.entrypoints.api.v1.schemas import AsyncOperationReference
from accos.entrypoints.api.v1.stage17_schemas import SseEventData
from accos.kernel.features import FeatureFlags
from accos.kernel.settings import (
    OptionalSettings,
    RequiredSettings,
    RuntimeSettings,
    SecuritySettings,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "packages" / "api-client" / "openapi.json"


def contract_settings() -> RuntimeSettings:
    """Return inert settings used only to assemble the schema graph."""
    return RuntimeSettings(
        required=RequiredSettings(
            database_url="postgresql+psycopg://fixture:fixture@127.0.0.1/fixture",
            redis_url="redis://:fixture@127.0.0.1/0",
            s3_endpoint="http://127.0.0.1:9000",
            s3_bucket="fixture-project",
            s3_access_key="fixture",
            s3_secret_key="fixture",  # noqa: S106 - inert schema-only value.
        ),
        optional=OptionalSettings(
            environment="contract",
            log_level="ERROR",
            s3_region="us-east-1",
            s3_use_ssl=False,
            api_host="127.0.0.1",
            api_port=8000,
            health_timeout_seconds=0.05,
            db_pool_size=1,
            db_max_overflow=0,
            db_pool_timeout_seconds=0.05,
            db_pool_recycle_seconds=60,
            ai_provider=None,
        ),
        features=FeatureFlags(real_provider_calls_enabled=False),
        security=SecuritySettings(
            dev_identity_enabled=False,
            dev_identity_token=None,
            dev_identity_actor_id=None,
            dev_identity_workspace_id=None,
        ),
    )


def build_schema() -> dict[str, object]:
    """Build and enrich the same schema served by the application factory."""
    settings = contract_settings()
    app = create_app(
        settings,
        schema_only=True,
        configure_logs=False,
    )
    schema = cast("dict[str, object]", app.openapi())
    info = cast("dict[str, object]", schema["info"])
    info["x-api-version"] = "v1"
    schema["jsonSchemaDialect"] = "https://json-schema.org/draft/2020-12/schema"
    schema["x-accos-deprecation-policy"] = (
        "Additive changes remain in v1; breaking changes require a new major path. "
        "Deprecated operations emit Deprecation and successor Link headers before removal."
    )
    components = cast("dict[str, object]", schema["components"])
    schemas = cast("dict[str, object]", components["schemas"])
    schemas["AsyncOperationReference"] = AsyncOperationReference.model_json_schema(
        ref_template="#/components/schemas/{model}"
    )
    schemas["SseEventData"] = SseEventData.model_json_schema(
        ref_template="#/components/schemas/{model}"
    )
    return schema


def serialized_schema() -> str:
    """Return canonical, stable JSON with one final newline."""
    return json.dumps(build_schema(), ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    arguments = parser.parse_args()
    expected = serialized_schema()
    output = arguments.output.resolve()
    if arguments.check:
        if not output.is_file() or output.read_text(encoding="utf-8") != expected:
            sys.stderr.write(f"OpenAPI export is stale: {output}\n")
            return 1
        return 0
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(expected, encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
