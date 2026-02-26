"""
University ERP — ETL Transformer

BaseTransformer ABC + concrete implementations for common
data-normalisation tasks.  ChainedTransformer enables pipeline
composition of multiple transformers.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any, Callable, Dict, List, Optional

from python_core.base import BaseTransformer
from python_core.utils.exceptions import ETLPipelineError
from python_core.utils.logger import ERPLogger

_log = ERPLogger.get_logger("etl.transformer")


# ══════════════════════════════════════════════════════════════
#  STUDENT DATA TRANSFORMER
# ══════════════════════════════════════════════════════════════
class StudentDataTransformer(BaseTransformer):
    """
    Normalises raw student records into the canonical schema
    expected by the Student model.

    Handles:
      • Name casing / trimming
      • Email lowercasing
      • Date parsing (multiple formats)
      • Status normalisation
      • GPA clamping
    """

    DATE_FORMATS = ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%Y%m%d", "%d-%m-%Y")

    def transform(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        _log.info("Transforming %d student records", len(data))
        transformed: List[Dict[str, Any]] = []

        for idx, record in enumerate(data):
            try:
                transformed.append(self._transform_record(record))
            except Exception as exc:
                _log.warning("Skipping record %d: %s", idx, exc)

        _log.info("Transformed %d / %d records", len(transformed), len(data))
        return transformed

    def _transform_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        result: Dict[str, Any] = {}

        # Name
        result["first_name"] = self._clean_name(record.get("first_name", ""))
        result["last_name"] = self._clean_name(record.get("last_name", ""))

        # Email
        email = str(record.get("email", "")).strip().lower()
        result["email"] = email

        # DOB
        result["date_of_birth"] = self._parse_date(record.get("date_of_birth", ""))

        # Department
        result["department_id"] = str(record.get("department_id", "")).strip()

        # Status
        status = str(record.get("status", "active")).strip().lower()
        result["status"] = status if status in (
            "active", "inactive", "graduated", "suspended", "on_leave"
        ) else "active"

        # GPA
        try:
            gpa = float(record.get("gpa", 0.0))
            result["gpa"] = max(0.0, min(4.0, gpa))
        except (ValueError, TypeError):
            result["gpa"] = 0.0

        # Dates
        if record.get("enrollment_date"):
            result["enrollment_date"] = self._parse_date(record["enrollment_date"])

        # Pass-through: preserve ALL keys not already handled
        handled_keys = {
            "first_name", "last_name", "email", "date_of_birth",
            "department_id", "status", "gpa", "enrollment_date",
        }
        for key, value in record.items():
            if key not in handled_keys and key not in result:
                result[key] = value

        return result

    @staticmethod
    def _clean_name(name: Any) -> str:
        return str(name).strip().title()

    def _parse_date(self, value: Any) -> str:
        """Attempt multiple date formats and return ISO string."""
        if isinstance(value, (date, datetime)):
            return value.isoformat()[:10]
        text = str(value).strip()
        for fmt in self.DATE_FORMATS:
            try:
                return datetime.strptime(text, fmt).date().isoformat()
            except ValueError:
                continue
        raise ETLPipelineError("Transformer", f"Cannot parse date: {value}")


# ══════════════════════════════════════════════════════════════
#  GRADE NORMALIZER
# ══════════════════════════════════════════════════════════════
class GradeNormalizer(BaseTransformer):
    """
    Normalises grade records:
      • Uppercase letter grades
      • Validate grade-point ranges
      • Map numeric scores → letter grades (optional)
    """

    SCORE_TO_GRADE = [
        (93, "A"), (90, "A-"), (87, "B+"), (83, "B"), (80, "B-"),
        (77, "C+"), (73, "C"), (70, "C-"), (67, "D+"), (63, "D"),
        (60, "D-"), (0, "F"),
    ]

    def transform(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        _log.info("Normalising %d grade records", len(data))
        result = []
        for record in data:
            rec = dict(record)
            if "numeric_score" in rec and "grade" not in rec:
                rec["grade"] = self._score_to_letter(float(rec["numeric_score"]))
            if "grade" in rec:
                rec["grade"] = str(rec["grade"]).strip().upper()
            result.append(rec)
        return result

    def _score_to_letter(self, score: float) -> str:
        for threshold, letter in self.SCORE_TO_GRADE:
            if score >= threshold:
                return letter
        return "F"


# ══════════════════════════════════════════════════════════════
#  CHAINED TRANSFORMER  (Decorator / Composite)
# ══════════════════════════════════════════════════════════════
class ChainedTransformer(BaseTransformer):
    """
    Composes multiple transformers in sequence.

        chain = ChainedTransformer([StudentDataTransformer(), GradeNormalizer()])
        result = chain.transform(raw_data)
    """

    def __init__(self, transformers: List[BaseTransformer]) -> None:
        if not transformers:
            raise ETLPipelineError("Transformer", "ChainedTransformer requires at least one transformer")
        self._transformers = transformers

    def transform(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        result = data
        for transformer in self._transformers:
            _log.debug("Running %s", transformer.__class__.__name__)
            result = transformer.transform(result)
        return result
