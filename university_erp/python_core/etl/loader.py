"""
University ERP — ETL Loader

BaseLoader ABC + concrete implementations for Database,
CSV, and JSON destinations.
"""

from __future__ import annotations

import csv
import json
import os
from typing import Any, Dict, List, Optional

from python_core.base import BaseLoader
from python_core.utils.exceptions import ETLPipelineError
from python_core.utils.logger import ERPLogger

_log = ERPLogger.get_logger("etl.loader")


# ══════════════════════════════════════════════════════════════
#  DATABASE LOADER
# ══════════════════════════════════════════════════════════════
class DatabaseLoader(BaseLoader):
    """
    Loads records into a PostgreSQL table using batch inserts.

    `destination` must be a dict with:
      • "connection" — DB-API 2.0 connection
      • "table"      — target table name
      • "columns"    — optional list[str] column whitelist
    """

    def __init__(self, *, batch_size: int = 500) -> None:
        self._batch_size = batch_size

    def load(self, data: List[Dict[str, Any]], destination: Any) -> int:
        if not isinstance(destination, dict):
            raise ETLPipelineError("Loader", "DatabaseLoader expects dict destination")

        conn = destination.get("connection")
        table = destination.get("table")
        columns = destination.get("columns")

        if not conn or not table:
            raise ETLPipelineError("Loader", "Missing 'connection' or 'table'")

        if not data:
            _log.info("No data to load — skipping")
            return 0

        # Determine columns from first record if not specified
        if not columns:
            columns = list(data[0].keys())

        col_str = ", ".join(columns)
        placeholders = ", ".join(["%s"] * len(columns))
        sql = f"INSERT INTO {table} ({col_str}) VALUES ({placeholders})"

        loaded = 0
        try:
            cursor = conn.cursor()
            for i in range(0, len(data), self._batch_size):
                batch = data[i : i + self._batch_size]
                values = [tuple(row.get(c) for c in columns) for row in batch]
                cursor.executemany(sql, values)
                loaded += len(batch)
                _log.debug("Loaded batch %d–%d", i, i + len(batch))
            conn.commit()
            _log.info("Successfully loaded %d records into %s", loaded, table)
        except Exception as exc:
            conn.rollback()
            raise ETLPipelineError("Loader", f"Database load failed: {exc}") from exc

        return loaded


# ══════════════════════════════════════════════════════════════
#  CSV LOADER
# ══════════════════════════════════════════════════════════════
class CSVLoader(BaseLoader):
    """
    Writes records to a CSV file.

    `destination` — file path (str).
    """

    def __init__(self, *, delimiter: str = ",", encoding: str = "utf-8") -> None:
        self._delimiter = delimiter
        self._encoding = encoding

    def load(self, data: List[Dict[str, Any]], destination: Any) -> int:
        if not isinstance(destination, str):
            raise ETLPipelineError("Loader", "CSVLoader expects a file path string")
        if not data:
            _log.info("No data to load — skipping")
            return 0

        try:
            os.makedirs(os.path.dirname(destination) or ".", exist_ok=True)
            fieldnames = list(data[0].keys())
            with open(destination, "w", newline="", encoding=self._encoding) as fh:
                writer = csv.DictWriter(
                    fh, fieldnames=fieldnames, delimiter=self._delimiter
                )
                writer.writeheader()
                writer.writerows(data)
            _log.info("Wrote %d records to %s", len(data), destination)
            return len(data)
        except Exception as exc:
            raise ETLPipelineError("Loader", f"CSV write failed: {exc}") from exc


# ══════════════════════════════════════════════════════════════
#  JSON LOADER
# ══════════════════════════════════════════════════════════════
class JSONLoader(BaseLoader):
    """
    Writes records to a JSON file.

    `destination` — file path (str).
    """

    def __init__(self, *, indent: int = 2) -> None:
        self._indent = indent

    def load(self, data: List[Dict[str, Any]], destination: Any) -> int:
        if not isinstance(destination, str):
            raise ETLPipelineError("Loader", "JSONLoader expects a file path string")
        if not data:
            _log.info("No data to load — skipping")
            return 0

        try:
            os.makedirs(os.path.dirname(destination) or ".", exist_ok=True)
            with open(destination, "w", encoding="utf-8") as fh:
                json.dump(data, fh, indent=self._indent, default=str)
            _log.info("Wrote %d records to %s", len(data), destination)
            return len(data)
        except Exception as exc:
            raise ETLPipelineError("Loader", f"JSON write failed: {exc}") from exc
