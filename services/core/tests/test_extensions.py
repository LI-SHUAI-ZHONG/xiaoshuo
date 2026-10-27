from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

import pytest

from accos.extensions import (
    PROMOTION_CRITERIA,
    AssetReference,
    CapabilityRequest,
    CapabilityResult,
    CapabilityState,
    CollaborationBoundary,
    CollaborationRequest,
    CollaborationTaskReference,
    CommentReference,
    DeferredBoundary,
    ExtensionCapability,
    ExtensionCatalog,
    MediaKind,
    MultimodalBoundary,
    MultimodalJob,
    MultimodalJobState,
    MultimodalRequest,
    MultimodalResult,
    NullAcquisitionProvider,
    NullCollaborationAdapter,
    NullExternalVerificationProvider,
    NullGraphStore,
    NullGrowthAdapter,
    NullMarketplaceAdapter,
    NullMultimodalAdapter,
    NullReputationAdapter,
    NullResearchTeamProvider,
    NullRightsAdapter,
    OwnedAssetReference,
    PresenceReference,
    ProvenanceMetadata,
    RightsBoundary,
    RightsMetadata,
    RightsRequest,
    RightsResult,
    SafetyMetadata,
    TeamReference,
    TeamRole,
    UsageMetadata,
    default_manifests,
)
from accos.kernel.errors import InvalidStateError, ScopeViolationError
from accos.kernel.features import FeatureFlags
from accos.kernel.graph import GraphDirection, GraphNodeRef

WORKSPACE_ID = UUID("11111111-1111-4111-8111-111111111111")
PROJECT_ID = UUID("22222222-2222-4222-8222-222222222222")
ASSET_ID = UUID("33333333-3333-4333-8333-333333333333")
VERSION_ID = UUID("44444444-4444-4444-8444-444444444444")
OWNER_ID = UUID("55555555-5555-4555-8555-555555555555")
ACTOR_ID = UUID("66666666-6666-4666-8666-666666666666")
TASK_ID = UUID("77777777-7777-4777-8777-777777777777")
COMMENT_ID = UUID("88888888-8888-4888-8888-888888888888")


@dataclass(frozen=True, slots=True)
class ConfiguredCapability:
    configured: bool = True

    async def invoke(self, request: CapabilityRequest) -> CapabilityResult:
        assert request.workspace_id == WORKSPACE_ID
        return CapabilityResult(CapabilityState.AVAILABLE, ("fixture-reference",), "fixture-usage")


@dataclass(frozen=True, slots=True)
class ConfiguredMultimodal:
    job: MultimodalJob
    configured: bool = True

    async def submit(self, request: MultimodalRequest) -> MultimodalResult:
        assert request.capability == self.job.capability
        return MultimodalResult(CapabilityState.AVAILABLE, self.job)


@dataclass(frozen=True, slots=True)
class ConfiguredCollaboration:
    configured: bool = True

    async def invoke(self, request: CollaborationRequest) -> CapabilityResult:
        assert request.collaborative_editor_requested
        return CapabilityResult(CapabilityState.AVAILABLE, ("fixture-collaboration",))


@dataclass(frozen=True, slots=True)
class ConfiguredRights:
    metadata: RightsMetadata
    configured: bool = True

    async def evaluate(self, request: RightsRequest) -> RightsResult:
        assert request.asset.asset_id == ASSET_ID
        return RightsResult(CapabilityState.AVAILABLE, self.metadata)


def asset_reference() -> AssetReference:
    return AssetReference(
        WORKSPACE_ID,
        PROJECT_ID,
        ASSET_ID,
        VERSION_ID,
        OWNER_ID,
        "image/png",
    )


def rights_metadata(
    *,
    workspace_id: UUID = WORKSPACE_ID,
    asset_id: UUID = ASSET_ID,
    owner_id: UUID = OWNER_ID,
) -> RightsMetadata:
    return RightsMetadata(
        workspace_id,
        asset_id,
        owner_id,
        (ACTOR_ID,),
        "fixture-license",
        ("fixture-permission",),
        ("asset://fixture-source",),
        ("audit://fixture-event",),
    )


