"""Terminal UI for LC Trainer. Talks directly to the same DB and business
logic as the web app (app.runner, app.claude_client, app.stats, ...) -- no
HTTP layer, no need for the web server to be running. Run via ./start.sh or
`python -m app.tui`.
"""
import json
from datetime import datetime

from sqlmodel import Session, select
from textual import work
from textual.markup import escape as esc
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, VerticalScroll
from textual.screen import Screen
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Header,
    Select,
    Static,
    TextArea,
    Tree,
)

from app.claude_client import get_hint, get_solution, review_submission
from app.curriculum import CURRICULUM
from app.db import engine, init_db
from app.models import Problem, Submission, TestCase, TopicProgress
from app.runner import run_submission
from app.seed_catalog import seed_catalog
from app.stats import compute_dashboard_stats

DIFFICULTY_ORDER = {"Easy": 0, "Medium": 1, "Hard": 2}
STATUS_ORDER = {"todo": 0, "attempted": 1, "solved": 2}

APP_CSS = """
Screen {
    background: #000000;
    color: #c9ffd6;
}
Header, Footer {
    background: #030602;
    color: #00ff66;
}
.title {
    color: #00ff66;
    text-style: bold;
}
.muted {
    color: #5c8a67;
}
.panel {
    border: round #164023;
    padding: 1 2;
    margin: 0 0 1 0;
}
Button {
    background: #030602;
    color: #00ff66;
    border: round #00cc52;
}
Button:hover {
    background: #00ff66;
    color: #020402;
}
Button.-danger {
    color: #ff4d5e;
    border: round #ff4d5e;
}
DataTable {
    background: #000000;
}
TextArea {
    border: round #164023;
    height: 18;
}
ProgressBar {
    width: 100%;
}
ProgressBar Bar {
    color: #00ff66;
}
"""


def _session() -> Session:
    return Session(engine)


# ---------------------------------------------------------------- dashboard


class DashboardScreen(Screen):
    BINDINGS = [
        Binding("p", "goto_problems", "problems"),
        Binding("l", "goto_learn", "learn"),
        Binding("q", "app.quit", "quit"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        with VerticalScroll():
            yield Static("", id="dash-body")
        yield Footer()

    def on_mount(self) -> None:
        self.refresh_dashboard()

    def refresh_dashboard(self) -> None:
        with _session() as session:
            stats = compute_dashboard_stats(session)

        lines = []
        lines.append(f"[b]{stats['solved_count']}/{stats['total']} solved[/b]  ({stats['pct']}%)")
        bar_width = 40
        filled = int(bar_width * stats["pct"] / 100)
        lines.append("[#00ff66]" + "#" * filled + "[/#00ff66]" + "-" * (bar_width - filled))
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
        lines.append("[dim]p: problems   l: learn   q: quit[/dim]")

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
    ]

    def __init__(self):
        super().__init__()
        self.sort_key = "created"
        self.sort_dir = "desc"

    def compose(self) -> ComposeResult:
        yield Header()
        yield DataTable(id="problems-table")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.cursor_type = "row"
        table.add_columns("Title", "Difficulty", "Topic", "Status")
        self.load_rows()

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
            yield Static("[b]Code[/b]")
            yield TextArea("", id="pd-code", language="python")
            with Horizontal():
                yield Button("run + review", id="pd-submit")
                yield Button("get hint", id="pd-hint")
                yield Button("reveal solution", id="pd-solution", classes="-danger")
            yield Static("", id="pd-result", classes="panel")
            yield Static("[b]My Notes[/b]")
            yield TextArea("", id="pd-notes")
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

        code_box = self.query_one("#pd-code", TextArea)
        code_box.text = problem.starter_code or f"def {fn_name}(*args):\n    pass"

        self.query_one("#pd-notes", TextArea).text = problem.my_notes or ""

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
        notes_text = self.query_one("#pd-notes", TextArea).text
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
        code = self.query_one("#pd-code", TextArea).text
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

        status = "[#00ff66]PASSED[/#00ff66]" if passed else "[#ff4d5e]FAILED[/#ff4d5e]"
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
    ]

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

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        data = event.node.data
        if not data:
            return
        lines = [
            f"[b]{esc(data['name'])}[/b]",
            "",
            esc(data["explanation"]),
            "",
            "[dim]template:[/dim]",
            esc(data["template"]),
        ]
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

    def on_mount(self) -> None:
        init_db()
        with _session() as session:
            seed_catalog(session)
        self.push_screen(DashboardScreen())


def main() -> None:
    LCTrainerApp().run()


if __name__ == "__main__":
    main()
