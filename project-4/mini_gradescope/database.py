import json
import os
from dataclasses import asdict
from typing import Any

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")

_TABLES = ("assignments", "submissions", "grades")


def _path(table: str) -> str:
    return os.path.join(DATA_DIR, f"{table}.json")


def _load(table: str) -> dict[str, Any]:
    p = _path(table)
    if not os.path.exists(p):
        return {}
    with open(p) as f:
        return json.load(f)


def _save(table: str, data: dict[str, Any]) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(_path(table), "w") as f:
        json.dump(data, f, indent=2)


def insert(table: str, record) -> None:
    data = _load(table)
    data[record.id] = asdict(record)
    _save(table, data)


def get(table: str, record_id: str) -> dict[str, Any] | None:
    return _load(table).get(record_id)


def all_records(table: str) -> list[dict[str, Any]]:
    return list(_load(table).values())


def find(table: str, **filters) -> list[dict[str, Any]]:
    results = []
    for record in _load(table).values():
        if all(record.get(k) == v for k, v in filters.items()):
            results.append(record)
    return results


def reset() -> None:
    """Clear all data (useful for testing)."""
    for table in _TABLES:
        p = _path(table)
        if os.path.exists(p):
            os.remove(p)
