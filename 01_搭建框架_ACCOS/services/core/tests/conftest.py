from __future__ import annotations

import pytest

from accos.kernel.auth_settings import AuthSettings

from accos.kernel.features import FeatureFlags
from accos.kernel.settings import (
    ModelSettings,
    OptionalSettings,
    RequiredSettings,
    RuntimeSettings,
    SecuritySettings,
)


@pytest.fixture
def runtime_settings() -> RuntimeSettings:
    return RuntimeSettings(
        required=RequiredSettings(
            database_url=("postgresql+psycopg://fixture:fixture-database-secret@127.0.0.1/fixture"),
            redis_url="redis://:fixture-redis-secret@127.0.0.1/0",
            s3_endpoint="http://127.0.0.1:9000",
            s3_bucket="fixture-project",
            s3_access_key="fixture-access-key",
            s3_secret_key="fixture-object-secret",
        ),
        optional=OptionalSettings(
            environment="test",
            log_level="INFO",
            s3_region="us-east-1",
            s3_use_ssl=False,
            api_host="127.0.0.1",
            api_port=8000,
            health_timeout_seconds=0.05,
            db_pool_size=2,
            db_max_overflow=1,
            db_pool_timeout_seconds=0.05,
            db_pool_recycle_seconds=60,
            ai_provider=None,
        ),
        features=FeatureFlags(real_provider_calls_enabled=False),
        models=ModelSettings(mode="test"),
        security=SecuritySettings(
            dev_identity_enabled=False,
            dev_identity_token=None,
            dev_identity_actor_id=None,
            dev_identity_workspace_id=None,
        ),
        auth=AuthSettings(allowed_hosts=("testserver", "localhost", "127.0.0.1")),
    )
