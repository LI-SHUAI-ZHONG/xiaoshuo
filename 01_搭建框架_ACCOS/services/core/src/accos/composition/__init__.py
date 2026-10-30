"""Application composition root; the only place concrete adapters are assembled."""

from accos.adapters.workflows import CELERY_WORKFLOW_TASK
from accos.composition.root import (
    AgentServices,
    ApplicationContainer,
    AssetServices,
    CreativeServices,
    EvolutionServices,
    ExtensionServices,
    FeedbackServices,
    IdentityServices,
    KnowledgeServices,
    ModelServices,
    ObservabilityServices,
    ProjectServices,
    ToolServices,
    WorkflowServices,
    build_container,
)

__all__ = [
    "CELERY_WORKFLOW_TASK",
    "AgentServices",
    "ApplicationContainer",
    "AssetServices",
    "CreativeServices",
    "EvolutionServices",
    "ExtensionServices",
    "FeedbackServices",
    "IdentityServices",
    "KnowledgeServices",
    "ModelServices",
    "ObservabilityServices",
    "ProjectServices",
    "ToolServices",
    "WorkflowServices",
    "build_container",
]
