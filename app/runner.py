"""Runs a user's submitted Python code against test cases in a separate
subprocess (real isolation + hard timeout), and reports pass/fail per case.

Only for Python submissions right now. Not sandboxed against malicious code
(no seccomp/docker) -- fine for a local, single-user tool running code you
wrote yourself, but don't paste code you don't trust.
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

TIMEOUT_SECONDS = 5

HARNESS_TEMPLATE = """
import json, traceback

{user_code}

_cases = json.loads({cases_json!r})
_results = []
for _args, _expected in _cases:
    entry = {{"input": _args, "expected": _expected}}
    try:
        actual = solve(*_args)
        entry["actual"] = actual
        entry["passed"] = actual == _expected
    except Exception as e:
        entry["actual"] = None
        entry["passed"] = False
        entry["error"] = f"{{type(e).__name__}}: {{e}}"
    _results.append(entry)

print("__RESULTS_JSON__" + json.dumps(_results))
"""


def run_submission(code: str, test_cases: list[tuple[list, object]]) -> dict:
    """test_cases: list of (args_list, expected_value).

    Returns {"ok": bool, "results": [...], "error": str | None}
    """
    cases_json = json.dumps(test_cases)
    script = HARNESS_TEMPLATE.format(user_code=code, cases_json=cases_json)

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, encoding="utf-8"
    ) as f:
        f.write(script)
        tmp_path = Path(f.name)

    try:
        proc = subprocess.run(
            [sys.executable, str(tmp_path)],
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "results": [], "error": f"Timed out after {TIMEOUT_SECONDS}s"}
    finally:
        tmp_path.unlink(missing_ok=True)

    marker = "__RESULTS_JSON__"
    if marker in proc.stdout:
        results = json.loads(proc.stdout.split(marker, 1)[1].strip())
        return {"ok": True, "results": results, "error": None}

    # code failed before printing results (syntax error, missing solve(), etc)
    return {"ok": False, "results": [], "error": proc.stderr.strip() or "Unknown error"}
