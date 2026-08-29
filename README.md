# LC Trainer

Practice LeetCode-style problems (paired with algo.monster), submit code, and
get an automated review from Claude on correctness, complexity, and style.
Goal: comfortably pass Mediums within a year. Two front ends, same local
SQLite data underneath: a terminal UI and a web UI.

## Setup

```bash
cd leetcode-practice
./start.sh   # terminal UI (default)
./web.sh     # web UI, opens Chrome
```

First run creates a venv, installs deps, and copies `.env.example` to `.env`
(already points at `~/.antrhopic_key`, edit it if your key lives elsewhere).
Both scripts seed a 27-problem starter catalog on first boot (instant, no
network call, the data's baked in).

## Terminal UI

`./start.sh` drops you straight into a Textual-based TUI, no browser needed:

- **Dashboard**: overall progress, per-difficulty breakdown, streak, per-pattern
  progress bars, "continue where you left off", due-for-review.
- **Problems** (`p`): sortable list (`t`/`d`/`s` for title/difficulty/status),
  enter a row to open it.
- **Problem detail**: description, constraints, examples, a code editor, run +
  review, get a hint, reveal a full solution (cached after first pull),
  personal notes.
- **Learn** (`l`): pattern checklist by category, space to toggle done,
  select a topic to see its explanation + template.

`escape` goes back a screen, `q` quits from the dashboard, `ctrl+p` opens
Textual's command palette.

## Web UI

`./web.sh` starts the FastAPI server and opens it in Chrome. Same data, same
features, plus small inline diagrams on a few Learn topics that don't
translate to a terminal.

## How it works

1. Every problem defines a real function signature (e.g. `def two_sum(nums,
   target): ...`) with real test cases, LeetCode-style constraints, and
   examples. Add your own via the LeetCode auto-fetch (paste a
   `leetcode.com/problems/...` link) or manually.
2. Write your solution, hit "Run + Review". Code runs in a subprocess (5s
   timeout) against the test cases, then the code + results go to Claude for
   a structured review: correctness, time/space complexity, style feedback,
   and one concrete next step.
3. Stuck? Get a hint (a nudge, not the answer) or reveal the full solution
   (gated behind an explicit click so you don't spoil it by accident).
4. Every submission is saved to history so you can track how your solutions
   evolve over time. Solving a problem starts a spaced-repetition timer;
   it resurfaces on the dashboard when it's due for a retry.

## Security note

Code execution is a subprocess with a timeout, not a full sandbox (no
docker/seccomp). Fine for a local, single-user tool running code you wrote
yourself. Don't paste code you don't trust.

## Roadmap ideas

- Multi-language support (Go, Java, C++, Rust) once Python habits are solid
- Per-problem diagrams (auto-generated from test-case data) in the web UI
