"""Capability catalog, secure Null adapters, and rights invariants."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from accos.extensions.contracts import (
    PROMOTION_CRITERIA,
    AcquisitionProvider,
    CapabilityManifest,
    CapabilityRequest,
    CapabilityResult,
    CapabilityState,
    CapabilityStatus,
    CollaborationRequest,
    ConfigurationField,
    ConfigurationValueKind,
    ExtensionCapability,
    ExternalVerificationProvider,
    MultimodalRequest,
    MultimodalResult,
    ResearchTeamProvider,
    RightsMetadata,
    RightsRequest,
    RightsResult,
)
from accos.kernel.errors import ScopeViolationError

if TYPE_CHECKING:
    from collections.abc import Mapping

    from accos.extensions.contracts import (
        CollaborationPort,
        DeferredCapabilityPort,
        MultimodalPort,
        RightsPort,
    )


_PROVIDER_FIELDS = (
    ConfigurationField("provider_id", ConfigurationValueKind.STRING, required=True),
    ConfigurationField(
        "credential_reference", ConfigurationValueKind.OPAQUE_REFERENCE, required=True
    ),
)
_BUILT_IN_GRAPH_FIELDS = (
    ConfigurationField("projection_owner", ConfigurationValueKind.STRING, required=True),
)


def default_manifests() -> tuple[CapabilityManifest, ...]:
    """Return the complete parked-capability catalog in deterministic API order."""
    definitions = (
        (
            ExtensionCapability.MULTIMODAL_IMAGE,
            "multimodal_image",
            ("model:run",),
            ("extension.multimodal.image.job_status_changed",),
            _PROVIDER_FIELDS,
        ),
        (
            ExtensionCapability.MULTIMODAL_AUDIO,
            "multimodal_audio",
            ("model:run",),
            ("extension.multimodal.audio.job_status_changed",),
            _PROVIDER_FIELDS,
        ),
        (
            ExtensionCapability.MULTIMODAL_VIDEO,
            "multimodal_video",
            ("model:run",),
            ("extension.multimodal.video.job_status_changed",),
            _PROVIDER_FIELDS,
        ),
        (
            ExtensionCapability.MULTIMODAL_THREE_D,
            "multimodal_three_d",
            ("model:run",),
            ("extension.multimodal.three_d.job_status_changed",),
            _PROVIDER_FIELDS,
        ),
        (
            ExtensionCapability.GRAPH,
            "graph",
            ("project:read",),
            ("extension.graph.projection_rebuilt",),
            _BUILT_IN_GRAPH_FIELDS,
        ),
        (
            ExtensionCapability.COLLABORATION,
            "collaboration",
            ("project:write",),
            ("extension.collaboration.reference_changed",),
            _PROVIDER_FIELDS,
        ),
        (
            ExtensionCapability.RIGHTS,
            "rights",
            ("workspace:write", "audit:read"),
            ("extension.rights.metadata_proposed",),
            _PROVIDER_FIELDS,
        ),
        (
            ExtensionCapability.MARKETPLACE,
            "marketplace",
            ("feature-flag:manage",),
            ("extension.marketplace.status_changed",),
            _PROVIDER_FIELDS,
        ),
        (
            ExtensionCapability.REPUTATION,
            "reputation",
            ("feature-flag:manage",),
            ("extension.reputation.status_changed",),
            _PROVIDER_FIELDS,
        ),
        (
            ExtensionCapability.GROWTH,
            "growth",
            ("feature-flag:manage",),
            ("extension.growth.status_changed",),
            _PROVIDER_FIELDS,
        ),
        (
            ExtensionCapability.KNOWLEDGE_ACQUISITION,
            "knowledge_network",
            ("project:write",),
            ("extension.knowledge.acquisition_status_changed",),
            _PROVIDER_FIELDS,
        ),
        (
            ExtensionCapability.KNOWLEDGE_RESEARCH_TEAM,
            "knowledge_network",
            ("project:write",),
            ("extension.knowledge.research_team_status_changed",),
            _PROVIDER_FIELDS,
        ),
        (
            ExtensionCapability.KNOWLEDGE_VERIFICATION,
            "knowledge_network",
            ("project:read",),
            ("extension.knowledge.verification_status_changed",),
            _PROVIDER_FIELDS,
        ),
    )
    return tuple(
        CapabilityManifest(
            capability,
            feature_flag,
            permissions,
            events,
            "1.0.0",
            fields,
            PROMOTION_CRITERIA,
        )
        for capability, feature_flag, permissions, events, fields in definitions
    )


@dataclass(frozen=True, slots=True)
class ExtensionCatalog:
    """Read-only catalog separating feature enablement from adapter configuration."""

    manifests: tuple[CapabilityManifest, ...]
    feature_values: Mapping[str, bool]
    configured_capabilities: frozenset[ExtensionCapability]

    def statuses(self) -> tuple[CapabilityStatus, ...]:
        """Report disabled, unconfigured, or available without probing optional services."""
        statuses: list[CapabilityStatus] = []
        for manifest in self.manifests:
            enabled = self.feature_values[manifest.feature_flag]
            configured = manifest.capability in self.configured_capabilities
            if not enabled:
                state = CapabilityState.DISABLED
                detail = "feature_flag_disabled"
            elif not configured:
                state = CapabilityState.NOT_CONFIGURED
                detail = "null_adapter_active"
            else:
                state = CapabilityState.AVAILABLE
                detail = "adapter_configured"
            statuses.append(CapabilityStatus(manifest, state, enabled, configured, detail))
        return tuple(statuses)


@dataclass(frozen=True, slots=True)
class DeferredBoundary:
    """Fail-closed invocation wrapper shared by parked generic capabilities."""

    enabled: bool
    adapter: DeferredCapabilityPort

    async def invoke(self, request: CapabilityRequest) -> CapabilityResult:
        if not self.enabled:
            return CapabilityResult(CapabilityState.DISABLED)
        return await self.adapter.invoke(request)


@dataclass(frozen=True, slots=True)
class MultimodalBoundary:
    """Prevent disabled multimodal requests from reaching a provider adapter."""

    enabled: bool
    adapter: MultimodalPort

    async def submit(self, request: MultimodalRequest) -> MultimodalResult:
        if not self.enabled:
            return MultimodalResult(CapabilityState.DISABLED)
        return await self.adapter.submit(request)


@dataclass(frozen=True, slots=True)
class CollaborationBoundary:
    """Prevent disabled collaboration requests from reaching an adapter."""

    enabled: bool
    adapter: CollaborationPort

    async def invoke(self, request: CollaborationRequest) -> CapabilityResult:
        if not self.enabled:
            return CapabilityResult(CapabilityState.DISABLED)
        return await self.adapter.invoke(request)


@dataclass(frozen=True, slots=True)
class RightsBoundary:
    """Preserve core workspace and owner identity across any rights adapter."""

    enabled: bool
    adapter: RightsPort

    async def evaluate(self, request: RightsRequest) -> RightsResult:
        if not self.enabled:
            return RightsResult(CapabilityState.DISABLED)
        result = await self.adapter.evaluate(request)
        if result.metadata is not None:
            self._assert_ownership(request, result.metadata)
        return result

    @staticmethod
    def _assert_ownership(request: RightsRequest, metadata: RightsMetadata) -> None:
        asset = request.asset
        if (
            metadata.workspace_id != asset.workspace_id
            or metadata.asset_id != asset.asset_id
            or metadata.owner_id != asset.owner_id
        ):
            raise ScopeViolationError


class NullCapabilityAdapter:
    """No-op adapter returning an explicit state and no output or usage."""

    configured = False

    async def invoke(self, request: CapabilityRequest) -> CapabilityResult:
        del request
        return CapabilityResult(CapabilityState.NOT_CONFIGURED)


class NullMarketplaceAdapter(NullCapabilityAdapter):
    """Marketplace Null adapter: no payment, product, or transaction behavior."""


class NullReputationAdapter(NullCapabilityAdapter):
    """Reputation Null adapter: no scores or rankings."""


class NullGrowthAdapter(NullCapabilityAdapter):
    """Growth Null adapter: no recommendation or acquisition behavior."""


class NullAcquisitionProvider(NullCapabilityAdapter, AcquisitionProvider):
    """External acquisition Null adapter: performs no network request."""


class NullResearchTeamProvider(NullCapabilityAdapter, ResearchTeamProvider):
    """External research-team Null adapter."""


class NullExternalVerificationProvider(NullCapabilityAdapter, ExternalVerificationProvider):
    """External verification Null adapter."""


class NullMultimodalAdapter:
    """Multimodal Null adapter: never creates jobs, outputs, usage, or safety claims."""

    configured = False

    async def submit(self, request: MultimodalRequest) -> MultimodalResult:
        del request
        return MultimodalResult(CapabilityState.NOT_CONFIGURED)


class NullCollaborationAdapter:
    """Collaboration Null adapter: no presence or editor session is created."""

    configured = False

    async def invoke(self, request: CollaborationRequest) -> CapabilityResult:
        del request
        return CapabilityResult(CapabilityState.NOT_CONFIGURED)


class NullRightsAdapter:
    """Rights Null adapter: makes no legal or ownership determination."""

    configured = False

    async def evaluate(self, request: RightsRequest) -> RightsResult:
        del request
        return RightsResult(CapabilityState.NOT_CONFIGURED)
