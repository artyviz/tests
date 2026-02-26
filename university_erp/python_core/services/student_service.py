"""
University ERP — Student Service

Encapsulates student-related business logic.
Receives its repository via constructor injection.
"""

from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional

from python_core.base import BaseService
from python_core.models.student import Student
from python_core.repository.student_repo import StudentRepository
from python_core.utils.exceptions import (
    DuplicateEntryError,
    EnrollmentError,
    StudentNotFoundError,
    ValidationFailedError,
)
from python_core.utils.logger import ERPLogger

_log = ERPLogger.get_logger("service.student")


class StudentService(BaseService[Student]):
    """
    High-level operations on students:
    register, enroll, transfer, search, GPA computation.
    """

    def __init__(self, repository: StudentRepository) -> None:
        super().__init__(repository)
        self._repo: StudentRepository = repository  # typed alias

    # ── Template-method hooks ────────────────────────────────
    def _pre_execute(self, *args: Any, **kwargs: Any) -> None:
        _log.debug("StudentService pre-execute: %s %s", args, kwargs)

    def _post_execute(self, result: Any, *args: Any, **kwargs: Any) -> Any:
        _log.debug("StudentService post-execute: result=%s", type(result).__name__)
        return result

    # ── Required by BaseService ──────────────────────────────
    def execute(self, *args: Any, **kwargs: Any) -> Any:
        """Dispatch point — delegates to specific methods."""
        action = kwargs.get("action", "get")
        if action == "register":
            return self.register_student(**kwargs)
        elif action == "get":
            return self.get_student(kwargs["student_id"])
        raise ValidationFailedError("StudentService", [f"Unknown action: {action}"])

    # ── Business operations ──────────────────────────────────
    def register_student(
        self,
        first_name: str,
        last_name: str,
        email: str,
        date_of_birth: date,
        department_id: str,
        **kwargs: Any,
    ) -> Student:
        """Register a new student after checking for duplicates."""
        self._pre_execute(email=email)

        # Duplicate email check
        existing = self._repo.find_by_email(email)
        if existing:
            raise DuplicateEntryError("Student", email)

        student = Student(
            first_name=first_name,
            last_name=last_name,
            email=email,
            date_of_birth=date_of_birth,
            department_id=department_id,
        )
        student.validate()
        saved = self._repo.save(student)
        _log.info("Registered student: %s (%s)", student.full_name, student.email)
        return self._post_execute(saved)

    def get_student(self, student_id: str) -> Student:
        """Fetch a student by ID or raise."""
        return self._repo.get_or_raise(student_id)

    def update_student(self, student_id: str, **fields: Any) -> Student:
        """Partially update student fields."""
        student = self._repo.get_or_raise(student_id)

        for field, value in fields.items():
            if hasattr(student, field):
                setattr(student, field, value)

        student.validate()
        return self._repo.update(student)

    def enroll_in_course(self, student_id: str, course_id: str) -> Student:
        """Enroll a student in a course."""
        student = self._repo.get_or_raise(student_id)
        if student.status != "active":
            raise EnrollmentError(
                f"Cannot enroll student with status '{student.status}'",
                student_id=student_id,
                course_id=course_id,
            )
        student.enroll_in_course(course_id)
        return self._repo.update(student)

    def complete_course(
        self, student_id: str, course_id: str, grade_point: float
    ) -> Student:
        """Mark a course as completed for a student."""
        student = self._repo.get_or_raise(student_id)
        student.complete_course(course_id, grade_point)
        return self._repo.update(student)

    def drop_course(self, student_id: str, course_id: str) -> Student:
        """Drop a student from a course."""
        student = self._repo.get_or_raise(student_id)
        student.drop_course(course_id)
        return self._repo.update(student)

    def transfer_department(
        self, student_id: str, new_department_id: str
    ) -> Student:
        """Transfer a student to a different department."""
        student = self._repo.get_or_raise(student_id)
        old_dept = student.department_id
        student.department_id = new_department_id
        updated = self._repo.update(student)
        _log.info(
            "Transferred student %s from dept %s → %s",
            student_id, old_dept, new_department_id,
        )
        return updated

    def search_students(self, query: str, *, limit: int = 50) -> List[Student]:
        """Search students by name or email."""
        return self._repo.search(query, limit=limit)

    def list_students(
        self,
        *,
        limit: int = 100,
        offset: int = 0,
        department_id: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[Student]:
        """List students with optional filters."""
        filters: Dict[str, Any] = {}
        if department_id:
            filters["department_id"] = department_id
        if status:
            filters["status"] = status
        return self._repo.find_all(limit=limit, offset=offset, filters=filters)

    def deactivate_student(self, student_id: str) -> Student:
        """Set student status to inactive."""
        student = self._repo.get_or_raise(student_id)
        student.status = "inactive"
        return self._repo.update(student)

    def get_total_count(self, department_id: Optional[str] = None) -> int:
        filters = {"department_id": department_id} if department_id else None
        return self._repo.count(filters)
