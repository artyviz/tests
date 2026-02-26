"""
University ERP — Enrollment Domain Model

Junction entity linking Students ↔ Courses with grade tracking.
"""

from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional

from python_core.base import BaseModel
from python_core.utils.exceptions import ValidationFailedError


class Enrollment(BaseModel):
    """
    Represents a student's enrollment in a specific course.

    Tracks the enrollment lifecycle: registered → in_progress →
    completed / withdrawn / failed.
    """

    VALID_STATUSES = ("registered", "in_progress", "completed", "withdrawn", "failed")
    GRADE_POINTS = {
        "A+": 4.0, "A": 4.0, "A-": 3.7,
        "B+": 3.3, "B": 3.0, "B-": 2.7,
        "C+": 2.3, "C": 2.0, "C-": 1.7,
        "D+": 1.3, "D": 1.0, "D-": 0.7,
        "F": 0.0,
    }

    def __init__(
        self,
        student_id: str,
        course_id: str,
        semester: str,
        *,
        entity_id: Optional[str] = None,
        enrollment_date: Optional[date] = None,
        status: str = "registered",
        grade: Optional[str] = None,
        grade_point: Optional[float] = None,
    ) -> None:
        super().__init__(entity_id)
        self._student_id = student_id
        self._course_id = course_id
        self._semester = semester
        self._enrollment_date = enrollment_date or date.today()
        self._status = status
        self._grade = grade
        self._grade_point = grade_point

    # ── Properties ───────────────────────────────────────────
    @property
    def student_id(self) -> str:
        return self._student_id

    @property
    def course_id(self) -> str:
        return self._course_id

    @property
    def semester(self) -> str:
        return self._semester

    @property
    def enrollment_date(self) -> date:
        return self._enrollment_date

    @property
    def status(self) -> str:
        return self._status

    @property
    def grade(self) -> Optional[str]:
        return self._grade

    @property
    def grade_point(self) -> Optional[float]:
        return self._grade_point

    @property
    def is_completed(self) -> bool:
        return self._status == "completed"

    @property
    def is_active(self) -> bool:
        return self._status in ("registered", "in_progress")

    # ── Business Logic ───────────────────────────────────────
    def start(self) -> None:
        """Transition from registered → in_progress."""
        if self._status != "registered":
            raise ValidationFailedError(
                "Enrollment", [f"Cannot start enrollment in status '{self._status}'"]
            )
        self._status = "in_progress"
        self.touch()

    def assign_grade(self, grade: str) -> None:
        """Assign a letter grade, auto-calculate grade point, and mark completed."""
        if grade not in self.GRADE_POINTS:
            raise ValidationFailedError(
                "Enrollment", [f"Invalid grade '{grade}'. Must be one of {list(self.GRADE_POINTS)}"]
            )
        if self._status not in ("in_progress", "registered"):
            raise ValidationFailedError(
                "Enrollment", [f"Cannot grade enrollment in status '{self._status}'"]
            )
        self._grade = grade
        self._grade_point = self.GRADE_POINTS[grade]
        self._status = "completed" if self._grade_point > 0.0 else "failed"
        self.touch()

    def withdraw(self) -> None:
        """Withdraw from the course."""
        if not self.is_active:
            raise ValidationFailedError(
                "Enrollment", [f"Cannot withdraw from enrollment in status '{self._status}'"]
            )
        self._status = "withdrawn"
        self.touch()

    # ── Validation ───────────────────────────────────────────
    def validate(self) -> bool:
        errors: List[str] = []
        if not self._student_id:
            errors.append("student_id is required")
        if not self._course_id:
            errors.append("course_id is required")
        if not self._semester:
            errors.append("semester is required")
        if self._status not in self.VALID_STATUSES:
            errors.append(f"status must be one of {self.VALID_STATUSES}")
        if self._grade and self._grade not in self.GRADE_POINTS:
            errors.append(f"grade must be one of {list(self.GRADE_POINTS)}")
        if errors:
            raise ValidationFailedError("Enrollment", errors)
        return True

    # ── Serialisation ────────────────────────────────────────
    def to_dict(self) -> Dict[str, Any]:
        data = self._base_dict()
        data.update(
            {
                "student_id": self._student_id,
                "course_id": self._course_id,
                "semester": self._semester,
                "enrollment_date": self._enrollment_date.isoformat(),
                "status": self._status,
                "grade": self._grade,
                "grade_point": self._grade_point,
            }
        )
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Enrollment":
        return cls(
            student_id=data["student_id"],
            course_id=data["course_id"],
            semester=data["semester"],
            entity_id=data.get("id"),
            enrollment_date=(
                date.fromisoformat(data["enrollment_date"])
                if data.get("enrollment_date")
                else None
            ),
            status=data.get("status", "registered"),
            grade=data.get("grade"),
            grade_point=data.get("grade_point"),
        )
