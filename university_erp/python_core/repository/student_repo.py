"""
University ERP — Student Repository

Extends PostgresRepository with student-specific queries.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from python_core.models.student import Student
from python_core.repository.base_repo import PostgresRepository
from python_core.utils.exceptions import RepositoryError, StudentNotFoundError
from python_core.utils.logger import ERPLogger

_log = ERPLogger.get_logger("repository.student")


class StudentRepository(PostgresRepository):
    """
    Repository for Student entities.

    Adds domain-specific queries beyond basic CRUD.
    """

    _table_name = "students"
    _model_class = Student
    _columns = [
        "id", "first_name", "last_name", "email", "date_of_birth",
        "enrollment_date", "department_id", "status", "gpa",
        "enrolled_course_ids", "completed_course_ids",
        "created_at", "updated_at",
    ]

    def find_by_email(self, email: str) -> Optional[Student]:
        """Lookup a student by email address."""
        sql = f"SELECT * FROM {self._table_name} WHERE email = %s"
        try:
            cursor = self._conn.cursor()
            cursor.execute(sql, (email.lower(),))
            row = cursor.fetchone()
            if not row:
                return None
            return self._row_to_model(cursor.description, row)
        except Exception as exc:
            raise RepositoryError("find_by_email", str(exc)) from exc

    def find_by_department(
        self, department_id: str, *, limit: int = 100, offset: int = 0
    ) -> List[Student]:
        """All students in a given department."""
        return self.find_all(
            limit=limit, offset=offset, filters={"department_id": department_id}
        )

    def find_active(self, *, limit: int = 100, offset: int = 0) -> List[Student]:
        """Return only active students."""
        return self.find_all(
            limit=limit, offset=offset, filters={"status": "active"}
        )

    def find_by_gpa_range(
        self, min_gpa: float, max_gpa: float, *, limit: int = 100, offset: int = 0
    ) -> List[Student]:
        """Students with GPA in [min_gpa, max_gpa]."""
        sql = (
            f"SELECT * FROM {self._table_name} "
            f"WHERE gpa >= %s AND gpa <= %s "
            f"ORDER BY gpa DESC LIMIT %s OFFSET %s"
        )
        try:
            cursor = self._conn.cursor()
            cursor.execute(sql, (min_gpa, max_gpa, limit, offset))
            rows = cursor.fetchall()
            return [self._row_to_model(cursor.description, r) for r in rows]
        except Exception as exc:
            raise RepositoryError("find_by_gpa_range", str(exc)) from exc

    def search(
        self, query: str, *, limit: int = 50
    ) -> List[Student]:
        """Full-text search on name and email."""
        pattern = f"%{query}%"
        sql = (
            f"SELECT * FROM {self._table_name} "
            f"WHERE first_name ILIKE %s OR last_name ILIKE %s OR email ILIKE %s "
            f"LIMIT %s"
        )
        try:
            cursor = self._conn.cursor()
            cursor.execute(sql, (pattern, pattern, pattern, limit))
            rows = cursor.fetchall()
            return [self._row_to_model(cursor.description, r) for r in rows]
        except Exception as exc:
            raise RepositoryError("search", str(exc)) from exc

    def get_or_raise(self, student_id: str) -> Student:
        """Find a student or raise StudentNotFoundError."""
        student = self.find_by_id(student_id)
        if student is None:
            raise StudentNotFoundError(student_id)
        return student

    def count_by_department(self) -> Dict[str, int]:
        """Return a {department_id: count} map."""
        sql = (
            f"SELECT department_id, COUNT(*) FROM {self._table_name} "
            f"GROUP BY department_id"
        )
        try:
            cursor = self._conn.cursor()
            cursor.execute(sql)
            return {row[0]: row[1] for row in cursor.fetchall()}
        except Exception as exc:
            raise RepositoryError("count_by_department", str(exc)) from exc

    def average_gpa(self, department_id: Optional[str] = None) -> float:
        """Average GPA, optionally filtered by department."""
        if department_id:
            sql = f"SELECT AVG(gpa) FROM {self._table_name} WHERE department_id = %s"
            params: tuple = (department_id,)
        else:
            sql = f"SELECT AVG(gpa) FROM {self._table_name}"
            params = ()
        try:
            cursor = self._conn.cursor()
            cursor.execute(sql, params)
            result = cursor.fetchone()
            return float(result[0]) if result and result[0] else 0.0
        except Exception as exc:
            raise RepositoryError("average_gpa", str(exc)) from exc

    def bulk_insert(self, records: List[Dict[str, Any]]) -> int:
        """Insert massive amounts of records quickly using execute_values."""
        import psycopg2.extras
        if not records:
            return 0
        
        # Determine the columns from the first record
        columns = list(records[0].keys())
        col_names = ", ".join(columns)
        
        # Prepare the list of tuples for execute_values
        data_tuples = [tuple(rec[c] for c in columns) for rec in records]
        
        # ON CONFLICT DO NOTHING — silently skips duplicate emails
        sql = f"INSERT INTO {self._table_name} ({col_names}) VALUES %s ON CONFLICT DO NOTHING"
        try:
            cursor = self._conn.cursor()
            psycopg2.extras.execute_values(
                cursor, sql, data_tuples, page_size=1000
            )
            self._conn.commit()
            return len(records)
        except Exception as exc:
            self._conn.rollback()
            raise RepositoryError("bulk_insert", str(exc)) from exc
