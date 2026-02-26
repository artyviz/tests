"""
University ERP — Analytics Service

Aggregation / reporting queries across the entire system.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from python_core.base import BaseService
from python_core.models.student import Student
from python_core.repository.student_repo import StudentRepository
from python_core.utils.logger import ERPLogger

_log = ERPLogger.get_logger("service.analytics")


class AnalyticsService(BaseService[Student]):
    """
    Read-only analytics built on top of the student repository.
    Extend with additional repositories as the system grows.
    """

    def __init__(self, student_repo: StudentRepository) -> None:
        super().__init__(student_repo)
        self._student_repo: StudentRepository = student_repo

    def execute(self, *args: Any, **kwargs: Any) -> Any:
        action = kwargs.get("action", "dashboard")
        if action == "dashboard":
            return self.dashboard_summary()
        return self.dashboard_summary()

    # ── Analytics methods ────────────────────────────────────
    def dashboard_summary(self) -> Dict[str, Any]:
        """High-level dashboard stats."""
        total_students = self._student_repo.count()
        active_students = self._student_repo.count(filters={"status": "active"})
        avg_gpa = self._student_repo.average_gpa()
        dept_counts = self._student_repo.count_by_department()

        summary = {
            "total_students": total_students,
            "active_students": active_students,
            "inactive_students": total_students - active_students,
            "average_gpa": round(avg_gpa, 2),
            "students_per_department": dept_counts,
        }
        _log.info("Dashboard summary generated: %s", summary)
        return summary

    def department_report(self, department_id: str) -> Dict[str, Any]:
        """Detailed stats for a single department."""
        students = self._student_repo.find_by_department(department_id, limit=10_000)
        avg_gpa = self._student_repo.average_gpa(department_id)

        status_dist: Dict[str, int] = {}
        gpa_dist: Dict[str, int] = {"high": 0, "mid": 0, "low": 0}

        for s in students:
            status_dist[s.status] = status_dist.get(s.status, 0) + 1
            if s.gpa >= 3.5:
                gpa_dist["high"] += 1
            elif s.gpa >= 2.0:
                gpa_dist["mid"] += 1
            else:
                gpa_dist["low"] += 1

        return {
            "department_id": department_id,
            "total_students": len(students),
            "average_gpa": round(avg_gpa, 2),
            "status_distribution": status_dist,
            "gpa_distribution": gpa_dist,
        }

    def top_students(
        self, *, min_gpa: float = 3.5, limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Return top students by GPA."""
        students = self._student_repo.find_by_gpa_range(
            min_gpa, 4.0, limit=limit
        )
        return [
            {
                "id": s.id,
                "name": s.full_name,
                "email": s.email,
                "gpa": s.gpa,
                "department_id": s.department_id,
            }
            for s in students
        ]
