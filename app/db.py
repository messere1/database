from __future__ import annotations

import re
from collections.abc import Generator
from typing import Any

from sqlalchemy import text

from app.core.config import get_settings

settings = get_settings()


class _OpenGaussRow:
    def __init__(self, mapping: dict[str, Any]) -> None:
        self._mapping = mapping


class _OpenGaussMappings:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self._rows = rows

    def first(self) -> dict[str, Any] | None:
        return self._rows[0] if self._rows else None


class _OpenGaussResult:
    def __init__(self, columns: list[str], rows: list[tuple[Any, ...]]) -> None:
        self._dict_rows = [dict(zip(columns, row)) for row in rows]
        self._rows = [_OpenGaussRow(mapping) for mapping in self._dict_rows]

    def __iter__(self):
        return iter(self._rows)

    def mappings(self) -> _OpenGaussMappings:
        return _OpenGaussMappings(self._dict_rows)


PARAM_PATTERN = re.compile(r"(?<!:):([A-Za-z_][A-Za-z0-9_]*)")


def _convert_named_params(sql: str, params: dict[str, Any]) -> tuple[str, tuple[Any, ...]]:
    if not params:
        return sql, ()

    converted_sql = sql
    for name, value in params.items():
        null_check_pattern = re.compile(rf"(?<!:):{re.escape(name)}\s+IS\s+NULL", re.IGNORECASE)
        converted_sql = null_check_pattern.sub("TRUE" if value is None else "FALSE", converted_sql)

    ordered_names: list[str] = []
    name_to_index: dict[str, int] = {}

    def replace_param(match: re.Match[str]) -> str:
        name = match.group(1)
        if name not in params:
            raise KeyError(f"Missing SQL parameter: {name}")
        if name not in name_to_index:
            name_to_index[name] = len(ordered_names) + 1
            ordered_names.append(name)
        return f"${name_to_index[name]}"

    converted_sql = PARAM_PATTERN.sub(replace_param, converted_sql)
    values = tuple(params[name] for name in ordered_names)
    return converted_sql, values


class OpenGaussSession:
    def __init__(self) -> None:
        try:
            import py_opengauss
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("py-opengauss is required to run this project") from exc

        if not settings.og_host or not settings.og_database or not settings.og_user:
            raise RuntimeError("Missing OG_HOST/OG_DATABASE/OG_USER in environment for openGauss backend")

        self._db = py_opengauss.open(
            settings.opengauss_iri,
            password=settings.og_password,
            sslmode=settings.og_sslmode,
            connect_timeout=settings.og_connect_timeout,
        )

        schema = settings.og_schema.replace('"', '""')
        self._db.execute(f'SET search_path TO "{schema}";')

    def execute(self, statement: Any, params: dict[str, Any] | None = None) -> _OpenGaussResult:
        sql = str(statement)
        converted_sql, values = _convert_named_params(sql, params or {})
        prepared = self._db.prepare(converted_sql)
        rows = prepared(*values) if values else prepared()
        return _OpenGaussResult(list(prepared.column_names), rows)

    def close(self) -> None:
        self._db.close()


def get_db() -> Generator[Any, None, None]:
    db: Any = OpenGaussSession()

    try:
        yield db
    finally:
        db.close()


def check_db_health() -> bool:
    db = OpenGaussSession()
    try:
        db.execute(text("SELECT 1"))
    finally:
        db.close()

    return True
