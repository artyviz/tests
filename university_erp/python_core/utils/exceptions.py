"""
University ERP — Custom Exception Hierarchy

Every exception inherits from ERPBaseError so callers can
catch the full family with a single except clause when needed.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


class ERPBaseError(Exception):
    """Root exception for the entire ERP system."""

    def __init__(self, message: str, *, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


# ── Model / Domain errors ────────────────────────────────────
class StudentNotFoundError(ERPBaseError):
    """Raised when a student lookup yields no results."""

    def __init__(self, student_id: str) -> None:
        super().__init__(
            f"Student not found: {student_id}",
            details={"student_id": student_id},
        )


class CourseNotFoundError(ERPBaseError):
    """Raised when a course lookup yields no results."""

    def __init__(self, course_id: str) -> None:
        super().__init__(
            f"Course not found: {course_id}",
            details={"course_id": course_id},
        )


class FacultyNotFoundError(ERPBaseError):
    """Raised when a faculty lookup yields no results."""

    def __init__(self, faculty_id: str) -> None:
        super().__init__(
            f"Faculty not found: {faculty_id}",
            details={"faculty_id": faculty_id},
        )


class DepartmentNotFoundError(ERPBaseError):
    """Raised when a department lookup yields no results."""

    def __init__(self, department_id: str) -> None:
        super().__init__(
            f"Department not found: {department_id}",
            details={"department_id": department_id},
        )


class CourseCapacityError(ERPBaseError):
    """Raised when trying to enroll in a full course."""

    def __init__(self, course_id: str, capacity: int) -> None:
        super().__init__(
            f"Course {course_id} is at full capacity ({capacity})",
            details={"course_id": course_id, "capacity": capacity},
        )


class DuplicateEntryError(ERPBaseError):
    """Raised on unique-constraint violations."""

    def __init__(self, entity_type: str, identifier: str) -> None:
        super().__init__(
            f"Duplicate {entity_type}: {identifier}",
            details={"entity_type": entity_type, "identifier": identifier},
        )


class EnrollmentError(ERPBaseError):
    """Raised on enrollment business-rule violations."""

    def __init__(self, message: str, *, student_id: str = "", course_id: str = "") -> None:
        super().__init__(
            message,
            details={"student_id": student_id, "course_id": course_id},
        )


class PrerequisiteNotMetError(ERPBaseError):
    """Raised when a student lacks prerequisites for a course."""

    def __init__(self, student_id: str, course_id: str, missing: List[str]) -> None:
        super().__init__(
            f"Student {student_id} missing prerequisites for {course_id}: {missing}",
            details={
                "student_id": student_id,
                "course_id": course_id,
                "missing_prerequisites": missing,
            },
        )


# ── Validation / ETL errors ──────────────────────────────────
class ValidationFailedError(ERPBaseError):
    """Raised when model or schema validation fails."""

    def __init__(self, entity_type: str, errors: List[str]) -> None:
        super().__init__(
            f"Validation failed for {entity_type}: {'; '.join(errors)}",
            details={"entity_type": entity_type, "errors": errors},
        )


class ETLPipelineError(ERPBaseError):
    """Raised when any ETL stage fails."""

    def __init__(self, stage: str, reason: str) -> None:
        super().__init__(
            f"ETL pipeline error at [{stage}]: {reason}",
            details={"stage": stage, "reason": reason},
        )


# ── Repository / infra errors ────────────────────────────────
class RepositoryError(ERPBaseError):
    """Raised on database / persistence-layer failures."""

    def __init__(self, operation: str, reason: str) -> None:
        super().__init__(
            f"Repository error during {operation}: {reason}",
            details={"operation": operation, "reason": reason},
        )


class ConfigurationError(ERPBaseError):
    """Raised when settings.yaml is malformed or missing."""

    def __init__(self, key: str, reason: str = "missing or invalid") -> None:
        super().__init__(
            f"Configuration error — {key}: {reason}",
            details={"key": key, "reason": reason},
        )
