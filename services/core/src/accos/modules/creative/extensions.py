"""Creative extension ports and deterministic unconfigured defaults."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from uuid import UUID


class ExtensionStatus(StrEnum):
    """Machine-readable extension result state."""

    NOT_CONFIGURED = "NOT_CONFIGURED"
    PROPOSED = "PROPOSED"


@dataclass(frozen=True, slots=True)
class ExtensionRequest:
    """Content-free request carrying only scope and opaque input references."""

    workspace_id: UUID
    project_id: UUID
    input_references: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ExtensionResult:
    """An extension may return a proposal reference, never mutate accepted facts."""

    status: ExtensionStatus
    proposal_reference: str | None = None


class CreativeExtensionPort(Protocol):
    async def invoke(self, request: ExtensionRequest) -> ExtensionResult: ...


class ConceptPort(CreativeExtensionPort, Protocol):
    """Concept proposal boundary."""


class ThemePort(CreativeExtensionPort, Protocol):
    """Theme proposal boundary."""


class PlotPort(CreativeExtensionPort, Protocol):
    """Plot proposal boundary."""


class EmotionPort(CreativeExtensionPort, Protocol):
    """Emotion metadata proposal boundary."""


class StylePort(CreativeExtensionPort, Protocol):
    """Style metadata proposal boundary."""


class ChapterGeneratorPort(CreativeExtensionPort, Protocol):
    """Chapter draft proposal boundary."""


class WorldSimulationPort(CreativeExtensionPort, Protocol):
    """World simulation proposal boundary."""


class CharacterBehaviorPort(CreativeExtensionPort, Protocol):
    """Character behavior proposal boundary."""


class CreatorLearningPort(CreativeExtensionPort, Protocol):
    """Creator-learning proposal boundary."""


class PoliticalComponentPort(CreativeExtensionPort, Protocol):
    """Extensible political component boundary."""


class EconomicComponentPort(CreativeExtensionPort, Protocol):
    """Extensible economic component boundary."""


class TechnologyComponentPort(CreativeExtensionPort, Protocol):
    """Extensible technology component boundary."""


class CultureComponentPort(CreativeExtensionPort, Protocol):
    """Extensible culture component boundary."""


class NullCreativeExtension:
    """Default for every optional creative capability."""

    async def invoke(self, request: ExtensionRequest) -> ExtensionResult:
        del request
        return ExtensionResult(ExtensionStatus.NOT_CONFIGURED)


@dataclass(frozen=True, slots=True)
class CreativeExtensions:
    """All optional ports assembled explicitly by the composition root."""

    concept: ConceptPort
    theme: ThemePort
    plot: PlotPort
    emotion: EmotionPort
    style: StylePort
    chapter_generator: ChapterGeneratorPort
    world_simulation: WorldSimulationPort
    character_behavior: CharacterBehaviorPort
    creator_learning: CreatorLearningPort
    political: PoliticalComponentPort
    economic: EconomicComponentPort
    technology: TechnologyComponentPort
    culture: CultureComponentPort


def null_creative_extensions() -> CreativeExtensions:
    """Build isolated Null instances so later adapter replacement stays granular."""
    return CreativeExtensions(
        NullCreativeExtension(),
        NullCreativeExtension(),
        NullCreativeExtension(),
        NullCreativeExtension(),
        NullCreativeExtension(),
        NullCreativeExtension(),
        NullCreativeExtension(),
        NullCreativeExtension(),
        NullCreativeExtension(),
        NullCreativeExtension(),
        NullCreativeExtension(),
        NullCreativeExtension(),
        NullCreativeExtension(),
    )
