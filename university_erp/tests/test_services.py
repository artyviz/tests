"""
University ERP — Unit Tests for Exceptions & Base Classes
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from python_core.utils.exceptions import (
    ERPBaseError,
    StudentNotFoundError,
    CourseCapacityError,
    ValidationFailedError,
    ETLPipelineError,
    RepositoryError,
    DuplicateEntryError,
    ConfigurationError,
)
from python_core.base import ValidationResult


class TestExceptions(unittest.TestCase):
    """Verify exception hierarchy and detail payloads."""

    def test_base_error(self):
        e = ERPBaseError("test error", details={"key": "val"})
        self.assertIn("test error", str(e))
        self.assertEqual(e.details["key"], "val")

    def test_student_not_found(self):
        e = StudentNotFoundError("s-123")
        self.assertIsInstance(e, ERPBaseError)
        self.assertEqual(e.details["student_id"], "s-123")

    def test_course_capacity(self):
        e = CourseCapacityError("CS101", 30)
        self.assertIn("CS101", str(e))
        self.assertEqual(e.details["capacity"], 30)

    def test_validation_failed(self):
        e = ValidationFailedError("Student", ["name required", "email invalid"])
        self.assertIn("name required", str(e))
        self.assertEqual(len(e.details["errors"]), 2)

    def test_etl_pipeline_error(self):
        e = ETLPipelineError("Extractor", "file not found")
        self.assertEqual(e.details["stage"], "Extractor")

    def test_repository_error(self):
        e = RepositoryError("save", "connection refused")
        self.assertIn("save", str(e))

    def test_duplicate_entry(self):
        e = DuplicateEntryError("Student", "john@test.edu")
        self.assertEqual(e.details["entity_type"], "Student")

    def test_configuration_error(self):
        e = ConfigurationError("database.host")
        self.assertIn("database.host", str(e))

    def test_all_inherit_from_base(self):
        """All custom exceptions must be catchable via ERPBaseError."""
        exceptions = [
            StudentNotFoundError("x"),
            CourseCapacityError("x", 1),
            ValidationFailedError("x", ["e"]),
            ETLPipelineError("x", "y"),
            RepositoryError("x", "y"),
            DuplicateEntryError("x", "y"),
            ConfigurationError("x"),
        ]
        for exc in exceptions:
            self.assertIsInstance(exc, ERPBaseError)


class TestValidationResult(unittest.TestCase):

    def test_valid_result(self):
        r = ValidationResult(
            is_valid=True, errors=[], valid_records=[{"a": 1}], invalid_records=[]
        )
        self.assertTrue(r.is_valid)
        self.assertEqual(len(r.valid_records), 1)
        self.assertEqual(len(r.invalid_records), 0)

    def test_invalid_result(self):
        r = ValidationResult(
            is_valid=False,
            errors=[{"index": 0, "errors": ["bad"]}],
            valid_records=[],
            invalid_records=[{"a": 1}],
        )
        self.assertFalse(r.is_valid)
        self.assertEqual(len(r.errors), 1)


if __name__ == "__main__":
    unittest.main()
