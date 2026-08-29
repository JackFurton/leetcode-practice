# LC Trainer

Local webapp to practice LeetCode-style problems (paired with algo.monster),
submit code, and get an automated review from Claude on correctness,
complexity, and style. Goal: comfortably pass Mediums within a year.

## Stack

- FastAPI + Jinja2 + HTMX (server-rendered, minimal JS)
- SQLite (via SQLModel) for problems / test cases / submission history
- Anthropic API for code review

## Setup

```bash
cd LC
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# edit .env: either set ANTHROPIC_API_KEY directly, or point
# ANTHROPIC_API_KEY_FILE at a file containing the key (defaults to
# ~/.antrhopic_key if you set that env var)

uvicorn app.main:app --reload
```

Visit http://localhost:8000

## How it works

1. Add a problem (title, link to algo.monster/leetcode, difficulty, topic, notes).
2. Add test cases as JSON: input is a list of positional args, expected is the
   return value. Your submitted code must define `def solve(*args): ...`.
3. Paste your solution and hit "Run + Review". Code runs in a subprocess
   (5s timeout) against your test cases, then the code + results get sent to
   Claude for a structured review: correctness, time/space complexity,
   style feedback, and one concrete next step.
4. Every submission is saved to history on the problem page so you can track
   how your solutions evolve over time.

## Security note

Code execution is a subprocess with a timeout, not a full sandbox (no
docker/seccomp). Fine for a local, single-user tool running code you wrote
yourself. Don't paste code you don't trust.

## Roadmap ideas

- Learning modules / topic checklists (arrays, two pointers, DP, graphs, ...)
- Pull problem descriptions automatically from algo.monster/leetcode links
- Multi-language support (Go, Java, C++, Rust) once Python habits are solid
- Spaced-repetition style resurfacing of previously-solved problems
