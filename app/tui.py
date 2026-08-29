"""Terminal UI for LC Trainer. Talks directly to the same DB and business
logic as the web app (app.runner, app.claude_client, app.stats, ...) -- no
HTTP layer, no need for the web server to be running. Run via ./start.sh or
`python -m app.tui`.

Fully keyboard-driven, vim-style: hjkl/gg/G/ctrl-d/ctrl-u to move around
lists and trees, and the code/notes editors are modal (NORMAL/INSERT, esc
to leave INSERT) with a real subset of vim motions and edits.
"""
import json
import time
from datetime import datetime

from rich.style import Style
from sqlmodel import Session, select
from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, VerticalScroll
from textual.events import Key
from textual.markup import escape as esc
from textual.screen import Screen
from textual.theme import Theme
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Header,
    Input,
    Select,
    Static,
    TextArea,
    Tree,
)
from textual.widgets.text_area import TextAreaTheme

from app.claude_client import get_hint, get_solution, review_submission
from app.curriculum import CURRICULUM
from app.db import engine, init_db
from app.models import Problem, Submission, TestCase, TopicProgress
from app.runner import run_submission
from app.seed_catalog import seed_catalog
from app.stats import compute_dashboard_stats

DIFFICULTY_ORDER = {"Easy": 0, "Medium": 1, "Hard": 2}
STATUS_ORDER = {"todo": 0, "attempted": 1, "solved": 2}

# -------------------------------------------------------------------- theme
# Select/Button/TextArea etc pull their colors from the App's registered
# Theme (design tokens like $surface/$foreground), not from ad-hoc CSS, so
# that's the only reliable way to make every widget follow the palette.

HACKER_THEME = Theme(
    name="hacker",
    primary="#00ff66",
    secondary="#00cc52",
    warning="#ffd23f",
    error="#ff4d5e",
    success="#00ff66",
    accent="#00ff66",
    foreground="#c9ffd6",
    background="#000000",
    surface="#030602",
    panel="#0a120a",
    boost="#0d160d",
    dark=True,
)

HACKER_TA_THEME = TextAreaTheme(
    name="hacker",
    base_style=Style(color="#c9ffd6", bgcolor="#020402"),
    gutter_style=Style(color="#5c8a67", bgcolor="#020402"),
    cursor_style=Style(color="#020402", bgcolor="#00ff66"),
    cursor_line_style=Style(bgcolor="#0a120a"),
    selection_style=Style(bgcolor="#164023"),
    syntax_styles={
        "keyword": Style(color="#00ff66", bold=True),
        "keyword.function": Style(color="#00ff66", bold=True),
        "keyword.return": Style(color="#00ff66", bold=True),
        "keyword.operator": Style(color="#00cc52"),
        "string": Style(color="#ffd23f"),
        "string.documentation": Style(color="#ffd23f"),
        "comment": Style(color="#5c8a67", italic=True),
        "number": Style(color="#c9ffd6"),
        "boolean": Style(color="#c9ffd6", bold=True),
        "function": Style(color="#39ff87"),
        "function.call": Style(color="#39ff87"),
        "method": Style(color="#39ff87"),
        "method.call": Style(color="#39ff87"),
        "class": Style(color="#00cc52", bold=True),
        "type": Style(color="#00cc52"),
        "type.builtin": Style(color="#00cc52"),
        "constant.builtin": Style(color="#ffd23f"),
        "operator": Style(color="#c9ffd6"),
        "punctuation.bracket": Style(color="#5c8a67"),
        "punctuation.delimiter": Style(color="#5c8a67"),
        "variable.builtin": Style(color="#c9ffd6", italic=True),
    },
)

APP_CSS = """
Header, Footer {
    background: $surface;
    color: $primary;
}
.panel {
    border: round $secondary;
    padding: 1 2;
    margin: 0 0 1 0;
}
Button {
    height: 3;
    min-width: 14;
    border: round $secondary;
}
Button.-danger {
    color: $error;
    border: round $error;
}
DataTable {
    background: $background;
}
TextArea {
    border: round $secondary;
    height: 1fr;
    min-height: 10;
}
TextArea:focus {
    border: round $primary;
}
#pd-notes {
    height: 6;
    min-height: 6;
}
Input#filter-input {
    border: round $primary;
    margin-bottom: 1;
}
"""


def _session() -> Session:
    return Session(engine)


