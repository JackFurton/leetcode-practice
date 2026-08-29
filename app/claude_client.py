import os
from pathlib import Path

import anthropic
from dotenv import load_dotenv

load_dotenv()

MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-5")


def _resolve_api_key() -> str:
    key = os.environ.get("ANTHROPIC_API_KEY")
    if key:
        return key
    key_file = os.environ.get("ANTHROPIC_API_KEY_FILE")
    if key_file:
        path = Path(key_file).expanduser()
        if path.exists():
            return path.read_text().strip()
    raise RuntimeError(
        "No Anthropic API key found. Set ANTHROPIC_API_KEY or ANTHROPIC_API_KEY_FILE in .env"
    )


_client: anthropic.Anthropic | None = None


def get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=_resolve_api_key())
    return _client


REVIEW_SYSTEM_PROMPT = """You are a patient coding mentor helping a beginner-to-intermediate \
engineer get comfortable passing Medium-difficulty LeetCode problems within about a year. \
They have a cloud engineering background but are newer to DS&A and coding-interview-style problem solving.

For every submission, respond in this structure, concise, no fluff:

**Correctness**: did it pass? If not, what's the actual bug (be specific, point at the line/logic).
**Complexity**: time and space, in Big-O, one line explaining why.
**Feedback**: 1-3 concrete things about their approach or code style, ranked most important first.
**Next step**: one specific, actionable suggestion (a pattern to review, an edge case to consider, \
or a follow-up variant to try).

Keep it tight. Assume they want to learn, not be flattered."""


def review_submission(
    problem_title: str,
    problem_notes: str | None,
    difficulty: str,
    code: str,
    run_result: dict,
) -> str:
    passed_count = sum(1 for r in run_result["results"] if r.get("passed"))
    total = len(run_result["results"])

    lines = [
        f"Problem: {problem_title} ({difficulty})",
    ]
    if problem_notes:
        lines.append(f"Notes/description: {problem_notes}")
    lines.append(f"\nSubmitted code:\n```python\n{code}\n```")

    if run_result["error"]:
        lines.append(f"\nExecution error: {run_result['error']}")
    else:
        lines.append(f"\nTest results: {passed_count}/{total} passed")
        for i, r in enumerate(run_result["results"]):
            status = "PASS" if r.get("passed") else "FAIL"
            lines.append(
                f"  Case {i + 1} [{status}]: input={r['input']} expected={r['expected']} "
                f"actual={r.get('actual')} {r.get('error', '')}"
            )

    user_message = "\n".join(lines)

    response = get_client().messages.create(
        model=MODEL,
        max_tokens=1024,
        system=REVIEW_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )
    return response.content[0].text
