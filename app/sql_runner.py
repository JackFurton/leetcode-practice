"""Runs a SQL submission against a real SQLite database: stand up the
problem's schema fresh in memory, run the submitted query, compare the
result set to the expected rows (order-insensitive, LC-style, unless the
problem's query itself sorts). Same idea as runner.py/go_runner.py: real
execution, not string matching.

Only a single SELECT is allowed. Anything else (multiple statements, or a
statement that isn't a SELECT/WITH) is rejected before it touches the
database -- this is a local single-user tool with no sandboxing (see the
README's security note), so the goal here is catching accidents, not
malicious input.
"""
import json
import re
import sqlite3

TIMEOUT_SECONDS = 5

_DISALLOWED = re.compile(
    r"\b(insert|update|delete|drop|alter|create|attach|detach|pragma|vacuum|replace)\b",
    re.IGNORECASE,
)


def sql_default_starter_code() -> str:
    return "-- write your query below\nSELECT"


def is_unedited(code: str, starter_code: str) -> bool:
    return code.strip() == starter_code.strip()


def _validate_query(query: str) -> str | None:
    stripped = query.strip().rstrip(";").strip()
    if not stripped:
        return "Empty query."
    if ";" in stripped:
        return "Only a single SELECT statement is allowed (no semicolons)."
    if not re.match(r"^(select|with)\b", stripped, re.IGNORECASE):
        return "Query must be a SELECT (or a WITH ... SELECT)."
    if _DISALLOWED.search(stripped):
        return "Only read-only SELECT queries are allowed here."
    return None


def run_sql_submission(
    query: str,
    setup_sql: str,
    expected_columns: list[str],
    expected_rows: list[list],
) -> dict:
    """Returns {"ok": bool, "results": [...], "error": str | None}, same
    shape as runner.run_submission / go_runner.run_go_submission so the
    TUI/web result rendering doesn't need a special case."""
    error = _validate_query(query)
    if error:
        return {"ok": False, "results": [], "error": error}

    conn = sqlite3.connect(":memory:", timeout=TIMEOUT_SECONDS)
    try:
        conn.executescript(setup_sql)
    except sqlite3.Error as e:
        conn.close()
        return {"ok": False, "results": [], "error": f"Schema setup failed: {e}"}

    try:
        cursor = conn.execute(query.strip().rstrip(";"))
        actual_columns = [d[0] for d in cursor.description] if cursor.description else []
        actual_rows = [list(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        conn.close()
        return {"ok": False, "results": [], "error": f"Query failed: {e}"}
    finally:
        conn.close()

    def _normalize(rows: list[list]) -> list[tuple]:
        return sorted(tuple(json.loads(json.dumps(v)) for v in row) for row in rows)

    columns_match = actual_columns == expected_columns
    rows_match = _normalize(actual_rows) == _normalize(expected_rows)
    passed = columns_match and rows_match

    detail = None
    if not columns_match:
        detail = f"expected columns {expected_columns}, got {actual_columns}"

    return {
        "ok": True,
        "results": [
            {
                "input": None,
                "expected": expected_rows,
                "actual": actual_rows,
                "passed": passed,
                "detail": detail,
            }
        ],
        "error": None,
    }
