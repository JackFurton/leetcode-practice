"""Runs a Go submission against real test cases, compiled and executed via
`go run` in a subprocess (real isolation, hard timeout, same idea as
runner.py's Python harness).

Go is statically typed, so unlike Python's `def solve(*args)` we can't just
json.loads the test cases and splat them in at runtime -- each problem needs
to declare its argument/return types (ProblemStarter.arg_types/return_type),
and the harness renders every test case as an actual typed Go literal at
generation time (e.g. JSON [2, 7, 11, 15] + type "[]int" -> the Go source
text "[]int{2, 7, 11, 15}"). No structure-wrapper (linked list / tree)
support yet, only primitive/slice types -- see runner.py's docstring for
the wrapper convention those will eventually need to match.
"""
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

TIMEOUT_SECONDS = 20  # go run compiles + runs; a bit more headroom than Python


def go_default_starter_code(function_name: str) -> str:
    return f"func {function_name}() {{\n\t// WRITE YOUR BRILLIANT CODE HERE\n}}"


def is_unedited(code: str, starter_code: str) -> bool:
    return code.strip() == starter_code.strip()


def _go_literal(value, go_type: str) -> str:
    if go_type == "int":
        return str(value)
    if go_type == "bool":
        return "true" if value else "false"
    if go_type == "string":
        return json.dumps(value)
    if go_type.startswith("[]"):
        inner = go_type[2:]
        items = ", ".join(_go_literal(v, inner) for v in value)
        return f"{go_type}{{{items}}}"
    raise ValueError(f"unsupported Go type for literal rendering: {go_type!r}")


def run_go_submission(
    code: str,
    test_cases: list[tuple[list, object]],
    function_name: str,
    arg_types: list[str],
    return_type: str,
) -> dict:
    """test_cases: list of (args_list, expected_value), same shape as
    runner.run_submission. Returns {"ok": bool, "results": [...], "error": str | None}."""
    if not shutil.which("go"):
        return {
            "ok": False,
            "results": [],
            "error": "Go toolchain not found. Install it from https://go.dev/dl/ "
            "and make sure `go` is on your PATH.",
        }

    if not function_name.isidentifier():
        raise ValueError(f"Invalid function_name: {function_name!r}")

    blocks = []
    for args, expected in test_cases:
        try:
            arg_literals = ", ".join(_go_literal(a, t) for a, t in zip(args, arg_types))
            expected_literal = _go_literal(expected, return_type)
        except (ValueError, TypeError) as e:
            return {"ok": False, "results": [], "error": f"Bad test case data: {e}"}
        blocks.append(
            "\t{\n"
            f"\t\tactual := {function_name}({arg_literals})\n"
            f"\t\texpected := {expected_literal}\n"
            "\t\tresults = append(results, __result{"
            "Expected: expected, Actual: actual, Passed: reflect.DeepEqual(actual, expected)"
            "})\n"
            "\t}\n"
        )

    script = (
        "package main\n\n"
        'import (\n\t"encoding/json"\n\t"fmt"\n\t"reflect"\n)\n\n'
        f"{code}\n\n"
        "type __result struct {\n"
        '\tExpected interface{} `json:"expected"`\n'
        '\tActual   interface{} `json:"actual"`\n'
        '\tPassed   bool        `json:"passed"`\n'
        "}\n\n"
        "func main() {\n"
        "\tvar results []__result\n\n"
        + "".join(blocks)
        + '\n\tout, _ := json.Marshal(results)\n'
        '\tfmt.Println("__RESULTS_JSON__" + string(out))\n'
        "}\n"
    )

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".go", delete=False, encoding="utf-8"
    ) as f:
        f.write(script)
        tmp_path = Path(f.name)

    try:
        proc = subprocess.run(
            ["go", "run", str(tmp_path)],
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
        raw_results = json.loads(proc.stdout.split(marker, 1)[1].strip())
        results = []
        for (args, _expected), r in zip(test_cases, raw_results):
            results.append(
                {
                    "input": args,
                    "expected": r["expected"],
                    "actual": r["actual"],
                    "passed": r["passed"],
                }
            )
        return {"ok": True, "results": results, "error": None}

    # compile error or panic before the marker was printed
    return {"ok": False, "results": [], "error": proc.stderr.strip() or "Unknown error"}
