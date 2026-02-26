"""
University ERP — Department Domain Model
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from python_core.base import BaseModel
from python_core.utils.exceptions import ValidationFailedError


class Department(BaseModel):
    """
    Represents a university department.

    Aggregates faculty members and courses,
    tracks budget and head-of-department.
    """

    def __init__(
        self,
        name: str,
        code: str,
        *,
        entity_id: Optional[str] = None,
        head_faculty_id: Optional[str] = None,
        faculty_ids: Optional[List[str]] = None,
        course_ids: Optional[List[str]] = None,
        budget: float = 0.0,
        description: str = "",
    ) -> None:
        super().__init__(entity_id)
        self._name = name
        self._code = code
        self._head_faculty_id = head_faculty_id
        self._faculty_ids: List[str] = list(faculty_ids or [])
        self._course_ids: List[str] = list(course_ids or [])
        self._budget = budget
        self._description = description

    # ── Properties ───────────────────────────────────────────
    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        if not value or not value.strip():
            raise ValidationFailedError("Department", ["name cannot be empty"])
        self._name = value.strip()
        self.touch()

    @property
    def code(self) -> str:
        return self._code

    @property
    def head_faculty_id(self) -> Optional[str]:
        return self._head_faculty_id

    @head_faculty_id.setter
    def head_faculty_id(self, value: Optional[str]) -> None:
        self._head_faculty_id = value
        self.touch()

    @property
    def faculty_ids(self) -> List[str]:
        return list(self._faculty_ids)

    @property
    def course_ids(self) -> List[str]:
        return list(self._course_ids)

    @property
    def budget(self) -> float:
        return self._budget

    @budget.setter
    def budget(self, value: float) -> None:
        if value < 0:
            raise ValidationFailedError("Department", ["budget cannot be negative"])
        self._budget = value
        self.touch()

    @property
    def description(self) -> str:
        return self._description

    @property
    def faculty_count(self) -> int:
        return len(self._faculty_ids)

    @property
    def course_count(self) -> int:
        return len(self._course_ids)

    # ── Business Logic ───────────────────────────────────────
    def add_faculty(self, faculty_id: str) -> None:
        if faculty_id not in self._faculty_ids:
            self._faculty_ids.append(faculty_id)
            self.touch()

    def remove_faculty(self, faculty_id: str) -> None:
        if faculty_id in self._faculty_ids:
            self._faculty_ids.remove(faculty_id)
            if self._head_faculty_id == faculty_id:
                self._head_faculty_id = None
            self.touch()

    def add_course(self, course_id: str) -> None:
        if course_id not in self._course_ids:
            self._course_ids.append(course_id)
            self.touch()

    def remove_course(self, course_id: str) -> None:
        if course_id in self._course_ids:
            self._course_ids.remove(course_id)
            self.touch()

    # ── Validation ───────────────────────────────────────────
    def validate(self) -> bool:
        errors: List[str] = []
        if not self._name or not self._name.strip():
            errors.append("name is required")
        if not self._code or not self._code.strip():
            errors.append("code is required")
        if self._budget < 0:
            errors.append("budget cannot be negative")
        if errors:
            raise ValidationFailedError("Department", errors)
        return True

    # ── Serialisation ────────────────────────────────────────
    def to_dict(self) -> Dict[str, Any]:
        data = self._base_dict()
        data.update(
            {
                "name": self._name,
                "code": self._code,
                "head_faculty_id": self._head_faculty_id,
                "faculty_ids": list(self._faculty_ids),
                "course_ids": list(self._course_ids),
                "budget": self._budget,
                "description": self._description,
            }
        )
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Department":
        return cls(
            name=data["name"],
            code=data["code"],
            entity_id=data.get("id"),
            head_faculty_id=data.get("head_faculty_id"),
            faculty_ids=data.get("faculty_ids"),
            course_ids=data.get("course_ids"),
            budget=float(data.get("budget", 0.0)),
            description=data.get("description", ""),
        )
