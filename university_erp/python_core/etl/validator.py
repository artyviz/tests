"""
University ERP — ETL Validator

BaseValidator ABC + concrete implementations for schema
validation and student-specific business-rule validation.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any, Callable, Dict, List, Optional, Set

from python_core.base import BaseValidator, ValidationResult
from python_core.utils.exceptions import ETLPipelineError
from python_core.utils.logger import ERPLogger

_log = ERPLogger.get_logger("etl.validator")


# ══════════════════════════════════════════════════════════════
#  SCHEMA VALIDATOR  (generic, rule-driven)
# ══════════════════════════════════════════════════════════════
class SchemaValidator(BaseValidator):
    """
    Validates records against a declarative schema.

    Each field rule is a dict:
        {
            "field": "email",
            "type": "str",
            "required": True,
            "pattern": r".+@.+\\..+",   # optional regex
            "min": ..., "max": ...,      # for numeric fields
        }
    """

    TYPE_MAP = {
        "str": str,
        "int": int,
        "float": (int, float),
        "bool": bool,
        "list": list,
        "dict": dict,
    }

    def __init__(self, schema: List[Dict[str, Any]]) -> None:
        self._schema = schema

    def validate(self, data: List[Dict[str, Any]]) -> ValidationResult:
        _log.info("Schema-validating %d records", len(data))
        valid_records: List[Dict[str, Any]] = []
        invalid_records: List[Dict[str, Any]] = []
        all_errors: List[Dict[str, Any]] = []

        for idx, record in enumerate(data):
            record_errors = self._validate_record(record)
            if record_errors:
                invalid_records.append(record)
                all_errors.append({"index": idx, "errors": record_errors})
            else:
                valid_records.append(record)

        is_valid = len(invalid_records) == 0
        _log.info(
            "Validation complete: %d valid, %d invalid",
            len(valid_records), len(invalid_records),
        )
        return ValidationResult(
            is_valid=is_valid,
            errors=all_errors,
            valid_records=valid_records,
            invalid_records=invalid_records,
        )

    def _validate_record(self, record: Dict[str, Any]) -> List[str]:
        errors: List[str] = []
        for rule in self._schema:
            field = rule["field"]
            value = record.get(field)

            # Required check
            if rule.get("required", False) and (value is None or value == ""):
                errors.append(f"'{field}' is required")
                continue

            if value is None:
                continue

            # Type check
            expected_type = rule.get("type")
            if expected_type and expected_type in self.TYPE_MAP:
                if not isinstance(value, self.TYPE_MAP[expected_type]):
                    errors.append(
                        f"'{field}' must be of type {expected_type}, got {type(value).__name__}"
                    )

            # Pattern check
            pattern = rule.get("pattern")
            if pattern and isinstance(value, str):
                if not re.match(pattern, value):
                    errors.append(f"'{field}' does not match pattern {pattern}")

            # Range checks
            if "min" in rule and isinstance(value, (int, float)):
                if value < rule["min"]:
                    errors.append(f"'{field}' must be >= {rule['min']}")
            if "max" in rule and isinstance(value, (int, float)):
                if value > rule["max"]:
                    errors.append(f"'{field}' must be <= {rule['max']}")

        return errors


# ══════════════════════════════════════════════════════════════
#  STUDENT DATA VALIDATOR  (domain-specific)
# ══════════════════════════════════════════════════════════════
class StudentDataValidator(BaseValidator):
    """
    Business-rule validator for student records.

    Rules:
      • first_name & last_name non-empty
      • valid email format
      • date_of_birth in the past & student age ≥ 15
      • GPA in [0.0, 4.0]
      • department_id non-empty
      • No duplicate emails within the batch
    """

    EMAIL_RE = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")

    def validate(self, data: List[Dict[str, Any]]) -> ValidationResult:
        _log.info("Student-validating %d records", len(data))
        valid_records: List[Dict[str, Any]] = []
        invalid_records: List[Dict[str, Any]] = []
        all_errors: List[Dict[str, Any]] = []
        seen_emails: Set[str] = set()

        for idx, record in enumerate(data):
            errors = self._validate_student(record, seen_emails)
            if errors:
                invalid_records.append(record)
                all_errors.append({"index": idx, "errors": errors})
            else:
                email = str(record.get("email", "")).lower()
                seen_emails.add(email)
                valid_records.append(record)

        is_valid = len(invalid_records) == 0
        _log.info(
            "Student validation: %d valid, %d invalid",
            len(valid_records), len(invalid_records),
        )
        return ValidationResult(
            is_valid=is_valid,
            errors=all_errors,
            valid_records=valid_records,
            invalid_records=invalid_records,
        )

    def _validate_student(
        self, record: Dict[str, Any], seen_emails: Set[str]
    ) -> List[str]:
        errors: List[str] = []

        # Name checks
        if not record.get("first_name", "").strip():
            errors.append("first_name is required")
        if not record.get("last_name", "").strip():
            errors.append("last_name is required")

        # Email
        email = str(record.get("email", "")).strip().lower()
        if not self.EMAIL_RE.match(email):
            errors.append("invalid email format")
        elif email in seen_emails:
            errors.append(f"duplicate email: {email}")

        # DOB / age
        dob_raw = record.get("date_of_birth")
        if dob_raw:
            try:
                if isinstance(dob_raw, str):
                    dob = date.fromisoformat(dob_raw)
                elif isinstance(dob_raw, date):
                    dob = dob_raw
                else:
                    raise ValueError("unsupported type")
                if dob >= date.today():
                    errors.append("date_of_birth must be in the past")
                else:
                    age = (date.today() - dob).days // 365
                    if age < 15:
                        errors.append("student must be at least 15 years old")
            except (ValueError, TypeError):
                errors.append("date_of_birth is not a valid ISO date")
        else:
            errors.append("date_of_birth is required")

        # GPA
        try:
            gpa = float(record.get("gpa", 0.0))
            if gpa < 0.0 or gpa > 4.0:
                errors.append("gpa must be between 0.0 and 4.0")
        except (ValueError, TypeError):
            errors.append("gpa must be numeric")

        # Department
        if not record.get("department_id", "").strip():
            errors.append("department_id is required")

        return errors