def test_extension_manifest_catalog_has_honest_states_and_promotion_gates() -> None:
    manifests = default_manifests()
    feature_values = FeatureFlags().extension_values()
    disabled = ExtensionCatalog(manifests, feature_values, frozenset()).statuses()

    assert len(manifests) == len(ExtensionCapability) == 13
    assert {item.capability for item in manifests} == set(ExtensionCapability)
    assert all(item.configuration_schema_version == "1.0.0" for item in manifests)
    assert all(item.configuration_fields for item in manifests)
    assert all(item.required_permissions and item.emitted_events for item in manifests)
    assert all(item.promotion_criteria == PROMOTION_CRITERIA for item in manifests)
    assert all(item.state is CapabilityState.DISABLED for item in disabled)
    assert all(item.detail == "feature_flag_disabled" for item in disabled)

    enabled_values = dict.fromkeys(feature_values, True)
    statuses = ExtensionCatalog(
        manifests,
        enabled_values,
        frozenset({ExtensionCapability.GRAPH}),
    ).statuses()
    graph = next(item for item in statuses if item.manifest.capability is ExtensionCapability.GRAPH)
    deferred = next(
        item
        for item in statuses
        if item.manifest.capability is ExtensionCapability.MULTIMODAL_IMAGE
    )

    assert graph.state is CapabilityState.AVAILABLE
    assert graph.enabled and graph.configured and graph.detail == "adapter_configured"
    assert deferred.state is CapabilityState.NOT_CONFIGURED
    assert deferred.enabled and not deferred.configured
    assert deferred.detail == "null_adapter_active"
    assert tuple(MediaKind) == (
        MediaKind.IMAGE,
        MediaKind.AUDIO,
        MediaKind.VIDEO,
        MediaKind.THREE_D,
    )


def test_disabled_and_null_boundaries_never_create_results_or_usage() -> None:
    request = CapabilityRequest(WORKSPACE_ID, PROJECT_ID, ("asset://fixture",))
    adapters = (
        NullMarketplaceAdapter(),
        NullReputationAdapter(),
        NullGrowthAdapter(),
        NullAcquisitionProvider(),
        NullResearchTeamProvider(),
        NullExternalVerificationProvider(),
    )
    for adapter in adapters:
        disabled = asyncio.run(DeferredBoundary(False, adapter).invoke(request))
        unconfigured = asyncio.run(DeferredBoundary(True, adapter).invoke(request))
        assert disabled == CapabilityResult(CapabilityState.DISABLED)
        assert unconfigured == CapabilityResult(CapabilityState.NOT_CONFIGURED)
        assert not unconfigured.output_references and unconfigured.usage_reference is None

    media_request = MultimodalRequest(
        WORKSPACE_ID,
        PROJECT_ID,
        ExtensionCapability.MULTIMODAL_IMAGE,
        (asset_reference(),),
        "image/png",
    )
    multimodal = NullMultimodalAdapter()
    assert asyncio.run(MultimodalBoundary(False, multimodal).submit(media_request)) == (
        MultimodalResult(CapabilityState.DISABLED)
    )
    assert asyncio.run(MultimodalBoundary(True, multimodal).submit(media_request)) == (
        MultimodalResult(CapabilityState.NOT_CONFIGURED)
    )

    collaboration_request = CollaborationRequest(
        WORKSPACE_ID,
        PROJECT_ID,
        TeamReference(WORKSPACE_ID, PROJECT_ID, (ACTOR_ID,), (TeamRole.CONTRIBUTOR,)),
        CollaborationTaskReference(WORKSPACE_ID, PROJECT_ID, TASK_ID, ACTOR_ID),
        CommentReference(WORKSPACE_ID, PROJECT_ID, COMMENT_ID, "asset://fixture"),
        PresenceReference(WORKSPACE_ID, PROJECT_ID, ACTOR_ID, "document://fixture"),
        True,
    )
    collaboration = NullCollaborationAdapter()
    assert asyncio.run(
        CollaborationBoundary(False, collaboration).invoke(collaboration_request)
    ) == CapabilityResult(CapabilityState.DISABLED)
    assert asyncio.run(
        CollaborationBoundary(True, collaboration).invoke(collaboration_request)
    ) == CapabilityResult(CapabilityState.NOT_CONFIGURED)

    owned = OwnedAssetReference(WORKSPACE_ID, PROJECT_ID, ASSET_ID, OWNER_ID)
    rights_request = RightsRequest(owned, rights_metadata())
    rights = NullRightsAdapter()
    assert asyncio.run(RightsBoundary(False, rights).evaluate(rights_request)) == RightsResult(
        CapabilityState.DISABLED
    )
    assert asyncio.run(RightsBoundary(True, rights).evaluate(rights_request)) == RightsResult(
        CapabilityState.NOT_CONFIGURED
    )


