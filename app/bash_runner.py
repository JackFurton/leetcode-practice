"""Runs a bash submission against real test cases: pipe stdin in, run the
script with real `bash`, compare stdout. Same idea as the other runners
(real execution, hard timeout), but bash is meaningfully more dangerous
than the sandboxed languages -- it's not an interpreter running a program,
it's literally shell commands (rm, curl, anything on PATH). This is still
not a sandbox (see the README's security note): the only extra precaution
here is running with cwd set to a disposable temp directory instead of the
project (or the user's home), so a destructive mistake in a submission
lands somewhere throwaway rather than somewhere that matters.
"""
import subprocess
import tempfile

TIMEOUT_SECONDS = 5


def bash_default_starter_code() -> str:
    return "#!/usr/bin/env bash\n# read from stdin, write to stdout\n"


def is_unedited(code: str, starter_code: str) -> bool:
    return code.strip() == starter_code.strip()


def run_bash_submission(script: str, test_cases: list[tuple[str, str]]) -> dict:
    """test_cases: list of (stdin_text, expected_stdout). Returns
    {"ok": bool, "results": [...], "error": str | None}, same shape as the
    other runners."""
    results = []
    with tempfile.TemporaryDirectory(prefix="lc-bash-") as scratch_dir:
        for stdin_text, expected in test_cases:
            try:
                proc = subprocess.run(
                    ["bash", "-c", script],
                    input=stdin_text,
                    capture_output=True,
                    text=True,
                    timeout=TIMEOUT_SECONDS,
                    cwd=scratch_dir,
                )
            except subprocess.TimeoutExpired:
                return {
                    "ok": False,
                    "results": results,
                    "error": f"Timed out after {TIMEOUT_SECONDS}s",
                }
            except FileNotFoundError:
                return {
                    "ok": False,
                    "results": [],
                    "error": "bash not found on PATH.",
                }

            actual = proc.stdout
            passed = actual.rstrip("\n") == expected.rstrip("\n")
            entry = {
                "input": stdin_text,
                "expected": expected,
                "actual": actual,
                "passed": passed,
            }
            if not passed and proc.stderr.strip():
                entry["detail"] = proc.stderr.strip()
            results.append(entry)

    return {"ok": True, "results": results, "error": None}
