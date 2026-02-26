"""
University ERP — PostgreSQL Repository (Base)

Implements BaseRepository for PostgreSQL using psycopg2
connection pooling with the Repository pattern.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Type

from python_core.base import BaseModel, BaseRepository
from python_core.utils.exceptions import RepositoryError
from python_core.utils.logger import ERPLogger

_log = ERPLogger.get_logger("repository.base")


class PostgresRepository(BaseRepository[BaseModel]):
    """
    Base PostgreSQL repository.

    Subclasses must set:
      • _table_name  — the DB table
      • _model_class — the BaseModel subclass for deserialisation
      • _columns     — ordered list of column names

    Constructor receives a DB-API 2.0 connection (or pool).
    """

    _table_name: str = ""
    _model_class: Type[BaseModel] = BaseModel  # overridden by subclasses
    _columns: List[str] = []

    def __init__(self, connection: Any) -> None:
        self._conn = connection

    # ── BaseRepository interface implementation ──────────────
    def find_by_id(self, entity_id: str) -> Optional[BaseModel]:
        sql = f"SELECT * FROM {self._table_name} WHERE id = %s"
        try:
            cursor = self._conn.cursor()
            cursor.execute(sql, (entity_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return self._row_to_model(cursor.description, row)
        except Exception as exc:
            raise RepositoryError("find_by_id", str(exc)) from exc

    def find_all(
        self,
        *,
        limit: int = 100,
        offset: int = 0,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[BaseModel]:
        where, params = self._build_where(filters)
        sql = f"SELECT * FROM {self._table_name}{where} ORDER BY created_at DESC LIMIT %s OFFSET %s"
        params.extend([limit, offset])
        try:
            cursor = self._conn.cursor()
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            return [self._row_to_model(cursor.description, r) for r in rows]
        except Exception as exc:
            raise RepositoryError("find_all", str(exc)) from exc

    def save(self, entity: BaseModel) -> BaseModel:
        entity.validate()
        data = entity.to_dict()
        columns = [c for c in self._columns if c in data]
        col_str = ", ".join(columns)
        placeholders = ", ".join(["%s"] * len(columns))
        values = [data[c] for c in columns]
        sql = f"INSERT INTO {self._table_name} ({col_str}) VALUES ({placeholders}) RETURNING *"
        try:
            cursor = self._conn.cursor()
            cursor.execute(sql, values)
            self._conn.commit()
            row = cursor.fetchone()
            _log.info("Saved %s id=%s", self._table_name, entity.id)
            return self._row_to_model(cursor.description, row) if row else entity
        except Exception as exc:
            self._conn.rollback()
            raise RepositoryError("save", str(exc)) from exc

    def update(self, entity: BaseModel) -> BaseModel:
        entity.validate()
        entity.touch()
        data = entity.to_dict()
        columns = [c for c in self._columns if c in data and c != "id"]
        set_clause = ", ".join(f"{c} = %s" for c in columns)
        values = [data[c] for c in columns]
        values.append(entity.id)
        sql = f"UPDATE {self._table_name} SET {set_clause} WHERE id = %s RETURNING *"
        try:
            cursor = self._conn.cursor()
            cursor.execute(sql, values)
            self._conn.commit()
            row = cursor.fetchone()
            _log.info("Updated %s id=%s", self._table_name, entity.id)
            return self._row_to_model(cursor.description, row) if row else entity
        except Exception as exc:
            self._conn.rollback()
            raise RepositoryError("update", str(exc)) from exc

    def delete(self, entity_id: str) -> bool:
        sql = f"DELETE FROM {self._table_name} WHERE id = %s"
        try:
            cursor = self._conn.cursor()
            cursor.execute(sql, (entity_id,))
            self._conn.commit()
            deleted = cursor.rowcount > 0
            if deleted:
                _log.info("Deleted %s id=%s", self._table_name, entity_id)
            return deleted
        except Exception as exc:
            self._conn.rollback()
            raise RepositoryError("delete", str(exc)) from exc

    def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        where, params = self._build_where(filters)
        sql = f"SELECT COUNT(*) FROM {self._table_name}{where}"
        try:
            cursor = self._conn.cursor()
            cursor.execute(sql, params)
            result = cursor.fetchone()
            return result[0] if result else 0
        except Exception as exc:
            raise RepositoryError("count", str(exc)) from exc

    # ── Helpers ──────────────────────────────────────────────
    def _row_to_model(self, description: Any, row: tuple) -> BaseModel:
        columns = [d[0] for d in description]
        data = dict(zip(columns, row))
        return self._model_class.from_dict(data)

    @staticmethod
    def _build_where(
        filters: Optional[Dict[str, Any]],
    ) -> tuple:
        """Build a WHERE clause from a filters dict."""
        if not filters:
            return "", []
        clauses = []
        params: list = []
        for key, value in filters.items():
            if isinstance(value, list):
                placeholders = ", ".join(["%s"] * len(value))
                clauses.append(f"{key} IN ({placeholders})")
                params.extend(value)
            else:
                clauses.append(f"{key} = %s")
                params.append(value)
        where = " WHERE " + " AND ".join(clauses)
        return where, params