def test_configured_boundaries_preserve_rights_and_reference_metadata() -> None:
    capability_request = CapabilityRequest(WORKSPACE_ID, PROJECT_ID)
    result = asyncio.run(DeferredBoundary(True, ConfiguredCapability()).invoke(capability_request))
    assert result == CapabilityResult(
        CapabilityState.AVAILABLE,
        ("fixture-reference",),
        "fixture-usage",
    )

    reference = asset_reference()
    job = MultimodalJob(
        TASK_ID,
        WORKSPACE_ID,
        PROJECT_ID,
        ExtensionCapability.MULTIMODAL_IMAGE,
        MultimodalJobState.SUCCEEDED,
        (reference,),
        (reference,),
        ProvenanceMetadata(
            "fixture-provider",
            "fixture-job",
            (ASSET_ID,),
            datetime(2026, 9, 17, tzinfo=UTC),
        ),
        UsageMetadata(1, 1, 1, 0),
        SafetyMetadata("fixture-policy", "scanned", ("fixture-safe",)),
    )
    request = MultimodalRequest(
        WORKSPACE_ID,
        PROJECT_ID,
        ExtensionCapability.MULTIMODAL_IMAGE,
        (reference,),
        "image/png",
    )
    assert (
        asyncio.run(MultimodalBoundary(True, ConfiguredMultimodal(job)).submit(request)).job == job
    )

    collaboration = CollaborationRequest(
        WORKSPACE_ID,
        PROJECT_ID,
        collaborative_editor_requested=True,
    )
    assert (
        asyncio.run(
            CollaborationBoundary(True, ConfiguredCollaboration()).invoke(collaboration)
        ).state
        is CapabilityState.AVAILABLE
    )

    owned = OwnedAssetReference(WORKSPACE_ID, PROJECT_ID, ASSET_ID, OWNER_ID)
    proposed = rights_metadata()
    request_rights = RightsRequest(owned, proposed)
    accepted = asyncio.run(
        RightsBoundary(True, ConfiguredRights(proposed)).evaluate(request_rights)
    )
    assert accepted.metadata == proposed

    for changed in (
        rights_metadata(workspace_id=PROJECT_ID),
        rights_metadata(asset_id=PROJECT_ID),
        rights_metadata(owner_id=PROJECT_ID),
    ):
        with pytest.raises(ScopeViolationError):
            asyncio.run(RightsBoundary(True, ConfiguredRights(changed)).evaluate(request_rights))


def test_null_graph_store_fails_closed_for_every_operation() -> None:
    graph = NullGraphStore()
    node = GraphNodeRef(WORKSPACE_ID, "fixture-owner", "fixture-kind", ASSET_ID)
    calls = (
        graph.neighbors(
            node,
            projection_owner="fixture-projection",
            direction=GraphDirection.BOTH,
            limit=1,
        ),
        graph.replace_edges(
            WORKSPACE_ID,
            projection_owner="fixture-projection",
            edges=(),
        ),
        graph.drop_projection(WORKSPACE_ID, projection_owner="fixture-projection"),
        graph.rebuild(
            WORKSPACE_ID,
            projection_owner="fixture-projection",
            events=(),
        ),
        graph.traverse(
            node,
            projection_owner="fixture-projection",
            direction=GraphDirection.BOTH,
            max_depth=1,
            limit=1,
        ),
    )
    for call in calls:
        with pytest.raises(InvalidStateError, match="not configured"):
            asyncio.run(call)
