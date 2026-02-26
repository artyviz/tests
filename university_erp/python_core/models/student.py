"""
University ERP — Student Domain Model

Strict OOP: all attributes are private with controlled access
through properties.  Business rules are enforced inside the model.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, List, Optional

from python_core.base import BaseModel
from python_core.utils.exceptions import ValidationFailedError


class Student(BaseModel):
    """
    Represents a university student entity.

    Attributes (encapsulated):
        first_name, last_name, email, date_of_birth,
        enrollment_date, department_id, status, gpa,
        enrolled_course_ids, completed_course_ids
    """

    VALID_STATUSES = ("active", "inactive", "graduated", "suspended", "on_leave")

    def __init__(
        self,
        first_name: str,
        last_name: str,
        email: str,
        date_of_birth: date,
        department_id: str,
        *,
        entity_id: Optional[str] = None,
        enrollment_date: Optional[date] = None,
        status: str = "active",
        gpa: float = 0.0,
        enrolled_course_ids: Optional[List[str]] = None,
        completed_course_ids: Optional[List[str]] = None,
    ) -> None:
        super().__init__(entity_id)
        self._first_name = first_name
        self._last_name = last_name
        self._email = email
        self._date_of_birth = date_of_birth
        self._enrollment_date = enrollment_date or date.today()
        self._department_id = department_id
        self._status = status
        self._gpa = gpa
        self._enrolled_course_ids: List[str] = list(enrolled_course_ids or [])
        self._completed_course_ids: List[str] = list(completed_course_ids or [])

    # ── Properties ───────────────────────────────────────────
    @property
    def first_name(self) -> str:
        return self._first_name

    @first_name.setter
    def first_name(self, value: str) -> None:
        if not value or not value.strip():
            raise ValidationFailedError("Student", ["first_name cannot be empty"])
        self._first_name = value.strip()
        self.touch()

    @property
    def last_name(self) -> str:
        return self._last_name

    @last_name.setter
    def last_name(self, value: str) -> None:
        if not value or not value.strip():
            raise ValidationFailedError("Student", ["last_name cannot be empty"])
        self._last_name = value.strip()
        self.touch()

    @property
    def full_name(self) -> str:
        return f"{self._first_name} {self._last_name}"

    @property
    def email(self) -> str:
        return self._email

    @email.setter
    def email(self, value: str) -> None:
        if not value or "@" not in value:
            raise ValidationFailedError("Student", ["Invalid email address"])
        self._email = value.strip().lower()
        self.touch()

    @property
    def date_of_birth(self) -> date:
        return self._date_of_birth

    @property
    def enrollment_date(self) -> date:
        return self._enrollment_date

    @property
    def department_id(self) -> str:
        return self._department_id

    @department_id.setter
    def department_id(self, value: str) -> None:
        self._department_id = value
        self.touch()

    @property
    def status(self) -> str:
        return self._status

    @status.setter
    def status(self, value: str) -> None:
        if value not in self.VALID_STATUSES:
            raise ValidationFailedError(
                "Student", [f"Invalid status '{value}'. Must be one of {self.VALID_STATUSES}"]
            )
        self._status = value
        self.touch()

    @property
    def gpa(self) -> float:
        return self._gpa

    @property
    def enrolled_course_ids(self) -> List[str]:
        return list(self._enrolled_course_ids)

    @property
    def completed_course_ids(self) -> List[str]:
        return list(self._completed_course_ids)

    # ── Business Logic ───────────────────────────────────────
    def enroll_in_course(self, course_id: str) -> None:
        """Add a course to the student's active enrolments."""
        if course_id in self._enrolled_course_ids:
            raise ValidationFailedError(
                "Student", [f"Already enrolled in course {course_id}"]
            )
        if course_id in self._completed_course_ids:
            raise ValidationFailedError(
                "Student", [f"Already completed course {course_id}"]
            )
        self._enrolled_course_ids.append(course_id)
        self.touch()

    def complete_course(self, course_id: str, grade_point: float) -> None:
        """Mark a course as completed and update GPA."""
        if course_id not in self._enrolled_course_ids:
            raise ValidationFailedError(
                "Student", [f"Not enrolled in course {course_id}"]
            )
        self._enrolled_course_ids.remove(course_id)
        self._completed_course_ids.append(course_id)
        self._recalculate_gpa(grade_point)
        self.touch()

    def drop_course(self, course_id: str) -> None:
        """Remove a course from active enrolments."""
        if course_id not in self._enrolled_course_ids:
            raise ValidationFailedError(
                "Student", [f"Not enrolled in course {course_id}"]
            )
        self._enrolled_course_ids.remove(course_id)
        self.touch()

    def _recalculate_gpa(self, new_grade: float) -> None:
        """Incremental GPA recalculation upon course completion."""
        n = len(self._completed_course_ids)
        if n == 1:
            self._gpa = new_grade
        else:
            self._gpa = ((self._gpa * (n - 1)) + new_grade) / n

    @property
    def age(self) -> int:
        today = date.today()
        return (
            today.year
            - self._date_of_birth.year
            - (
                (today.month, today.day)
                < (self._date_of_birth.month, self._date_of_birth.day)
            )
        )

    # ── Validation ───────────────────────────────────────────
    def validate(self) -> bool:
        errors: List[str] = []
        if not self._first_name or not self._first_name.strip():
            errors.append("first_name is required")
        if not self._last_name or not self._last_name.strip():
            errors.append("last_name is required")
        if not self._email or "@" not in self._email:
            errors.append("valid email is required")
        if self._date_of_birth >= date.today():
            errors.append("date_of_birth must be in the past")
        if self._status not in self.VALID_STATUSES:
            errors.append(f"status must be one of {self.VALID_STATUSES}")
        if not (0.0 <= self._gpa <= 4.0):
            errors.append("gpa must be between 0.0 and 4.0")
        if errors:
            raise ValidationFailedError("Student", errors)
        return True

    # ── Serialisation ────────────────────────────────────────
    def to_dict(self) -> Dict[str, Any]:
        data = self._base_dict()
        data.update(
            {
                "first_name": self._first_name,
                "last_name": self._last_name,
                "email": self._email,
                "date_of_birth": self._date_of_birth.isoformat(),
                "enrollment_date": self._enrollment_date.isoformat(),
                "department_id": self._department_id,
                "status": self._status,
                "gpa": round(self._gpa, 2),
                "enrolled_course_ids": list(self._enrolled_course_ids),
                "completed_course_ids": list(self._completed_course_ids),
            }
        )
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Student":
        return cls(
            first_name=data["first_name"],
            last_name=data["last_name"],
            email=data["email"],
            date_of_birth=date.fromisoformat(data["date_of_birth"]),
            department_id=data["department_id"],
            entity_id=data.get("id"),
            enrollment_date=(
                date.fromisoformat(data["enrollment_date"])
                if data.get("enrollment_date")
                else None
            ),
            status=data.get("status", "active"),
            gpa=float(data.get("gpa", 0.0)),
            enrolled_course_ids=data.get("enrolled_course_ids"),
            completed_course_ids=data.get("completed_course_ids"),
        )