class _Chord:
    """Tracks a double-tap key chord, e.g. vim's 'gg'."""

    def __init__(self, timeout: float = 0.6):
        self.timeout = timeout
        self._last = 0.0

    def tap(self) -> bool:
        now = time.monotonic()
        if now - self._last < self.timeout:
            self._last = 0.0
            return True
        self._last = now
        return False


# --------------------------------------------------------------- vim editor


class VimTextArea(TextArea):
    """TextArea with a real (if partial) vim modal layer: NORMAL/INSERT
    modes, h j k l w b 0 $ g g G i a o O x dd yy p u ctrl+r."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.mode = "NORMAL"
        self._yank_buffer = ""
        self._gchord = _Chord()
        self._dchord = _Chord()
        self._ychord = _Chord()

    def on_mount(self) -> None:
        self.register_theme(HACKER_TA_THEME)
        self.theme = "hacker"
        self._sync_border()

    def _set_mode(self, mode: str) -> None:
        self.mode = mode
        self._sync_border()

    def _sync_border(self) -> None:
        self.border_title = f"-- {self.mode} --"
        self.border_subtitle = (
            "i:insert a:append o/O:open  |  gg/G 0/$ w/b  |  dd yy p x u ^r"
            if self.mode == "NORMAL"
            else "esc: back to NORMAL"
        )

    def _move_to_end(self) -> None:
        lines = self.text.split("\n")
        last_row = len(lines) - 1
        self.move_cursor((last_row, len(lines[-1])))

    def _yank_line(self) -> None:
        row, _ = self.cursor_location
        self._yank_buffer = self.get_line(row).plain

    def _paste_line(self) -> None:
        if not self._yank_buffer:
            return
        self.action_cursor_line_end()
        self.insert("\n" + self._yank_buffer)

    async def _on_key(self, event: Key) -> None:
        if self.mode == "INSERT":
            if event.key == "escape":
                event.stop()
                event.prevent_default()
                self._set_mode("NORMAL")
                return
            await super()._on_key(event)
            return

        # NORMAL mode: pure navigation keys still work via default handling
        if event.key in ("up", "down", "left", "right", "home", "end", "pageup", "pagedown"):
            await super()._on_key(event)
            return

        event.stop()
        event.prevent_default()
        key = event.key

        if key == "escape":
            return  # already normal

        if key == "g":
            if self._gchord.tap():
                self.move_cursor((0, 0))
            return
        if key == "d":
            if self._dchord.tap():
                self.action_delete_line()
            return
        if key == "y":
            if self._ychord.tap():
                self._yank_line()
            return

        if key == "i":
            self._set_mode("INSERT")
        elif key == "a":
            self.action_cursor_right()
            self._set_mode("INSERT")
        elif key == "o":
            self.action_cursor_line_end()
            self.insert("\n")
            self._set_mode("INSERT")
        elif key == "O":
            self.action_cursor_line_start()
            self.insert("\n")
            self.action_cursor_up()
            self._set_mode("INSERT")
        elif key == "h":
            self.action_cursor_left()
        elif key == "l":
            self.action_cursor_right()
        elif key == "j":
            self.action_cursor_down()
        elif key == "k":
            self.action_cursor_up()
        elif key == "0":
            self.action_cursor_line_start()
        elif key == "dollar_sign":
            self.action_cursor_line_end()
        elif key == "w":
            self.action_cursor_word_right()
        elif key == "b":
            self.action_cursor_word_left()
        elif key == "x":
            self.action_delete_right()
        elif key == "u":
            self.action_undo()
        elif key == "ctrl+r":
            self.action_redo()
        elif key == "G":
            self._move_to_end()
        elif key == "p":
            self._paste_line()
        # anything else: swallowed, no-op (standard vim behavior for unmapped keys)


# ---------------------------------------------------------------- dashboard


class DashboardScreen(Screen):
    BINDINGS = [
        Binding("p", "goto_problems", "problems"),
        Binding("l", "goto_learn", "learn"),
        Binding("q", "app.quit", "quit"),
        Binding("j", "scroll_line(1)", "down", show=False),
        Binding("k", "scroll_line(-1)", "up", show=False),
        Binding("G", "scroll_bottom", "bottom", show=False),
        Binding("ctrl+d", "scroll_page(1)", "page down", show=False),
        Binding("ctrl+u", "scroll_page(-1)", "page up", show=False),
    ]

    def __init__(self):
        super().__init__()
        self._gchord = _Chord()

    def compose(self) -> ComposeResult:
        yield Header()
        with VerticalScroll(id="dash-scroll"):
            yield Static("", id="dash-body")
        yield Footer()

    def on_mount(self) -> None:
        self.refresh_dashboard()

    def on_key(self, event: Key) -> None:
        if event.key == "g" and self._gchord.tap():
            self.query_one("#dash-scroll", VerticalScroll).scroll_home(animate=False)
            event.stop()

    def action_scroll_line(self, direction: int) -> None:
        self.query_one("#dash-scroll", VerticalScroll).scroll_relative(y=direction, animate=False)

    def action_scroll_bottom(self) -> None:
        self.query_one("#dash-scroll", VerticalScroll).scroll_end(animate=False)

    def action_scroll_page(self, direction: int) -> None:
        scroller = self.query_one("#dash-scroll", VerticalScroll)
        if direction > 0:
            scroller.scroll_page_down()
        else:
            scroller.scroll_page_up()

    def refresh_dashboard(self) -> None:
        with _session() as session:
            stats = compute_dashboard_stats(session)

        lines = []
        lines.append(f"[b]{stats['solved_count']}/{stats['total']} solved[/b]  ({stats['pct']}%)")
        bar_width = 40
        filled = int(bar_width * stats["pct"] / 100)
        lines.append("[$primary]" + "#" * filled + "[/$primary]" + "-" * (bar_width - filled))
        diff_line = "  ".join(f"{d['label']} {d['solved']}/{d['total']}" for d in stats["diff_stats"])
        lines.append(diff_line)
        streak = stats["streak"]
        lines.append(f"[dim]streak: {streak} day{'s' if streak != 1 else ''}[/dim]")
        lines.append("")

        cp = stats["continue_problem"]
        lines.append("[b]Continue[/b]")
        if cp:
            lines.append(f"  -> {esc(cp.title)} [{esc(cp.difficulty)}] ({esc(cp.status)})")
        else:
            lines.append("  [dim]nothing in progress[/dim]")
        lines.append("")

        if stats["due_for_review"]:
            lines.append("[b]Due for Review[/b]")
            for p in stats["due_for_review"]:
                lines.append(f"  - {esc(p.title)}")
            lines.append("")

        lines.append("[b]By Pattern[/b]")
        for c in stats["category_progress"]:
            pct = round(100 * c["solved"] / c["total"]) if c["total"] else 0
            filled = int(20 * pct / 100)
            bar = "#" * filled + "-" * (20 - filled)
            lines.append(f"  {c['name']:<22} [{bar}] {c['solved']}/{c['total']}")

        lines.append("")
        lines.append("[dim]p:problems  l:learn  q:quit  j/k gg/G ^d/^u: scroll[/dim]")

        self.query_one("#dash-body", Static).update("\n".join(lines))

    def action_goto_problems(self) -> None:
        self.app.push_screen(ProblemsScreen())

    def action_goto_learn(self) -> None:
        self.app.push_screen(LearnScreen())


# ----------------------------------------------------------------- problems


class ProblemsScreen(Screen):
    BINDINGS = [
        Binding("escape", "app.pop_screen", "back"),
        Binding("t", "sort('title')", "sort title"),
        Binding("d", "sort('difficulty')", "sort difficulty"),
        Binding("s", "sort('status')", "sort status"),
        Binding("j", "cursor_down", "down", show=False),
        Binding("k", "cursor_up", "up", show=False),
        Binding("l,enter", "open_row", "open", show=False),
        Binding("h", "app.pop_screen", "back", show=False),
        Binding("G", "cursor_bottom", "bottom", show=False),
        Binding("slash", "start_filter", "filter"),
    ]

    def __init__(self):
        super().__init__()
        self.sort_key = "created"
        self.sort_dir = "desc"
        self.filter_text = ""
        self._gchord = _Chord()

    def compose(self) -> ComposeResult:
        yield Header()
        yield Input(placeholder="filter...", id="filter-input")
        yield DataTable(id="problems-table")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#filter-input", Input).display = False
        table = self.query_one(DataTable)
        table.cursor_type = "row"
        table.add_columns("Title", "Difficulty", "Topic", "Status")
        self.load_rows()
        table.focus()

    def on_key(self, event: Key) -> None:
        filter_input = self.query_one("#filter-input", Input)
        if event.key == "escape" and filter_input.has_focus:
            event.stop()
            filter_input.display = False
            filter_input.value = ""
            self.filter_text = ""
            self.load_rows()
            self.query_one(DataTable).focus()
            return
        if event.key == "g" and not filter_input.has_focus and self._gchord.tap():
            self.query_one(DataTable).move_cursor(row=0, column=0)
            event.stop()

    def load_rows(self) -> None:
        table = self.query_one(DataTable)
        table.clear()
        with _session() as session:
            problems = session.exec(select(Problem)).all()

        keys = {
            "title": lambda p: p.title.lower(),
            "difficulty": lambda p: DIFFICULTY_ORDER.get(p.difficulty, 99),
            "status": lambda p: STATUS_ORDER.get(p.status, 99),
            "created": lambda p: p.created_at,
        }
        problems.sort(key=keys[self.sort_key], reverse=(self.sort_dir == "desc"))

        if self.filter_text:
            needle = self.filter_text.lower()
            problems = [
                p
                for p in problems
                if needle in p.title.lower()
                or needle in (p.topic or "").lower()
                or needle in p.difficulty.lower()
                or needle in p.status.lower()
            ]
        self._rows = problems

        for p in problems:
            table.add_row(
                esc(p.title), esc(p.difficulty), esc(p.topic or "-"), esc(p.status), key=str(p.id)
            )

    def action_sort(self, key: str) -> None:
        if self.sort_key == key:
            self.sort_dir = "asc" if self.sort_dir == "desc" else "desc"
        else:
            self.sort_key, self.sort_dir = key, "asc"
        self.load_rows()

    def action_cursor_down(self) -> None:
        self.query_one(DataTable).action_cursor_down()

    def action_cursor_up(self) -> None:
        self.query_one(DataTable).action_cursor_up()

    def action_cursor_bottom(self) -> None:
        table = self.query_one(DataTable)
        if table.row_count:
            table.move_cursor(row=table.row_count - 1, column=0)

    def action_open_row(self) -> None:
        table = self.query_one(DataTable)
        if table.row_count == 0:
            return
        table.action_select_cursor()

    def action_start_filter(self) -> None:
        filter_input = self.query_one("#filter-input", Input)
        filter_input.display = True
        filter_input.focus()

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id != "filter-input":
            return
        self.filter_text = event.value
        self.load_rows()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id != "filter-input":
            return
        self.query_one(DataTable).focus()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        self.app.push_screen(ProblemDetailScreen(int(event.row_key.value)))


# ------------------------------------------------------------- problem detail


class ProblemDetailScreen(Screen):
    BINDINGS = [
        Binding("escape", "app.pop_screen", "back"),
    ]

    def __init__(self, problem_id: int):
        super().__init__()
        self.problem_id = problem_id

    def compose(self) -> ComposeResult:
        yield Header()
        with VerticalScroll():
            yield Static("", id="pd-info", classes="panel")
            yield Select(
                [("todo", "todo"), ("attempted", "attempted"), ("solved", "solved")],
                id="pd-status",
                allow_blank=False,
            )
            yield Static("[b]Code[/b]  (vim-modal: starts in NORMAL, i to insert)")
            yield VimTextArea("", id="pd-code", language="python")
            with Horizontal():
                yield Button("run + review", id="pd-submit")
                yield Button("get hint", id="pd-hint")
                yield Button("reveal solution", id="pd-solution", classes="-danger")
            yield Static("", id="pd-result", classes="panel")
            yield Static("[b]My Notes[/b]")
            yield VimTextArea("", id="pd-notes")
            yield Button("save notes", id="pd-save-notes")
        yield Footer()

    def on_mount(self) -> None:
        self.load_problem()

    def load_problem(self) -> None:
        with _session() as session:
            problem = session.get(Problem, self.problem_id)
            self.problem = problem
            test_cases = session.exec(
                select(TestCase).where(TestCase.problem_id == self.problem_id)
            ).all()

        lines = [f"[b]{esc(problem.title)}[/b]  [{esc(problem.difficulty)}]"]
        if problem.notes:
            lines.append(esc(problem.notes))
        if problem.constraints:
            lines.append("")
            lines.append("[dim]constraints:[/dim]")
            for c in problem.constraints.split("\n"):
                lines.append(f"  - {esc(c)}")
        fn_name = problem.function_name or "solve"
        if test_cases:
            lines.append("")
            lines.append("[dim]examples:[/dim]")
            for i, tc in enumerate(test_cases, 1):
                args = ", ".join(json.dumps(a) for a in json.loads(tc.input_json))
                lines.append(f"  {i}. {esc(fn_name)}({esc(args)}) -> {esc(tc.expected_json)}")
        self.query_one("#pd-info", Static).update("\n".join(lines))

        self.query_one("#pd-status", Select).value = problem.status

        code_box = self.query_one("#pd-code", VimTextArea)
        code_box.text = problem.starter_code or f"def {fn_name}(*args):\n    pass"

        self.query_one("#pd-notes", VimTextArea).text = problem.my_notes or ""

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id != "pd-status":
            return
        with _session() as session:
            problem = session.get(Problem, self.problem_id)
            problem.status = event.value
            session.add(problem)
            session.commit()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "pd-submit":
            self.query_one("#pd-result", Static).update("[dim]running...[/dim]")
            self.do_submit()
        elif event.button.id == "pd-hint":
            self.query_one("#pd-result", Static).update("[dim]thinking...[/dim]")
            self.do_hint()
        elif event.button.id == "pd-solution":
            self.query_one("#pd-result", Static).update("[dim]thinking...[/dim]")
            self.do_solution()
        elif event.button.id == "pd-save-notes":
            self.save_notes()

    def save_notes(self) -> None:
        notes_text = self.query_one("#pd-notes", VimTextArea).text
        with _session() as session:
            problem = session.get(Problem, self.problem_id)
            problem.my_notes = notes_text or None
            session.add(problem)
            session.commit()
        self.query_one("#pd-result", Static).update("[dim]notes saved[/dim]")

    def _show_result(self, text: str) -> None:
        self.query_one("#pd-result", Static).update(text)

    def _show_submit_result(self, text: str, new_status: str) -> None:
        self.query_one("#pd-result", Static).update(text)
        self.query_one("#pd-status", Select).value = new_status

    @work(thread=True, exclusive=True)
    def do_submit(self) -> None:
        code = self.query_one("#pd-code", VimTextArea).text
        with _session() as session:
            problem = session.get(Problem, self.problem_id)
            test_cases = session.exec(
                select(TestCase).where(TestCase.problem_id == self.problem_id)
            ).all()
            cases = [
                (json.loads(tc.input_json), json.loads(tc.expected_json)) for tc in test_cases
            ]
            result = run_submission(code, cases, problem.function_name or "solve")
            passed = result["ok"] and all(r.get("passed") for r in result["results"]) and len(cases) > 0

            review_text = review_submission(
                problem_title=problem.title,
                problem_notes=problem.notes,
                difficulty=problem.difficulty,
                code=code,
                run_result=result,
            )

            submission = Submission(
                problem_id=self.problem_id,
                code=code,
                passed=passed,
                results_json=json.dumps(result),
                review=review_text,
            )
            session.add(submission)

            if passed:
                now = datetime.utcnow()
                if problem.status == "solved":
                    problem.review_interval_days = min(problem.review_interval_days * 2, 30)
                else:
                    problem.status = "solved"
                    problem.review_interval_days = 1
                problem.last_reviewed_at = now
                session.add(problem)
            elif problem.status == "todo":
                problem.status = "attempted"
                session.add(problem)

            session.commit()
            new_status = problem.status

        status = "[$primary]PASSED[/$primary]" if passed else "[$error]FAILED[/$error]"
        lines = [status]
        if result["error"]:
            lines.append(f"error: {esc(result['error'])}")
        else:
            for i, r in enumerate(result["results"], 1):
                mark = "ok" if r.get("passed") else "x"
                lines.append(
                    f"  ({mark}) case {i}: expected={esc(json.dumps(r['expected']))} "
                    f"actual={esc(json.dumps(r.get('actual')))}"
                )
        lines.append("")
        lines.append(esc(review_text))
        self.app.call_from_thread(self._show_submit_result, "\n".join(lines), new_status)

    @work(thread=True, exclusive=True)
    def do_hint(self) -> None:
        with _session() as session:
            problem = session.get(Problem, self.problem_id)
            hint_text = get_hint(problem.title, problem.notes, problem.difficulty)
        self.app.call_from_thread(self._show_result, f"[b]hint[/b]\n{esc(hint_text)}")

    @work(thread=True, exclusive=True)
    def do_solution(self) -> None:
        with _session() as session:
            problem = session.get(Problem, self.problem_id)
            if not problem.cached_solution:
                problem.cached_solution = get_solution(
                    problem.title,
                    problem.notes,
                    problem.difficulty,
                    problem.function_name or "solve",
                    problem.starter_code,
                )
                session.add(problem)
                session.commit()
            solution = problem.cached_solution
        self.app.call_from_thread(self._show_result, f"[b]solution[/b]\n{esc(solution)}")


# --------------------------------------------------------------------- learn


class LearnScreen(Screen):
    BINDINGS = [
        Binding("escape", "app.pop_screen", "back"),
        Binding("space", "toggle_selected", "toggle done"),
        Binding("j", "cursor_down", "down", show=False),
        Binding("k", "cursor_up", "up", show=False),
        Binding("l,enter", "select_cursor", "select/expand", show=False),
        Binding("h", "cursor_parent", "collapse", show=False),
        Binding("G", "cursor_bottom", "bottom", show=False),
    ]

    def __init__(self):
        super().__init__()
        self._gchord = _Chord()

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            yield Tree("Curriculum", id="learn-tree")
            with VerticalScroll(id="learn-detail-panel"):
                yield Static("select a topic", id="learn-detail")
        yield Footer()

    def on_mount(self) -> None:
        with _session() as session:
            existing = {tp.topic for tp in session.exec(select(TopicProgress)).all()}
            for category in CURRICULUM:
                for topic in category["topics"]:
                    if topic["name"] not in existing:
                        session.add(TopicProgress(topic=topic["name"]))
            session.commit()
            done_map = {p.topic: p.done for p in session.exec(select(TopicProgress)).all()}

        tree = self.query_one(Tree)
        tree.root.expand()
        for category in CURRICULUM:
            cat_node = tree.root.add(esc(category["category"]), expand=False)
            for topic in category["topics"]:
                mark = "x" if done_map.get(topic["name"]) else " "
                cat_node.add_leaf(f"({mark}) {esc(topic['name'])}", data=topic)
        tree.focus()

    def on_key(self, event: Key) -> None:
        if event.key == "g" and self._gchord.tap():
            self.query_one(Tree).move_cursor_to_line(0)
            event.stop()

    def action_cursor_down(self) -> None:
        self.query_one(Tree).action_cursor_down()

    def action_cursor_up(self) -> None:
        self.query_one(Tree).action_cursor_up()

    def action_cursor_parent(self) -> None:
        self.query_one(Tree).action_cursor_parent()

    def action_cursor_bottom(self) -> None:
        tree = self.query_one(Tree)
        tree.move_cursor_to_line(tree.last_line)

    def action_select_cursor(self) -> None:
        self.query_one(Tree).action_select_cursor()

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        data = event.node.data
        if not data:
            return
        lines = [
            f"[b]{esc(data['name'])}[/b]",
            "",
            esc(data["explanation"]),
        ]
        if data.get("diagram_ascii"):
            lines.append("")
            lines.append(esc(data["diagram_ascii"]))
        lines.append("")
        lines.append("[dim]template:[/dim]")
        lines.append(esc(data["template"]))
        self.query_one("#learn-detail", Static).update("\n".join(lines))

    def action_toggle_selected(self) -> None:
        tree = self.query_one(Tree)
        node = tree.cursor_node
        if not node or not node.data:
            return
        topic_name = node.data["name"]
        with _session() as session:
            tp = session.exec(select(TopicProgress).where(TopicProgress.topic == topic_name)).first()
            tp.done = not tp.done
            session.add(tp)
            session.commit()
            done = tp.done
        mark = "x" if done else " "
        node.set_label(f"({mark}) {esc(topic_name)}")


# ---------------------------------------------------------------------- app


class LCTrainerApp(App):
    CSS = APP_CSS
    TITLE = "LC Trainer"

    def __init__(self) -> None:
        super().__init__(ansi_color=False)

    def on_mount(self) -> None:
        self.register_theme(HACKER_THEME)
        self.theme = "hacker"
        init_db()
        with _session() as session:
            seed_catalog(session)
        self.push_screen(DashboardScreen())


def main() -> None:
    LCTrainerApp().run()


if __name__ == "__main__":
    main()
