# LC Trainer

Practice LeetCode-style problems (paired with algo.monster), submit code, and
get an automated review from Claude on correctness, complexity, and style.
Goal: comfortably pass Mediums within a year. A terminal UI, mouse-free,
vim-driven.

## Setup

```bash
cd leetcode-practice
./start.sh
```

First run creates a venv, installs deps, and copies `.env.example` to `.env`.
Edit `.env` and either set `ANTHROPIC_API_KEY` directly or point
`ANTHROPIC_API_KEY_FILE` at a file containing your key. This is required for
hints, code review, and any solution not already in the pre-baked set below
(see [Cost](#cost--api-key)); everything else (browsing, the dashboard,
Learn, running your own test cases) works with no key at all.

Seeds a 27-problem starter catalog on first boot (instant, no network call,
the data's baked in).

## Cost / API key

Every install uses **its own** key from its own `.env`, nobody else's. `.env`
and the local SQLite DB (`data/lc.db`) are gitignored, neither is ever
committed, so cloning or forking this repo never carries anyone's key or
submission history with it.

Reveal Solution is pre-baked (verified against the real test cases, not
Claude-generated) for the 25 catalog problems that have one, zero API calls,
works with **no key configured at all**. Hint and Code Review always call
Claude live, they're inherently dynamic (a review has to see your actual
code). Reveal Solution on a problem without a pre-baked one (Clone Graph,
Trie, or anything you add yourself) also calls Claude live and caches the
result after the first pull.

## Using it

`./start.sh` drops you straight into a Textual-based TUI, no browser, no
mouse needed:

- **Dashboard**: overall progress, per-difficulty breakdown, streak, per-pattern
  progress bars, `c` to jump into "continue where you left off", due-for-review.
- **Problems** (`p`): sortable list (`t`/`d`/`s` for title/difficulty/status),
  `/` to filter, enter a row to open it.
- **Problem detail**: description, constraints, examples, a modal vim code
  editor with syntax highlighting, run + review, get a hint, reveal a full
  solution (cached after first pull), personal notes.
- **Learn** (`l`): pattern checklist by category, an ASCII diagram on the
  more visual topics, space to toggle done, select a topic to see its
  explanation + template.

Navigation is vim-style everywhere: `h j k l`, `gg`/`G` (top/bottom),
`ctrl+d`/`ctrl+u` (page down/up), `escape` backs out (see below, always gets
you further out, never a dead end), `q` quits from the dashboard, `ctrl+p`
opens Textual's command palette.

### The problem screen is one box-hopping vim buffer

On a problem's detail screen, `j`/`k`/`gg`/`G` move a highlight between the
status field, the code editor, each button, and the notes editor, exactly
like moving between vim splits. `l` or `enter` "enters" whatever's
highlighted: opens the status dropdown, presses a button, or drops you into
the code/notes editor. `h` leaves the whole screen.

The code and notes editors are modal, same idea as vim: they open in
**NORMAL** mode (motions only, nothing types), `i`/`a`/`A`/`I`/`o`/`O` drop
into **INSERT** mode to actually write, `esc` backs out one level at a time:
INSERT → that editor's own NORMAL → back to box-hopping. In NORMAL mode:
`h j k l` move, `w`/`b` word-jump, `0`/`$` line start/end, `gg`/`G` document
start/end, `x` delete char, `D`/`C` delete/change to end of line, `dd`
delete line, `yy`/`p` yank/paste line, `u` undo, `ctrl+r` redo. Enter in
INSERT mode auto-indents: matches the current line, one level deeper after
a line ending in `:`.

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
   it resurfaces on the dashboard when it's due for a retry. A submission
   only counts as an "attempt" if you actually changed the starter code,
   an accidental click on unedited code doesn't touch its status.
5. Notes are per-problem (`Problem.my_notes` in the DB), your own scratch
   space, separate from the system-authored description.

## Web UI

There's also a FastAPI + HTMX web app (`app/main.py`) with the same data and
features, plus small inline SVG diagrams on a few Learn topics that don't
translate to a terminal. No launch script for it anymore (the TUI is the
primary interface now), run it manually if you want it:

```bash
source .venv/bin/activate
uvicorn app.main:app --reload
```

## Security note

Code execution is a subprocess with a timeout, not a full sandbox (no
docker/seccomp). Fine for a local, single-user tool running code you wrote
yourself. Don't paste code you don't trust.

## Contributing

MIT licensed (see `LICENSE`), issues/PRs welcome. Nothing here needs a
backend or account beyond your own Anthropic key, `git clone` + `./start.sh`
is the whole setup.

## Roadmap ideas

- Multi-language support (Go, Java, C++, Rust, TypeScript, JavaScript) once
  Python habits are solid, each needs its own runner harness and structure
  wrapper convention. Confirmed direction, not started yet.
- Per-problem diagrams (auto-generated from test-case data) in the web UI
