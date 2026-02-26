"""
University ERP — Faculty Domain Model
"""

from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional

from python_core.base import BaseModel
from python_core.utils.exceptions import ValidationFailedError


class Faculty(BaseModel):
    """
    Represents a faculty member.

    Tracks academic rank, department affiliation,
    and course assignments.
    """

    VALID_RANKS = (
        "lecturer",
        "assistant_professor",
        "associate_professor",
        "professor",
        "distinguished_professor",
    )

    MAX_COURSE_LOAD = 6

    def __init__(
        self,
        first_name: str,
        last_name: str,
        email: str,
        department_id: str,
        rank: str,
        *,
        entity_id: Optional[str] = None,
        hire_date: Optional[date] = None,
        specialisation: str = "",
        course_ids: Optional[List[str]] = None,
        is_active: bool = True,
    ) -> None:
        super().__init__(entity_id)
        self._first_name = first_name
        self._last_name = last_name
        self._email = email
        self._department_id = department_id
        self._rank = rank
        self._hire_date = hire_date or date.today()
        self._specialisation = specialisation
        self._course_ids: List[str] = list(course_ids or [])
        self._is_active = is_active

    # ── Properties ───────────────────────────────────────────
    @property
    def first_name(self) -> str:
        return self._first_name

    @property
    def last_name(self) -> str:
        return self._last_name

    @property
    def full_name(self) -> str:
        return f"{self._first_name} {self._last_name}"

    @property
    def email(self) -> str:
        return self._email

    @email.setter
    def email(self, value: str) -> None:
        if not value or "@" not in value:
            raise ValidationFailedError("Faculty", ["Invalid email"])
        self._email = value.strip().lower()
        self.touch()

    @property
    def department_id(self) -> str:
        return self._department_id

    @department_id.setter
    def department_id(self, value: str) -> None:
        self._department_id = value
        self.touch()

    @property
    def rank(self) -> str:
        return self._rank

    @rank.setter
    def rank(self, value: str) -> None:
        if value not in self.VALID_RANKS:
            raise ValidationFailedError(
                "Faculty", [f"Invalid rank '{value}'. Must be one of {self.VALID_RANKS}"]
            )
        self._rank = value
        self.touch()

    @property
    def hire_date(self) -> date:
        return self._hire_date

    @property
    def specialisation(self) -> str:
        return self._specialisation

    @property
    def course_ids(self) -> List[str]:
        return list(self._course_ids)

    @property
    def is_active(self) -> bool:
        return self._is_active

    @is_active.setter
    def is_active(self, value: bool) -> None:
        self._is_active = value
        self.touch()

    @property
    def course_load(self) -> int:
        return len(self._course_ids)

    @property
    def years_of_service(self) -> int:
        today = date.today()
        return today.year - self._hire_date.year - (
            (today.month, today.day) < (self._hire_date.month, self._hire_date.day)
        )

    # ── Business Logic ───────────────────────────────────────
    def assign_course(self, course_id: str) -> None:
        if self.course_load >= self.MAX_COURSE_LOAD:
            raise ValidationFailedError(
                "Faculty",
                [f"Cannot exceed max course load of {self.MAX_COURSE_LOAD}"],
            )
        if course_id in self._course_ids:
            raise ValidationFailedError(
                "Faculty", [f"Already assigned to course {course_id}"]
            )
        self._course_ids.append(course_id)
        self.touch()

    def unassign_course(self, course_id: str) -> None:
        if course_id not in self._course_ids:
            raise ValidationFailedError(
                "Faculty", [f"Not assigned to course {course_id}"]
            )
        self._course_ids.remove(course_id)
        self.touch()

    def promote(self) -> None:
        """Advance to the next academic rank, if possible."""
        ranks = list(self.VALID_RANKS)
        idx = ranks.index(self._rank)
        if idx >= len(ranks) - 1:
            raise ValidationFailedError(
                "Faculty", ["Already at highest rank"]
            )
        self._rank = ranks[idx + 1]
        self.touch()

    # ── Validation ───────────────────────────────────────────
    def validate(self) -> bool:
        errors: List[str] = []
        if not self._first_name or not self._first_name.strip():
            errors.append("first_name is required")
        if not self._last_name or not self._last_name.strip():
            errors.append("last_name is required")
        if not self._email or "@" not in self._email:
            errors.append("valid email is required")
        if self._rank not in self.VALID_RANKS:
            errors.append(f"rank must be one of {self.VALID_RANKS}")
        if self.course_load > self.MAX_COURSE_LOAD:
            errors.append(f"course load exceeds maximum ({self.MAX_COURSE_LOAD})")
        if errors:
            raise ValidationFailedError("Faculty", errors)
        return True

    # ── Serialisation ────────────────────────────────────────
    def to_dict(self) -> Dict[str, Any]:
        data = self._base_dict()
        data.update(
            {
                "first_name": self._first_name,
                "last_name": self._last_name,
                "email": self._email,
                "department_id": self._department_id,
                "rank": self._rank,
                "hire_date": self._hire_date.isoformat(),
                "specialisation": self._specialisation,
                "course_ids": list(self._course_ids),
                "is_active": self._is_active,
            }
        )
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Faculty":
        return cls(
            first_name=data["first_name"],
            last_name=data["last_name"],
            email=data["email"],
            department_id=data["department_id"],
            rank=data["rank"],
            entity_id=data.get("id"),
            hire_date=(
                date.fromisoformat(data["hire_date"])
                if data.get("hire_date")
                else None
            ),
            specialisation=data.get("specialisation", ""),
            course_ids=data.get("course_ids"),
            is_active=data.get("is_active", True),
        )
