"""
University ERP — Course Domain Model
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from python_core.base import BaseModel
from python_core.utils.exceptions import CourseCapacityError, ValidationFailedError


class Course(BaseModel):
    """
    Represents a university course.

    Encapsulates capacity management, prerequisite tracking,
    and credit-hour information.
    """

    def __init__(
        self,
        code: str,
        title: str,
        department_id: str,
        credits: int,
        capacity: int,
        *,
        entity_id: Optional[str] = None,
        description: str = "",
        instructor_id: Optional[str] = None,
        prerequisite_ids: Optional[List[str]] = None,
        enrolled_student_ids: Optional[List[str]] = None,
        semester: str = "",
        is_active: bool = True,
    ) -> None:
        super().__init__(entity_id)
        self._code = code
        self._title = title
        self._department_id = department_id
        self._credits = credits
        self._capacity = capacity
        self._description = description
        self._instructor_id = instructor_id
        self._prerequisite_ids: List[str] = list(prerequisite_ids or [])
        self._enrolled_student_ids: List[str] = list(enrolled_student_ids or [])
        self._semester = semester
        self._is_active = is_active

    # ── Properties ───────────────────────────────────────────
    @property
    def code(self) -> str:
        return self._code

    @property
    def title(self) -> str:
        return self._title

    @title.setter
    def title(self, value: str) -> None:
        if not value or not value.strip():
            raise ValidationFailedError("Course", ["title cannot be empty"])
        self._title = value.strip()
        self.touch()

    @property
    def department_id(self) -> str:
        return self._department_id

    @property
    def credits(self) -> int:
        return self._credits

    @property
    def capacity(self) -> int:
        return self._capacity

    @capacity.setter
    def capacity(self, value: int) -> None:
        if value < len(self._enrolled_student_ids):
            raise ValidationFailedError(
                "Course",
                [f"Cannot reduce capacity below current enrollment ({len(self._enrolled_student_ids)})"],
            )
        self._capacity = value
        self.touch()

    @property
    def description(self) -> str:
        return self._description

    @property
    def instructor_id(self) -> Optional[str]:
        return self._instructor_id

    @instructor_id.setter
    def instructor_id(self, value: Optional[str]) -> None:
        self._instructor_id = value
        self.touch()

    @property
    def prerequisite_ids(self) -> List[str]:
        return list(self._prerequisite_ids)

    @property
    def enrolled_student_ids(self) -> List[str]:
        return list(self._enrolled_student_ids)

    @property
    def semester(self) -> str:
        return self._semester

    @property
    def is_active(self) -> bool:
        return self._is_active

    @is_active.setter
    def is_active(self, value: bool) -> None:
        self._is_active = value
        self.touch()

    @property
    def available_seats(self) -> int:
        return self._capacity - len(self._enrolled_student_ids)

    @property
    def is_full(self) -> bool:
        return self.available_seats <= 0

    # ── Business Logic ───────────────────────────────────────
    def add_student(self, student_id: str) -> None:
        """Enroll a student if there is capacity."""
        if self.is_full:
            raise CourseCapacityError(self._code, self._capacity)
        if student_id in self._enrolled_student_ids:
            raise ValidationFailedError(
                "Course", [f"Student {student_id} already enrolled"]
            )
        self._enrolled_student_ids.append(student_id)
        self.touch()

    def remove_student(self, student_id: str) -> None:
        """Remove a student from the course roster."""
        if student_id not in self._enrolled_student_ids:
            raise ValidationFailedError(
                "Course", [f"Student {student_id} is not enrolled"]
            )
        self._enrolled_student_ids.remove(student_id)
        self.touch()

    def add_prerequisite(self, course_id: str) -> None:
        if course_id not in self._prerequisite_ids:
            self._prerequisite_ids.append(course_id)
            self.touch()

    def remove_prerequisite(self, course_id: str) -> None:
        if course_id in self._prerequisite_ids:
            self._prerequisite_ids.remove(course_id)
            self.touch()

    # ── Validation ───────────────────────────────────────────
    def validate(self) -> bool:
        errors: List[str] = []
        if not self._code or not self._code.strip():
            errors.append("code is required")
        if not self._title or not self._title.strip():
            errors.append("title is required")
        if self._credits < 1 or self._credits > 12:
            errors.append("credits must be between 1 and 12")
        if self._capacity < 1:
            errors.append("capacity must be at least 1")
        if len(self._enrolled_student_ids) > self._capacity:
            errors.append("enrollment exceeds capacity")
        if errors:
            raise ValidationFailedError("Course", errors)
        return True

    # ── Serialisation ────────────────────────────────────────
    def to_dict(self) -> Dict[str, Any]:
        data = self._base_dict()
        data.update(
            {
                "code": self._code,
                "title": self._title,
                "department_id": self._department_id,
                "credits": self._credits,
                "capacity": self._capacity,
                "description": self._description,
                "instructor_id": self._instructor_id,
                "prerequisite_ids": list(self._prerequisite_ids),
                "enrolled_student_ids": list(self._enrolled_student_ids),
                "semester": self._semester,
                "is_active": self._is_active,
                "available_seats": self.available_seats,
            }
        )
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Course":
        return cls(
            code=data["code"],
            title=data["title"],
            department_id=data["department_id"],
            credits=int(data["credits"]),
            capacity=int(data["capacity"]),
            entity_id=data.get("id"),
            description=data.get("description", ""),
            instructor_id=data.get("instructor_id"),
            prerequisite_ids=data.get("prerequisite_ids"),
            enrolled_student_ids=data.get("enrolled_student_ids"),
            semester=data.get("semester", ""),
            is_active=data.get("is_active", True),
        )
