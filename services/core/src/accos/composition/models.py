"""The same real model factory is used by API and Worker, with lazy I/O only."""

from accos.adapters.assets import SqlAlchemyAssetRepository
from accos.adapters.identity import SqlAlchemyAuditStore, SqlAlchemyIdentityRepository
from accos.adapters.identity.accounts import SqlAccountStore
from accos.adapters.identity.crypto import (
    CredentialCipher,
    external_secret,
    password_hash,
    password_matches,
)
from accos.adapters.identity.oidc import HttpOidcClient
from accos.adapters.memory import SqlAlchemyMemoryRepository
from accos.adapters.models.budgets import RedisModelQuota, SqlBudgetLedger
from accos.adapters.models.http import ModelHttpTransport
from accos.adapters.models.real_providers import (
    ChatCompletionsProvider,
    OllamaProvider,
    OpenAIResponsesProvider,
)
from accos.adapters.models.runtime_store import SqlModelStore
from accos.adapters.persistence.database import AsyncSessionFactory
from accos.adapters.projects import SqlAlchemyProjectRepository
from accos.kernel.clock import Clock
from accos.kernel.settings import RuntimeSettings
from accos.modules.assets.public import (
    AssetService,
    DefaultUploadSecurityPolicy,
    ObjectStorage,
    UnconfiguredContentScanner,
)
from accos.modules.identity.account_service import AccountService, LiveScopeAccess
from accos.modules.identity.public import AuthorizationService
from accos.modules.memory.public import (
    ContextBuilder,
    DefaultRetentionPolicy,
    FakeSemanticMemoryRanker,
    MemoryAccessPolicy,
)
from accos.modules.models.prompts import PromptRegistry, packaged_prompts
from accos.modules.models.runtime import ModelRuntime
from accos.modules.models.runtime_ports import ContentProvider


def build_model_runtime(
    settings: RuntimeSettings, sessions: AsyncSessionFactory, storage: ObjectStorage, clock: Clock
) -> ModelRuntime:
    store = SqlModelStore(sessions)
    accounts_store = SqlAccountStore(sessions)
    audit = SqlAlchemyAuditStore(sessions)
    authorizer = AuthorizationService(
        audit, clock, LiveScopeAccess(accounts_store, clock, SqlAlchemyIdentityRepository(sessions))
    )
    accounts = AccountService(
        accounts_store,
        authorizer,
        clock,
        settings.auth,
        CredentialCipher(settings.auth.secret_keys, settings.auth.active_key_id),
        password_hash,
        password_matches,
        external_secret,
        HttpOidcClient(settings.auth),
        audit,
    )
    projects = SqlAlchemyProjectRepository(sessions)
    assets = AssetService(
        SqlAlchemyAssetRepository(sessions),
        projects=projects,
        storage=storage,
        scanner=UnconfiguredContentScanner(),
        legacy_bucket=settings.required.s3_bucket,
        upload_policy=DefaultUploadSecurityPolicy(),
        authorizer=authorizer,
        clock=clock,
    )
    memory = SqlAlchemyMemoryRepository(sessions)
    contexts = ContextBuilder(
        memory,
        projects,
        authorizer,
        MemoryAccessPolicy(memory, authorizer),
        FakeSemanticMemoryRanker(DefaultRetentionPolicy()),
        clock,
    )
    transport = ModelHttpTransport()
    providers: dict[str, ContentProvider] = {
        "openai_responses": OpenAIResponsesProvider(transport),
        "chat_completions": ChatCompletionsProvider(transport),
        "ollama": OllamaProvider(transport),
    }
    return ModelRuntime(
        store,
        SqlBudgetLedger(sessions),
        RedisModelQuota(settings.required.redis_url),
        assets,
        accounts,
        projects,
        providers,
        PromptRegistry(store, packaged_prompts()),
        clock,
        contexts,
        calls_enabled=settings.features.real_provider_calls_enabled
        and settings.models.mode == "real",
        local_endpoints=settings.models.local_endpoints,
    )
