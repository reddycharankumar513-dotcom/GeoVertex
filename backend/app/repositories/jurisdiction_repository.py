"""Re-export jurisdiction_repository from organization_repository for modular access."""
from app.repositories.organization_repository import (
    JurisdictionRepository,
    jurisdiction_repository,
)

__all__ = ["JurisdictionRepository", "jurisdiction_repository"]
