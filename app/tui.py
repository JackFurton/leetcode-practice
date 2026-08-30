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
from typing import Callable

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

from app.claude_client import (
    get_design_review,
    get_hint,
    get_scenario_review,
    get_solution,
    review_submission,
)
from app.curriculum import CURRICULUM
from app.db import engine, init_db
from app.bash_catalog import seed_bash_catalog
from app.bash_runner import run_bash_submission
from app.bash_runner import is_unedited as bash_is_unedited
from app.design_catalog import seed_design_catalog
from app.go_runner import run_go_submission
from app.go_runner import is_unedited as go_is_unedited
from app.models import (
    BashProblem,
    BashTestCase,
    DesignProblem,
    DesignSubmission,
    Problem,
    ProblemStarter,
    ScenarioProblem,
    ScenarioSubmission,
    SqlProblem,
    Submission,
    TestCase,
    TopicProgress,
)
from app.runner import run_submission, is_unedited
from app.scenario_catalog import seed_scenario_catalog
from app.seed_catalog import seed_catalog
from app.sql_catalog import seed_sql_catalog
from app.sql_runner import run_sql_submission
from app.sql_runner import is_unedited as sql_is_unedited
from app.stats import compute_dashboard_stats

DIFFICULTY_ORDER = {"Easy": 0, "Medium": 1, "Hard": 2}
STATUS_ORDER = {"todo": 0, "attempted": 1, "solved": 2}
DESIGN_STATUS_ORDER = {"todo": 0, "attempted": 1, "reviewed": 2}

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
    margin: 0 1 1 0;
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
    height: 20;
    min-height: 10;
    margin-bottom: 1;
}
TextArea:focus {
    border: round $primary;
}
#pd-notes {
    height: 6;
    min-height: 6;
}
Select {
    margin-bottom: 1;
}
#pd-buttons {
    height: auto;
    margin-bottom: 1;
}
.nav-selected {
    border: heavy $primary;
}
Button.-danger.nav-selected {
    border: heavy $primary;
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
    modes, h j k l w b 0 $ g g G i a A I o O x dd yy p u ctrl+r D C, plus
    auto-indent on Enter while INSERT (matches the current line, +1 level
    after a line ending in ':').

    `on_exit_nav`, if set, is called when Escape is pressed while already in
    NORMAL mode (i.e. a second Escape) -- lets an owning screen implement
    "esc always gets you further out" instead of Escape being a dead end
    once you're in NORMAL but still focused on this widget."""

    INDENT = "    "

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.mode = "NORMAL"
        self.on_exit_nav: Callable[[], None] | None = None
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
            "i/a/A/I/o/O:insert  |  gg/G 0/$ w/b  |  dd yy p x D C u ^r"
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

    def _smart_newline(self) -> None:
        row, col = self.cursor_location
        current_line = self.get_line(row).plain[:col]
        leading = current_line[: len(current_line) - len(current_line.lstrip(" \t"))]
        indent = leading + self.INDENT if current_line.rstrip().endswith(":") else leading
        self.insert("\n" + indent)

    async def _on_key(self, event: Key) -> None:
        if self.mode == "INSERT":
            if event.key == "escape":
                event.stop()
                event.prevent_default()
                self._set_mode("NORMAL")
                return
            if event.key == "enter":
                event.stop()
                event.prevent_default()
                self._smart_newline()
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
            if self.on_exit_nav:
                self.on_exit_nav()
            return

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
        elif key == "A":
            self.action_cursor_line_end()
            self._set_mode("INSERT")
        elif key == "I":
            self.action_cursor_line_start()
            self._set_mode("INSERT")
        elif key == "o":
            self.action_cursor_line_end()
            self._smart_newline()
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
        elif key == "D":
            self.action_delete_to_end_of_line()
        elif key == "C":
            self.action_delete_to_end_of_line()
            self._set_mode("INSERT")
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
        Binding("s", "goto_design", "system design"),
        Binding("o", "goto_scenarios", "ops scenarios"),
        Binding("q", "app.quit", "quit"),
        Binding("j", "scroll_line(1)", "down", show=False),
        Binding("k", "scroll_line(-1)", "up", show=False),
        Binding("G", "scroll_bottom", "bottom", show=False),
        Binding("ctrl+d", "scroll_page(1)", "page down", show=False),
        Binding("ctrl+u", "scroll_page(-1)", "page up", show=False),
        Binding("c", "continue_problem", "continue"),
    ]

    def __init__(self):
        super().__init__()
        self._gchord = _Chord()
        self._continue_id: int | None = None

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
        self._continue_id = cp.id if cp else None
        lines.append("[b]Continue[/b]")
        if cp:
            lines.append(f"  -> {esc(cp.title)} [{esc(cp.difficulty)}] ({esc(cp.status)})  (press c)")
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
        lines.append(
            "[dim]p:problems  l:learn  s:system design  o:ops scenarios  c:continue  q:quit  "
            "j/k gg/G ^d/^u: scroll[/dim]"
        )

        self.query_one("#dash-body", Static).update("\n".join(lines))

    def action_goto_problems(self) -> None:
        self.app.push_screen(ProblemsScreen())

    def action_goto_learn(self) -> None:
        self.app.push_screen(LearnScreen())

    def action_goto_design(self) -> None:
        self.app.push_screen(DesignScreen())

    def action_goto_scenarios(self) -> None:
        self.app.push_screen(ScenarioScreen())

    def action_continue_problem(self) -> None:
        if self._continue_id is not None:
            self.app.push_screen(ProblemDetailScreen(self._continue_id))


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
    """Box-hopping vim navigation: in NORMAL (nothing "entered"), j/k/gg/G
    move a highlight between the status select / code editor / buttons /
    notes editor, l or enter "enters" the highlighted box (types into a
    VimTextArea, opens the Select, presses a Button), h leaves the screen.
    Once entered a VimTextArea, that box's own NORMAL/INSERT layer takes
    over (see VimTextArea); Escape from its NORMAL mode calls back into
    _exit_to_nav to pop back out to box-hopping, so Escape always gets you
    further out instead of ever being a dead end."""

    BINDINGS = [
        Binding("escape", "app.pop_screen", "back"),
    ]

    def __init__(self, problem_id: int):
        super().__init__()
        self.problem_id = problem_id
        self.nav_index = 0
        self.entered = False
        self._gchord = _Chord()
        self.current_language = "python"
        self.starters: dict[str, ProblemStarter] = {}  # non-python languages, by name
        self.sql_problem: SqlProblem | None = None
        self.bash_problem: BashProblem | None = None
        self.bash_test_cases: list[BashTestCase] = []

    def compose(self) -> ComposeResult:
        yield Header()
        with VerticalScroll():
            yield Static("", id="pd-info", classes="panel")
            yield Select(
                [("todo", "todo"), ("attempted", "attempted"), ("solved", "solved")],
                id="pd-status",
                allow_blank=False,
            )
            yield Select([("python", "python")], id="pd-language", allow_blank=False)
            yield Static(
                "[b]Code[/b]  (j/k to move between boxes, l/enter to enter one, "
                "esc always backs out)"
            )
            yield VimTextArea("", id="pd-code", language="python")
            with Horizontal(id="pd-buttons"):
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
        code_box = self.query_one("#pd-code", VimTextArea)
        notes_box = self.query_one("#pd-notes", VimTextArea)
        code_box.on_exit_nav = self._exit_to_nav
        notes_box.on_exit_nav = self._exit_to_nav
        self._focusables = [
            self.query_one("#pd-status", Select),
            self.query_one("#pd-language", Select),
            code_box,
            self.query_one("#pd-submit", Button),
            self.query_one("#pd-hint", Button),
            self.query_one("#pd-solution", Button),
            notes_box,
            self.query_one("#pd-save-notes", Button),
        ]
        self._highlight()

    def _highlight(self) -> None:
        for i, widget in enumerate(self._focusables):
            widget.set_class(i == self.nav_index, "nav-selected")

    def _nav(self, delta: int) -> None:
        self.nav_index = max(0, min(len(self._focusables) - 1, self.nav_index + delta))
        self._highlight()

    def _enter_current(self) -> None:
        widget = self._focusables[self.nav_index]
        widget.focus()
        if isinstance(widget, VimTextArea):
            self.entered = True
        elif isinstance(widget, Button):
            widget.press()
        elif isinstance(widget, Select):
            widget.action_show_overlay()

    def _exit_to_nav(self) -> None:
        self.entered = False
        self.set_focus(None)
        self._highlight()

    def on_key(self, event: Key) -> None:
        if self.entered:
            return  # focused VimTextArea owns input, see its own _on_key
        key = event.key
        if key == "j":
            self._nav(1)
            event.stop()
        elif key == "k":
            self._nav(-1)
            event.stop()
        elif key == "g":
            if self._gchord.tap():
                self.nav_index = 0
                self._highlight()
            event.stop()
        elif key == "G":
            self.nav_index = len(self._focusables) - 1
            self._highlight()
            event.stop()
        elif key in ("l", "enter"):
            self._enter_current()
            event.stop()
        elif key == "h":
            self.app.pop_screen()
            event.stop()

    def load_problem(self) -> None:
        with _session() as session:
            problem = session.get(Problem, self.problem_id)
            self.problem = problem
            test_cases = session.exec(
                select(TestCase).where(TestCase.problem_id == self.problem_id)
            ).all()
            self.starters = {
                st.language: st
                for st in session.exec(
                    select(ProblemStarter).where(ProblemStarter.problem_id == self.problem_id)
                ).all()
            }
            self.sql_problem = session.exec(
                select(SqlProblem).where(SqlProblem.problem_id == self.problem_id)
            ).first()
            self.bash_problem = session.exec(
                select(BashProblem).where(BashProblem.problem_id == self.problem_id)
            ).first()
            self.bash_test_cases = session.exec(
                select(BashTestCase).where(BashTestCase.problem_id == self.problem_id)
            ).all()

        languages = [("python", "python")] + [(lang, lang) for lang in sorted(self.starters)]
        if self.sql_problem:
            languages.append(("sql", "sql"))
        if self.bash_problem:
            languages.append(("bash", "bash"))
        # SQL/bash-only problems have no python function signature at all,
        # default straight to the language that actually applies.
        if not problem.function_name and self.sql_problem:
            self.current_language = "sql"
        elif not problem.function_name and self.bash_problem:
            self.current_language = "bash"
        else:
            self.current_language = "python"
        lang_select = self.query_one("#pd-language", Select)
        lang_select.set_options(languages)
        lang_select.value = self.current_language

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
        if self.sql_problem:
            lines.append("")
            lines.append("[dim]schema:[/dim]")
            for schema_line in self.sql_problem.setup_sql.strip().splitlines():
                lines.append(f"  {esc(schema_line.strip())}")
        if self.bash_test_cases:
            lines.append("")
            lines.append("[dim]examples (stdin -> stdout):[/dim]")
            for i, tc in enumerate(self.bash_test_cases, 1):
                lines.append(f"  {i}. in:  {esc(repr(tc.stdin))}")
                lines.append(f"     out: {esc(repr(tc.expected_stdout))}")
        self.query_one("#pd-info", Static).update("\n".join(lines))

        self.query_one("#pd-status", Select).value = problem.status
        self._load_code_for_language()
        self.query_one("#pd-notes", VimTextArea).text = problem.my_notes or ""

    def _load_code_for_language(self) -> None:
        code_box = self.query_one("#pd-code", VimTextArea)
        if self.current_language == "python":
            fn_name = self.problem.function_name or "solve"
            code_box.language = "python"
            code_box.text = self.problem.starter_code or f"def {fn_name}(*args):\n    pass"
        elif self.current_language == "sql":
            code_box.language = "sql"
            code_box.text = self.sql_problem.starter_code
        elif self.current_language == "bash":
            code_box.language = "bash"
            code_box.text = self.bash_problem.starter_code
        else:
            starter = self.starters[self.current_language]
            code_box.language = self.current_language if self.current_language in (
                "python", "go", "rust", "javascript", "typescript", "java",
            ) else None
            code_box.text = starter.starter_code

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "pd-status":
            with _session() as session:
                problem = session.get(Problem, self.problem_id)
                problem.status = event.value
                session.add(problem)
                session.commit()
        elif event.select.id == "pd-language":
            self.current_language = event.value
            self._load_code_for_language()
            self.query_one("#pd-result", Static).update("")

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
        language = self.current_language
        with _session() as session:
            problem = session.get(Problem, self.problem_id)
            test_cases = session.exec(
                select(TestCase).where(TestCase.problem_id == self.problem_id)
            ).all()
            cases = [
                (json.loads(tc.input_json), json.loads(tc.expected_json)) for tc in test_cases
            ]

            if language == "python":
                result = run_submission(code, cases, problem.function_name or "solve")
                edited = not is_unedited(code, problem.starter_code, problem.function_name)
            elif language == "go":
                starter = self.starters["go"]
                arg_types = json.loads(starter.arg_types)
                result = run_go_submission(
                    code, cases, starter.function_name, arg_types, starter.return_type
                )
                edited = not go_is_unedited(code, starter.starter_code)
            elif language == "sql":
                sql_problem = self.sql_problem
                result = run_sql_submission(
                    code,
                    sql_problem.setup_sql,
                    json.loads(sql_problem.expected_columns),
                    json.loads(sql_problem.expected_rows),
                )
                edited = not sql_is_unedited(code, sql_problem.starter_code)
            elif language == "bash":
                bash_cases = [(tc.stdin, tc.expected_stdout) for tc in self.bash_test_cases]
                result = run_bash_submission(code, bash_cases)
                edited = not bash_is_unedited(code, self.bash_problem.starter_code)
            else:
                result = {"ok": False, "results": [], "error": f"Unsupported language: {language}"}
                edited = True

            has_cases = len(cases) > 0 if language in ("python", "go") else len(result["results"]) > 0
            passed = result["ok"] and all(r.get("passed") for r in result["results"]) and has_cases

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
                language=language,
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
            elif problem.status == "todo" and edited:
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
                if r.get("detail"):
                    lines.append(f"      {esc(r['detail'])}")
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
        language = self.current_language
        with _session() as session:
            problem = session.get(Problem, self.problem_id)
            if language == "python":
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
            elif language == "sql":
                sql_problem = session.exec(
                    select(SqlProblem).where(SqlProblem.problem_id == self.problem_id)
                ).first()
                if not sql_problem.cached_solution:
                    sql_problem.cached_solution = get_solution(
                        f"{problem.title} (SQL)",
                        problem.notes,
                        problem.difficulty,
                        "query",
                        sql_problem.starter_code,
                    )
                    session.add(sql_problem)
                    session.commit()
                solution = sql_problem.cached_solution
            elif language == "bash":
                bash_problem = session.exec(
                    select(BashProblem).where(BashProblem.problem_id == self.problem_id)
                ).first()
                if not bash_problem.cached_solution:
                    bash_problem.cached_solution = get_solution(
                        f"{problem.title} (bash)",
                        problem.notes,
                        problem.difficulty,
                        "script",
                        bash_problem.starter_code,
                    )
                    session.add(bash_problem)
                    session.commit()
                solution = bash_problem.cached_solution
            else:
                starter = session.exec(
                    select(ProblemStarter).where(
                        ProblemStarter.problem_id == self.problem_id,
                        ProblemStarter.language == language,
                    )
                ).first()
                if not starter.cached_solution:
                    starter.cached_solution = get_solution(
                        f"{problem.title} (in {language})",
                        problem.notes,
                        problem.difficulty,
                        starter.function_name,
                        starter.starter_code,
                    )
                    session.add(starter)
                    session.commit()
                solution = starter.cached_solution
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


