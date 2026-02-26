"""
University ERP — Unit Tests for Domain Models

Covers: Student, Course, Department, Enrollment, Faculty
"""

import sys
import os
import unittest
from datetime import date, timedelta

# Ensure project root is on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from python_core.models.student import Student
from python_core.models.course import Course
from python_core.models.department import Department
from python_core.models.enrollment import Enrollment
from python_core.models.faculty import Faculty
from python_core.utils.exceptions import (
    CourseCapacityError,
    ValidationFailedError,
)


# ══════════════════════════════════════════════════════════════
#  STUDENT TESTS
# ══════════════════════════════════════════════════════════════
class TestStudent(unittest.TestCase):

    def _make_student(self, **overrides):
        defaults = dict(
            first_name="John",
            last_name="Doe",
            email="john.doe@university.edu",
            date_of_birth=date(2000, 5, 15),
            department_id="dept-cs-001",
        )
        defaults.update(overrides)
        return Student(**defaults)

    def test_creation_and_defaults(self):
        s = self._make_student()
        self.assertEqual(s.first_name, "John")
        self.assertEqual(s.status, "active")
        self.assertAlmostEqual(s.gpa, 0.0)
        self.assertEqual(s.enrolled_course_ids, [])
        self.assertIsNotNone(s.id)
        self.assertIsNotNone(s.created_at)

    def test_validate_success(self):
        s = self._make_student()
        self.assertTrue(s.validate())

    def test_validate_empty_name(self):
        s = self._make_student(first_name="")
        with self.assertRaises(ValidationFailedError):
            s.validate()

    def test_validate_bad_email(self):
        s = self._make_student(email="not-an-email")
        with self.assertRaises(ValidationFailedError):
            s.validate()

    def test_validate_future_dob(self):
        s = self._make_student(date_of_birth=date.today() + timedelta(days=1))
        with self.assertRaises(ValidationFailedError):
            s.validate()

    def test_validate_bad_status(self):
        s = self._make_student()
        with self.assertRaises(ValidationFailedError):
            s.status = "invalid_status"

    def test_enroll_and_complete(self):
        s = self._make_student()
        s.enroll_in_course("course-1")
        self.assertIn("course-1", s.enrolled_course_ids)

        s.complete_course("course-1", 3.5)
        self.assertNotIn("course-1", s.enrolled_course_ids)
        self.assertIn("course-1", s.completed_course_ids)
        self.assertAlmostEqual(s.gpa, 3.5)

    def test_enroll_duplicate(self):
        s = self._make_student()
        s.enroll_in_course("course-1")
        with self.assertRaises(ValidationFailedError):
            s.enroll_in_course("course-1")

    def test_drop_course(self):
        s = self._make_student()
        s.enroll_in_course("course-1")
        s.drop_course("course-1")
        self.assertEqual(s.enrolled_course_ids, [])

    def test_drop_not_enrolled(self):
        s = self._make_student()
        with self.assertRaises(ValidationFailedError):
            s.drop_course("course-1")

    def test_gpa_calculation(self):
        s = self._make_student()
        s.enroll_in_course("c1")
        s.enroll_in_course("c2")
        s.complete_course("c1", 4.0)
        s.complete_course("c2", 3.0)
        self.assertAlmostEqual(s.gpa, 3.5)

    def test_to_dict_from_dict_roundtrip(self):
        s = self._make_student()
        d = s.to_dict()
        s2 = Student.from_dict(d)
        self.assertEqual(s.first_name, s2.first_name)
        self.assertEqual(s.email, s2.email)
        self.assertEqual(s.department_id, s2.department_id)

    def test_full_name(self):
        s = self._make_student()
        self.assertEqual(s.full_name, "John Doe")

    def test_age(self):
        s = self._make_student(date_of_birth=date(2000, 1, 1))
        self.assertGreaterEqual(s.age, 25)

    def test_equality(self):
        s1 = self._make_student(entity_id="same-id")
        s2 = self._make_student(entity_id="same-id", first_name="Jane")
        self.assertEqual(s1, s2)


# ══════════════════════════════════════════════════════════════
#  COURSE TESTS
# ══════════════════════════════════════════════════════════════
class TestCourse(unittest.TestCase):

    def _make_course(self, **overrides):
        defaults = dict(
            code="CS101",
            title="Intro to CS",
            department_id="dept-cs-001",
            credits=3,
            capacity=30,
        )
        defaults.update(overrides)
        return Course(**defaults)

    def test_creation(self):
        c = self._make_course()
        self.assertEqual(c.code, "CS101")
        self.assertEqual(c.available_seats, 30)
        self.assertFalse(c.is_full)

    def test_add_student(self):
        c = self._make_course(capacity=2)
        c.add_student("s1")
        c.add_student("s2")
        self.assertTrue(c.is_full)

    def test_add_student_full(self):
        c = self._make_course(capacity=1)
        c.add_student("s1")
        with self.assertRaises(CourseCapacityError):
            c.add_student("s2")

    def test_remove_student(self):
        c = self._make_course()
        c.add_student("s1")
        c.remove_student("s1")
        self.assertEqual(c.available_seats, c.capacity)

    def test_validate_bad_credits(self):
        c = self._make_course(credits=0)
        with self.assertRaises(ValidationFailedError):
            c.validate()

    def test_roundtrip(self):
        c = self._make_course()
        d = c.to_dict()
        c2 = Course.from_dict(d)
        self.assertEqual(c.code, c2.code)
        self.assertEqual(c.credits, c2.credits)


