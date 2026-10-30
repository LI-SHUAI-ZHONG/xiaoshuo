"""Quality persistence adapters."""

from accos.adapters.quality.persistence import (
    InMemoryQualityRepository,
    SqlAlchemyQualityRepository,
)

__all__ = ["InMemoryQualityRepository", "SqlAlchemyQualityRepository"]
