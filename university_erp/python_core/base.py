"""
University ERP — Abstract Base Classes

Defines the foundational contracts for every domain model,
repository, and service in the system.  All concrete classes
MUST extend these ABCs to guarantee interface consistency.
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, Generic, List, Optional, TypeVar

# ── Generic type for Repository / Service parameterisation ────
T = TypeVar("T", bound="BaseModel")


# ══════════════════════════════════════════════════════════════
#  BASE MODEL
# ══════════════════════════════════════════════════════════════
class BaseModel(ABC):
    """
    Abstract base for every domain entity.

    Guarantees:
      • Unique `id` generation
      • Created / updated timestamps
      • Serialisation round-trip  (to_dict ↔ from_dict)
      • Self-validation before persistence
    """

    def __init__(self, entity_id: Optional[str] = None) -> None:
        self._id: str = entity_id or str(uuid.uuid4())
        self._created_at: datetime = datetime.utcnow()
        self._updated_at: datetime = datetime.utcnow()

    # ── Read-only properties ─────────────────────────────────
    @property
    def id(self) -> str:
        return self._id

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def updated_at(self) -> datetime:
        return self._updated_at

    def touch(self) -> None:
        """Mark the entity as recently modified."""
        self._updated_at = datetime.utcnow()

    # ── Abstract contract ────────────────────────────────────
    @abstractmethod
    def validate(self) -> bool:
        """
        Return True if the entity is in a valid state.
        Raise ValidationFailedError on the first violated rule.
        """
        ...

    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """Serialise to a plain dict (JSON-safe)."""
        ...

    @classmethod
    @abstractmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BaseModel":
        """Construct a model instance from a plain dict."""
        ...

    # ── Shared helpers ───────────────────────────────────────
    def _base_dict(self) -> Dict[str, Any]:
        """Common fields included in every to_dict() call."""
        return {
            "id": self._id,
            "created_at": self._created_at.isoformat(),
            "updated_at": self._updated_at.isoformat(),
        }

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} id={self._id}>"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, BaseModel):
            return NotImplemented
        return self._id == other._id

    def __hash__(self) -> int:
        return hash(self._id)


# ══════════════════════════════════════════════════════════════
#  BASE REPOSITORY  (Data Access Layer)
# ══════════════════════════════════════════════════════════════
class BaseRepository(ABC, Generic[T]):
    """
    Repository pattern — isolates persistence logic from
    domain models and services.
    """

    @abstractmethod
    def find_by_id(self, entity_id: str) -> Optional[T]:
        ...

    @abstractmethod
    def find_all(
        self,
        *,
        limit: int = 100,
        offset: int = 0,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[T]:
        ...

    @abstractmethod
    def save(self, entity: T) -> T:
        ...

    @abstractmethod
    def update(self, entity: T) -> T:
        ...

    @abstractmethod
    def delete(self, entity_id: str) -> bool:
        ...

    @abstractmethod
    def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        ...


# ══════════════════════════════════════════════════════════════
#  BASE SERVICE  (Business Logic Layer)
# ══════════════════════════════════════════════════════════════
class BaseService(ABC, Generic[T]):
    """
    Services encapsulate business rules and orchestrate
    repository calls.  Concrete services receive their
    repository via constructor injection (no global state).
    """

    def __init__(self, repository: BaseRepository[T]) -> None:
        self._repository = repository

    # ── Template-method hooks ────────────────────────────────
    def _pre_execute(self, *args: Any, **kwargs: Any) -> None:
        """Override to add pre-processing (logging, auth, …)."""

    def _post_execute(self, result: Any, *args: Any, **kwargs: Any) -> Any:
        """Override to add post-processing (caching, events, …)."""
        return result

    @abstractmethod
    def execute(self, *args: Any, **kwargs: Any) -> Any:
        """Primary service action — must be implemented."""
        ...


# ══════════════════════════════════════════════════════════════
#  ETL  ABSTRACT BASES
# ══════════════════════════════════════════════════════════════
class BaseExtractor(ABC):
    """Pulls raw data from an external source."""

    @abstractmethod
    def extract(self, source: Any) -> List[Dict[str, Any]]:
        ...


class BaseTransformer(ABC):
    """Transforms / normalises raw records."""

    @abstractmethod
    def transform(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        ...


class BaseLoader(ABC):
    """Writes processed records to a destination."""

    @abstractmethod
    def load(self, data: List[Dict[str, Any]], destination: Any) -> int:
        """Return the number of records successfully loaded."""
        ...


class BaseValidator(ABC):
    """Validates records against a schema or rule-set."""

    @abstractmethod
    def validate(
        self, data: List[Dict[str, Any]]
    ) -> "ValidationResult":
        ...


class ValidationResult:
    """Immutable result of a validation pass."""

    __slots__ = ("_is_valid", "_errors", "_valid_records", "_invalid_records")

    def __init__(
        self,
        is_valid: bool,
        errors: List[Dict[str, Any]],
        valid_records: List[Dict[str, Any]],
        invalid_records: List[Dict[str, Any]],
    ) -> None:
        self._is_valid = is_valid
        self._errors = errors
        self._valid_records = valid_records
        self._invalid_records = invalid_records

    @property
    def is_valid(self) -> bool:
        return self._is_valid

    @property
    def errors(self) -> List[Dict[str, Any]]:
        return list(self._errors)

    @property
    def valid_records(self) -> List[Dict[str, Any]]:
        return list(self._valid_records)

    @property
    def invalid_records(self) -> List[Dict[str, Any]]:
        return list(self._invalid_records)

    def __repr__(self) -> str:
        return (
            f"<ValidationResult valid={self._is_valid} "
            f"ok={len(self._valid_records)} "
            f"err={len(self._invalid_records)}>"
        )