# ══════════════════════════════════════════════════════════════
#  DEPARTMENT TESTS
# ══════════════════════════════════════════════════════════════
class TestDepartment(unittest.TestCase):

    def test_creation(self):
        d = Department(name="Computer Science", code="CS")
        self.assertEqual(d.name, "Computer Science")
        self.assertEqual(d.faculty_count, 0)

    def test_add_remove_faculty(self):
        d = Department(name="CS", code="CS")
        d.add_faculty("f1")
        self.assertEqual(d.faculty_count, 1)
        d.remove_faculty("f1")
        self.assertEqual(d.faculty_count, 0)

    def test_budget_negative(self):
        d = Department(name="CS", code="CS")
        with self.assertRaises(ValidationFailedError):
            d.budget = -100

    def test_roundtrip(self):
        d = Department(name="CS", code="CS", budget=50000.0)
        data = d.to_dict()
        d2 = Department.from_dict(data)
        self.assertEqual(d.name, d2.name)
        self.assertEqual(d.budget, d2.budget)


# ══════════════════════════════════════════════════════════════
#  ENROLLMENT TESTS
# ══════════════════════════════════════════════════════════════
class TestEnrollment(unittest.TestCase):

    def test_lifecycle(self):
        e = Enrollment(student_id="s1", course_id="c1", semester="Fall2025")
        self.assertEqual(e.status, "registered")
        self.assertTrue(e.is_active)

        e.start()
        self.assertEqual(e.status, "in_progress")

        e.assign_grade("A")
        self.assertEqual(e.status, "completed")
        self.assertTrue(e.is_completed)
        self.assertAlmostEqual(e.grade_point, 4.0)

    def test_withdraw(self):
        e = Enrollment(student_id="s1", course_id="c1", semester="Fall2025")
        e.withdraw()
        self.assertEqual(e.status, "withdrawn")
        self.assertFalse(e.is_active)

    def test_invalid_grade(self):
        e = Enrollment(student_id="s1", course_id="c1", semester="Fall2025")
        with self.assertRaises(ValidationFailedError):
            e.assign_grade("Z")

    def test_grade_after_withdrawn(self):
        e = Enrollment(student_id="s1", course_id="c1", semester="Fall2025")
        e.withdraw()
        with self.assertRaises(ValidationFailedError):
            e.assign_grade("A")

    def test_failing_grade(self):
        e = Enrollment(student_id="s1", course_id="c1", semester="Fall2025")
        e.assign_grade("F")
        self.assertEqual(e.status, "failed")
        self.assertAlmostEqual(e.grade_point, 0.0)


# ══════════════════════════════════════════════════════════════
#  FACULTY TESTS
# ══════════════════════════════════════════════════════════════
class TestFaculty(unittest.TestCase):

    def _make_faculty(self, **overrides):
        defaults = dict(
            first_name="Dr. Jane",
            last_name="Smith",
            email="jane.smith@university.edu",
            department_id="dept-cs-001",
            rank="assistant_professor",
        )
        defaults.update(overrides)
        return Faculty(**defaults)

    def test_creation(self):
        f = self._make_faculty()
        self.assertEqual(f.full_name, "Dr. Jane Smith")
        self.assertEqual(f.rank, "assistant_professor")

    def test_promote(self):
        f = self._make_faculty(rank="lecturer")
        f.promote()
        self.assertEqual(f.rank, "assistant_professor")
        f.promote()
        self.assertEqual(f.rank, "associate_professor")

    def test_promote_at_max(self):
        f = self._make_faculty(rank="distinguished_professor")
        with self.assertRaises(ValidationFailedError):
            f.promote()

    def test_course_load_limit(self):
        f = self._make_faculty()
        for i in range(Faculty.MAX_COURSE_LOAD):
            f.assign_course(f"course-{i}")
        with self.assertRaises(ValidationFailedError):
            f.assign_course("one-too-many")

    def test_roundtrip(self):
        f = self._make_faculty()
        d = f.to_dict()
        f2 = Faculty.from_dict(d)
        self.assertEqual(f.full_name, f2.full_name)
        self.assertEqual(f.rank, f2.rank)


if __name__ == "__main__":
    unittest.main()
