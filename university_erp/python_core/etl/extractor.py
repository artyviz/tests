"""
University ERP — ETL Extractor

BaseExtractor ABC + concrete implementations for CSV, JSON,
and database sources.  New extractors can be hot-swapped via
settings.yaml without code changes.
"""

from __future__ import annotations

import csv
import io
import json
import os
from typing import Any, Dict, List, Optional

from python_core.base import BaseExtractor
from python_core.utils.exceptions import ETLPipelineError
from python_core.utils.logger import ERPLogger

_log = ERPLogger.get_logger("etl.extractor")


# ══════════════════════════════════════════════════════════════
#  CSV  EXTRACTOR
# ══════════════════════════════════════════════════════════════
class CSVExtractor(BaseExtractor):
    """
    Extracts records from a CSV file or an in-memory CSV string.

    `source` can be:
      • A file path (str) ending in .csv
      • A string containing raw CSV text
    """

    def __init__(self, *, delimiter: str = ",", encoding: str = "utf-8") -> None:
        self._delimiter = delimiter
        self._encoding = encoding

    def extract(self, source: Any) -> List[Dict[str, Any]]:
        try:
            if isinstance(source, str) and os.path.isfile(source):
                _log.info("Extracting CSV from file: %s", source)
                with open(source, newline="", encoding=self._encoding) as fh:
                    reader = csv.DictReader(fh, delimiter=self._delimiter)
                    return [dict(row) for row in reader]
            elif isinstance(source, str):
                _log.info("Extracting CSV from in-memory string (%d chars)", len(source))
                reader = csv.DictReader(
                    io.StringIO(source), delimiter=self._delimiter
                )
                return [dict(row) for row in reader]
            else:
                raise ETLPipelineError(
                    "Extractor",
                    f"Unsupported CSV source type: {type(source).__name__}",
                )
        except ETLPipelineError:
            raise
        except Exception as exc:
            raise ETLPipelineError("Extractor", f"CSV extraction failed: {exc}") from exc


# ══════════════════════════════════════════════════════════════
#  JSON  EXTRACTOR
# ══════════════════════════════════════════════════════════════
class JSONExtractor(BaseExtractor):
    """
    Extracts records from a JSON file or string.

    The top-level structure must be a list of objects, or an
    object containing a key (configurable) that maps to such a list.
    """

    def __init__(self, *, array_key: Optional[str] = None) -> None:
        self._array_key = array_key  # e.g. "students" in {"students": [...]}

    def extract(self, source: Any) -> List[Dict[str, Any]]:
        try:
            if isinstance(source, str) and os.path.isfile(source):
                _log.info("Extracting JSON from file: %s", source)
                with open(source, encoding="utf-8") as fh:
                    raw = json.load(fh)
            elif isinstance(source, str):
                _log.info("Extracting JSON from string (%d chars)", len(source))
                raw = json.loads(source)
            elif isinstance(source, (list, dict)):
                raw = source
            else:
                raise ETLPipelineError(
                    "Extractor",
                    f"Unsupported JSON source type: {type(source).__name__}",
                )

            if isinstance(raw, list):
                return raw
            if isinstance(raw, dict) and self._array_key:
                return raw[self._array_key]
            if isinstance(raw, dict):
                # try first list-valued key
                for val in raw.values():
                    if isinstance(val, list):
                        return val
                raise ETLPipelineError(
                    "Extractor",
                    "JSON object has no array key; set array_key in constructor",
                )
            raise ETLPipelineError("Extractor", "Unexpected JSON structure")
        except ETLPipelineError:
            raise
        except Exception as exc:
            raise ETLPipelineError("Extractor", f"JSON extraction failed: {exc}") from exc


# ══════════════════════════════════════════════════════════════
#  DATABASE  EXTRACTOR
# ══════════════════════════════════════════════════════════════
class DatabaseExtractor(BaseExtractor):
    """
    Extracts records by executing a SQL query against a database
    connection.

    `source` must be a dict with keys:
      • "connection" — a DB-API 2.0 connection object
      • "query"      — the SQL SELECT statement
      • "params"     — optional query parameters (tuple)
    """

    def extract(self, source: Any) -> List[Dict[str, Any]]:
        if not isinstance(source, dict):
            raise ETLPipelineError(
                "Extractor",
                "DatabaseExtractor expects a dict with 'connection' and 'query'",
            )
        conn = source.get("connection")
        query = source.get("query")
        params = source.get("params", ())

        if not conn or not query:
            raise ETLPipelineError(
                "Extractor", "Missing 'connection' or 'query' in source dict"
            )

        try:
            _log.info("Extracting from database: %s", query[:120])
            cursor = conn.cursor()
            cursor.execute(query, params)
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
            _log.info("Extracted %d rows", len(rows))
            return [dict(zip(columns, row)) for row in rows]
        except Exception as exc:
            raise ETLPipelineError("Extractor", f"Database extraction failed: {exc}") from exc