# ------------------------------------------------------------ system design


class DesignScreen(Screen):
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
    ]

    def __init__(self):
        super().__init__()
        self.sort_key = "title"
        self.sort_dir = "asc"
        self._gchord = _Chord()

    def compose(self) -> ComposeResult:
        yield Header()
        yield DataTable(id="design-table")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.cursor_type = "row"
        table.add_columns("Title", "Difficulty", "Topic", "Status")
        self.load_rows()
        table.focus()

    def on_key(self, event: Key) -> None:
        if event.key == "g" and self._gchord.tap():
            self.query_one(DataTable).move_cursor(row=0, column=0)
            event.stop()

    def load_rows(self) -> None:
        table = self.query_one(DataTable)
        table.clear()
        with _session() as session:
            problems = session.exec(select(DesignProblem)).all()

        keys = {
            "title": lambda p: p.title.lower(),
            "difficulty": lambda p: DIFFICULTY_ORDER.get(p.difficulty, 99),
            "status": lambda p: DESIGN_STATUS_ORDER.get(p.status, 99),
        }
        problems.sort(key=keys[self.sort_key], reverse=(self.sort_dir == "desc"))

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

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        self.app.push_screen(DesignDetailScreen(int(event.row_key.value)))


class DesignDetailScreen(Screen):
    """Same box-hopping model as ProblemDetailScreen, a smaller widget set:
    status, a free-text answer editor, a submit button, the review."""

    BINDINGS = [
        Binding("escape", "app.pop_screen", "back"),
    ]

    def __init__(self, design_id: int):
        super().__init__()
        self.design_id = design_id
        self.nav_index = 0
        self.entered = False
        self._gchord = _Chord()

    def compose(self) -> ComposeResult:
        yield Header()
        with VerticalScroll():
            yield Static("", id="dd-info", classes="panel")
            yield Select(
                [("todo", "todo"), ("attempted", "attempted"), ("reviewed", "reviewed")],
                id="dd-status",
                allow_blank=False,
            )
            yield Static(
                "[b]Your design[/b]  (j/k to move between boxes, l/enter to enter one, "
                "esc always backs out)"
            )
            yield VimTextArea("", id="dd-answer")
            yield Button("get review", id="dd-submit")
            yield Static("", id="dd-result", classes="panel")
        yield Footer()

    def on_mount(self) -> None:
        self.load_problem()
        answer_box = self.query_one("#dd-answer", VimTextArea)
        answer_box.on_exit_nav = self._exit_to_nav
        self._focusables = [
            self.query_one("#dd-status", Select),
            answer_box,
            self.query_one("#dd-submit", Button),
        ]
        self._highlight()

    def _highlight(self) -> None:
        for i, widget in enumerate(self._focusables):
            widget.set_class(i == self.nav_index, "nav-selected")

    def _nav(self, delta: int) -> None:
        self.nav_index = max(0, min(len(self._focusables) - 1, self.nav_index + delta))
        self._highlight()

    def _enter_current(self) -> None:
        widget = self._focusables[self.nav_index]
        widget.focus()
        if isinstance(widget, VimTextArea):
            self.entered = True
        elif isinstance(widget, Button):
            widget.press()
        elif isinstance(widget, Select):
            widget.action_show_overlay()

    def _exit_to_nav(self) -> None:
        self.entered = False
        self.set_focus(None)
        self._highlight()

    def on_key(self, event: Key) -> None:
        if self.entered:
            return
        key = event.key
        if key == "j":
            self._nav(1)
            event.stop()
        elif key == "k":
            self._nav(-1)
            event.stop()
        elif key == "g":
            if self._gchord.tap():
                self.nav_index = 0
                self._highlight()
            event.stop()
        elif key == "G":
            self.nav_index = len(self._focusables) - 1
            self._highlight()
            event.stop()
        elif key in ("l", "enter"):
            self._enter_current()
            event.stop()
        elif key == "h":
            self.app.pop_screen()
            event.stop()

    def load_problem(self) -> None:
        with _session() as session:
            problem = session.get(DesignProblem, self.design_id)
            self.problem = problem

        lines = [f"[b]{esc(problem.title)}[/b]  [{esc(problem.difficulty)}]"]
        lines.append("")
        lines.append(esc(problem.prompt))
        if problem.constraints:
            lines.append("")
            lines.append("[dim]constraints:[/dim]")
            for c in problem.constraints.split("\n"):
                lines.append(f"  - {esc(c)}")
        self.query_one("#dd-info", Static).update("\n".join(lines))

        self.query_one("#dd-status", Select).value = problem.status
        self.query_one("#dd-answer", VimTextArea).text = ""

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "dd-status":
            with _session() as session:
                problem = session.get(DesignProblem, self.design_id)
                problem.status = event.value
                session.add(problem)
                session.commit()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "dd-submit":
            self.query_one("#dd-result", Static).update("[dim]thinking...[/dim]")
            self.do_submit()

    def _show_submit_result(self, text: str, new_status: str) -> None:
        self.query_one("#dd-result", Static).update(text)
        self.query_one("#dd-status", Select).value = new_status

    @work(thread=True, exclusive=True)
    def do_submit(self) -> None:
        answer = self.query_one("#dd-answer", VimTextArea).text
        with _session() as session:
            problem = session.get(DesignProblem, self.design_id)
            review_text = get_design_review(
                problem.title, problem.prompt, problem.constraints, problem.difficulty, answer
            )
            session.add(
                DesignSubmission(
                    design_problem_id=self.design_id, answer_text=answer, review=review_text
                )
            )
            if problem.status == "todo" and answer.strip():
                problem.status = "attempted"
                session.add(problem)
            session.commit()
            new_status = problem.status

        self.app.call_from_thread(self._show_submit_result, esc(review_text), new_status)


