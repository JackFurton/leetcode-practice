"""Dashboard stat computation, shared between the web UI (main.py) and the
TUI (tui.py) so the two front ends never drift apart."""
from datetime import datetime, timedelta

from sqlmodel import Session, select

from app.curriculum import CURRICULUM
from app.models import Problem, Submission


def due_for_review(problems: list[Problem]) -> list[Problem]:
    now = datetime.utcnow()
    return [
        p
        for p in problems
        if p.status == "solved"
        and p.last_reviewed_at is not None
        and now >= p.last_reviewed_at + timedelta(days=p.review_interval_days)
    ]


def compute_dashboard_stats(session: Session) -> dict:
    problems = session.exec(select(Problem)).all()
    total = len(problems)
    solved_count = sum(1 for p in problems if p.status == "solved")
    pct = round(100 * solved_count / total) if total else 0

    diff_stats = []
    for d in ("Easy", "Medium", "Hard"):
        d_problems = [p for p in problems if p.difficulty == d]
        d_solved = sum(1 for p in d_problems if p.status == "solved")
        diff_stats.append({"label": d, "solved": d_solved, "total": len(d_problems)})

    by_title = {p.title: p for p in problems}
    category_progress = []
    for category in CURRICULUM:
        titles = category.get("practice", [])
        if not titles:
            continue
        matched = [by_title[t] for t in titles if t in by_title]
        solved = sum(1 for p in matched if p.status == "solved")
        category_progress.append(
            {"name": category["category"], "solved": solved, "total": len(titles)}
        )

    attempted = sorted((p for p in problems if p.status == "attempted"), key=lambda p: p.id)
    todo = sorted((p for p in problems if p.status == "todo"), key=lambda p: p.id)
    continue_problem = (attempted or todo or [None])[0]

    submission_days = {s.created_at.date() for s in session.exec(select(Submission)).all()}
    streak = 0
    cursor = datetime.utcnow().date()
    while cursor in submission_days:
        streak += 1
        cursor -= timedelta(days=1)

    return {
        "problems": problems,
        "total": total,
        "solved_count": solved_count,
        "pct": pct,
        "diff_stats": diff_stats,
        "category_progress": category_progress,
        "continue_problem": continue_problem,
        "streak": streak,
        "due_for_review": due_for_review(problems),
    }