# --------------------------------------------------------- ops/cloud scenarios


class ScenarioScreen(Screen):
    BINDINGS = [
        Binding("escape", "app.pop_screen", "back"),
        Binding("t", "sort('title')", "sort title"),
        Binding("a", "sort('area')", "sort area"),
        Binding("s", "sort('status')", "sort status"),
        Binding("j", "cursor_down", "down", show=False),
        Binding("k", "cursor_up", "up", show=False),
        Binding("l,enter", "open_row", "open", show=False),
        Binding("h", "app.pop_screen", "back", show=False),
        Binding("G", "cursor_bottom", "bottom", show=False),
    ]

    def __init__(self):
        super().__init__()
        self.sort_key = "area"
        self.sort_dir = "asc"
        self._gchord = _Chord()

    def compose(self) -> ComposeResult:
        yield Header()
        yield DataTable(id="scenario-table")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.cursor_type = "row"
        table.add_columns("Title", "Area", "Difficulty", "Status")
        self.load_rows()
        table.focus()

    def on_key(self, event: Key) -> None:
        if event.key == "g" and self._gchord.tap():
            self.query_one(DataTable).move_cursor(row=0, column=0)
            event.stop()

    def load_rows(self) -> None:
        table = self.query_one(DataTable)
        table.clear()
        with _session() as session:
            problems = session.exec(select(ScenarioProblem)).all()

        keys = {
            "title": lambda p: p.title.lower(),
            "area": lambda p: p.area,
            "status": lambda p: DESIGN_STATUS_ORDER.get(p.status, 99),
        }
        problems.sort(key=keys[self.sort_key], reverse=(self.sort_dir == "desc"))

        for p in problems:
            table.add_row(
                esc(p.title), esc(p.area), esc(p.difficulty), esc(p.status), key=str(p.id)
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

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        self.app.push_screen(ScenarioDetailScreen(int(event.row_key.value)))


class ScenarioDetailScreen(Screen):
    """Same box-hopping model as DesignDetailScreen. key_points isn't shown
    in the info panel (it's the grading rubric, not part of the prompt),
    only passed to get_scenario_review."""

    BINDINGS = [
        Binding("escape", "app.pop_screen", "back"),
    ]

    def __init__(self, scenario_id: int):
        super().__init__()
        self.scenario_id = scenario_id
        self.nav_index = 0
        self.entered = False
        self._gchord = _Chord()

    def compose(self) -> ComposeResult:
        yield Header()
        with VerticalScroll():
            yield Static("", id="sc-info", classes="panel")
            yield Select(
                [("todo", "todo"), ("attempted", "attempted"), ("reviewed", "reviewed")],
                id="sc-status",
                allow_blank=False,
            )
            yield Static(
                "[b]Your diagnosis / fix[/b]  (j/k to move between boxes, l/enter to enter one, "
                "esc always backs out)"
            )
            yield VimTextArea("", id="sc-answer")
            yield Button("get review", id="sc-submit")
            yield Static("", id="sc-result", classes="panel")
        yield Footer()

    def on_mount(self) -> None:
        self.load_problem()
        answer_box = self.query_one("#sc-answer", VimTextArea)
        answer_box.on_exit_nav = self._exit_to_nav
        self._focusables = [
            self.query_one("#sc-status", Select),
            answer_box,
            self.query_one("#sc-submit", Button),
        ]
        self._highlight()

    def _highlight(self) -> None:
        for i, widget in enumerate(self._focusables):
            widget.set_class(i == self.nav_index, "nav-selected")

    def _nav(self, delta: int) -> None:
        self.nav_index = max(0, min(len(self._focusables) - 1, self.nav_index + delta))
        self._highlight()

    def _enter_current(self) -> None:
        widget = self._focusables[self.nav_index]
        widget.focus()
        if isinstance(widget, VimTextArea):
            self.entered = True
        elif isinstance(widget, Button):
            widget.press()
        elif isinstance(widget, Select):
            widget.action_show_overlay()

    def _exit_to_nav(self) -> None:
        self.entered = False
        self.set_focus(None)
        self._highlight()

    def on_key(self, event: Key) -> None:
        if self.entered:
            return
        key = event.key
        if key == "j":
            self._nav(1)
            event.stop()
        elif key == "k":
            self._nav(-1)
            event.stop()
        elif key == "g":
            if self._gchord.tap():
                self.nav_index = 0
                self._highlight()
            event.stop()
        elif key == "G":
            self.nav_index = len(self._focusables) - 1
            self._highlight()
            event.stop()
        elif key in ("l", "enter"):
            self._enter_current()
            event.stop()
        elif key == "h":
            self.app.pop_screen()
            event.stop()

    def load_problem(self) -> None:
        with _session() as session:
            problem = session.get(ScenarioProblem, self.scenario_id)
            self.problem = problem

        lines = [
            f"[b]{esc(problem.title)}[/b]  [{esc(problem.area)}, {esc(problem.difficulty)}]"
        ]
        lines.append("")
        lines.append(esc(problem.situation))
        lines.append("")
        lines.append("[dim]ask:[/dim]")
        lines.append(esc(problem.ask))
        self.query_one("#sc-info", Static).update("\n".join(lines))

        self.query_one("#sc-status", Select).value = problem.status
        self.query_one("#sc-answer", VimTextArea).text = ""

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "sc-status":
            with _session() as session:
                problem = session.get(ScenarioProblem, self.scenario_id)
                problem.status = event.value
                session.add(problem)
                session.commit()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "sc-submit":
            self.query_one("#sc-result", Static).update("[dim]thinking...[/dim]")
            self.do_submit()

    def _show_submit_result(self, text: str, new_status: str) -> None:
        self.query_one("#sc-result", Static).update(text)
        self.query_one("#sc-status", Select).value = new_status

    @work(thread=True, exclusive=True)
    def do_submit(self) -> None:
        answer = self.query_one("#sc-answer", VimTextArea).text
        with _session() as session:
            problem = session.get(ScenarioProblem, self.scenario_id)
            key_points = json.loads(problem.key_points)
            review_text = get_scenario_review(
                problem.title,
                problem.area,
                problem.situation,
                problem.ask,
                key_points,
                problem.difficulty,
                answer,
            )
            session.add(
                ScenarioSubmission(
                    scenario_id=self.scenario_id, answer_text=answer, review=review_text
                )
            )
            if problem.status == "todo" and answer.strip():
                problem.status = "attempted"
                session.add(problem)
            session.commit()
            new_status = problem.status

        self.app.call_from_thread(self._show_submit_result, esc(review_text), new_status)


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
            seed_sql_catalog(session)
            seed_bash_catalog(session)
            seed_design_catalog(session)
            seed_scenario_catalog(session)
        self.push_screen(DashboardScreen())


def main() -> None:
    LCTrainerApp().run()


if __name__ == "__main__":
    main()
