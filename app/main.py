import json
from datetime import datetime, timedelta

from fastapi import FastAPI, Form, HTTPException, Request, Depends
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select

from app.curriculum import CURRICULUM, CATEGORY_BY_TITLE
from app.db import engine, get_session, init_db
from app.leetcode_client import fetch_problem
from app.models import Problem, Submission, TestCase, TopicProgress
from app.runner import run_submission
from app.seed_catalog import seed_catalog
from app.claude_client import review_submission, get_hint, get_solution

MAX_REVIEW_INTERVAL_DAYS = 30

app = FastAPI(title="LC Trainer")
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")


def _pretty_value(v):
    """Render a raw JSON value (possibly one of runner.py's structure
    wrapper dicts) as a short, readable string for the test-case list."""
    if isinstance(v, dict) and set(v.keys()) == {"type", "value"}:
        return f'{v["type"]}({json.dumps(v["value"])})'
    return json.dumps(v)


def _pretty_args(raw_json: str) -> str:
    return ", ".join(_pretty_value(a) for a in json.loads(raw_json))


def _pretty_expected(raw_json: str) -> str:
    return _pretty_value(json.loads(raw_json))


templates.env.filters["pretty_args"] = _pretty_args
templates.env.filters["pretty_value"] = _pretty_expected

_WRAPPER_EXAMPLES = {
    "linked_list": '{"type": "linked_list", "value": [1, 2, 3]}',
    "linked_list_cycle": '{"type": "linked_list_cycle", "value": {"vals": [3, 2, 0], "pos": 1}}',
    "tree": '{"type": "tree", "value": [1, null, 2]}',
    "list_of_lists_unordered": "order doesn't matter for this one, any valid arrangement passes",
}


def _structure_hint(test_cases: list[TestCase]) -> str | None:
    """Only mention the structure-wrapper convention when this problem's
    test cases actually use one, and show the type it actually uses."""
    types_present = set()
    for tc in test_cases:
        for raw in (tc.input_json, tc.expected_json):
            data = json.loads(raw)
            for item in data if isinstance(data, list) else [data]:
                if isinstance(item, dict) and set(item.keys()) == {"type", "value"}:
                    types_present.add(item["type"])
    examples = [_WRAPPER_EXAMPLES[t] for t in sorted(types_present) if t in _WRAPPER_EXAMPLES]
    return ", ".join(examples) if examples else None


@app.on_event("startup")
def on_startup():
    init_db()
    with Session(engine) as session:
        seed_catalog(session)


DIFFICULTY_ORDER = {"Easy": 0, "Medium": 1, "Hard": 2}
STATUS_ORDER = {"todo": 0, "attempted": 1, "solved": 2}

_SORT_KEYS = {
    "title": lambda p: p.title.lower(),
    "difficulty": lambda p: DIFFICULTY_ORDER.get(p.difficulty, 99),
    "topic": lambda p: (p.topic or "").lower(),
    "status": lambda p: STATUS_ORDER.get(p.status, 99),
    "created": lambda p: p.created_at,
}


def _sorted_problems(session: Session, sort: str, dir: str):
    if sort not in _SORT_KEYS:
        sort = "created"
    problems = session.exec(select(Problem)).all()
    problems.sort(key=_SORT_KEYS[sort], reverse=(dir == "desc"))
    return problems, sort


@app.get("/problems/table")
def problems_table(
    request: Request,
    sort: str = "created",
    dir: str = "desc",
    session: Session = Depends(get_session),
):
    problems, sort = _sorted_problems(session, sort, dir)
    return templates.TemplateResponse(
        "_problem_table.html",
        {"request": request, "problems": problems, "sort": sort, "dir": dir},
    )


def _due_for_review(problems: list[Problem]) -> list[Problem]:
    now = datetime.utcnow()
    return [
        p
        for p in problems
        if p.status == "solved"
        and p.last_reviewed_at is not None
        and now >= p.last_reviewed_at + timedelta(days=p.review_interval_days)
    ]


@app.get("/")
def dashboard(request: Request, session: Session = Depends(get_session)):
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

    submission_days = {
        s.created_at.date() for s in session.exec(select(Submission)).all()
    }
    streak = 0
    cursor = datetime.utcnow().date()
    while cursor in submission_days:
        streak += 1
        cursor -= timedelta(days=1)

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "total": total,
            "solved_count": solved_count,
            "pct": pct,
            "diff_stats": diff_stats,
            "category_progress": category_progress,
            "continue_problem": continue_problem,
            "streak": streak,
            "due_for_review": _due_for_review(problems),
        },
    )


@app.get("/problems")
def problems_page(
    request: Request,
    sort: str = "created",
    dir: str = "desc",
    session: Session = Depends(get_session),
):
    problems, sort = _sorted_problems(session, sort, dir)
    return templates.TemplateResponse(
        "problems.html",
        {"request": request, "problems": problems, "sort": sort, "dir": dir},
    )


@app.post("/problems/fetch")
def fetch_problem_route(url: str = Form(...), session: Session = Depends(get_session)):
    data = fetch_problem(url)
    if not data:
        raise HTTPException(
            400, "Couldn't fetch that URL. Only LeetCode problem links are supported, add others manually."
        )
    problem = Problem(**data)
    session.add(problem)
    session.commit()
    session.refresh(problem)
    return RedirectResponse(f"/problems/{problem.id}", status_code=303)


@app.post("/problems")
def create_problem(
    title: str = Form(...),
    url: str = Form(""),
    difficulty: str = Form("Medium"),
    topic: str = Form(""),
    notes: str = Form(""),
    session: Session = Depends(get_session),
):
    problem = Problem(
        title=title,
        url=url or None,
        difficulty=difficulty,
        topic=topic or None,
        notes=notes or None,
    )
    session.add(problem)
    session.commit()
    session.refresh(problem)
    return RedirectResponse(f"/problems/{problem.id}", status_code=303)


@app.get("/problems/{problem_id}")
def problem_detail(
    problem_id: int, request: Request, session: Session = Depends(get_session)
):
    problem = session.get(Problem, problem_id)
    test_cases = session.exec(
        select(TestCase).where(TestCase.problem_id == problem_id)
    ).all()
    submissions = session.exec(
        select(Submission)
        .where(Submission.problem_id == problem_id)
        .order_by(Submission.created_at.desc())
    ).all()
    prev_problem = session.exec(
        select(Problem).where(Problem.id < problem_id).order_by(Problem.id.desc()).limit(1)
    ).first()
    next_problem = session.exec(
        select(Problem).where(Problem.id > problem_id).order_by(Problem.id).limit(1)
    ).first()
    return templates.TemplateResponse(
        "problem.html",
        {
            "request": request,
            "problem": problem,
            "test_cases": test_cases,
            "submissions": submissions,
            "structure_hint": _structure_hint(test_cases),
            "category": CATEGORY_BY_TITLE.get(problem.title),
            "prev_problem": prev_problem,
            "next_problem": next_problem,
        },
    )


@app.post("/problems/{problem_id}/notes")
def save_notes(
    problem_id: int, my_notes: str = Form(""), session: Session = Depends(get_session)
):
    problem = session.get(Problem, problem_id)
    problem.my_notes = my_notes or None
    session.add(problem)
    session.commit()
    return RedirectResponse(f"/problems/{problem_id}", status_code=303)


@app.post("/problems/{problem_id}/status")
def update_status(
    problem_id: int, status: str = Form(...), session: Session = Depends(get_session)
):
    problem = session.get(Problem, problem_id)
    problem.status = status
    session.add(problem)
    session.commit()
    return RedirectResponse(f"/problems/{problem_id}", status_code=303)


@app.post("/problems/{problem_id}/testcases")
def add_test_case(
    problem_id: int,
    input_json: str = Form(...),
    expected_json: str = Form(...),
    session: Session = Depends(get_session),
):
    # validate JSON before saving
    json.loads(input_json)
    json.loads(expected_json)
    tc = TestCase(
        problem_id=problem_id, input_json=input_json, expected_json=expected_json
    )
    session.add(tc)
    session.commit()
    return RedirectResponse(f"/problems/{problem_id}", status_code=303)


@app.post("/problems/{problem_id}/submit")
def submit_code(
    problem_id: int,
    request: Request,
    code: str = Form(...),
    session: Session = Depends(get_session),
):
    problem = session.get(Problem, problem_id)
    test_cases = session.exec(
        select(TestCase).where(TestCase.problem_id == problem_id)
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
        problem_id=problem_id,
        code=code,
        passed=passed,
        results_json=json.dumps(result),
        review=review_text,
    )
    session.add(submission)

    if passed:
        now = datetime.utcnow()
        if problem.status == "solved":
            # a review pass on an already-solved problem: push interval out further
            problem.review_interval_days = min(
                problem.review_interval_days * 2, MAX_REVIEW_INTERVAL_DAYS
            )
        else:
            problem.status = "solved"
            problem.review_interval_days = 1
        problem.last_reviewed_at = now
        session.add(problem)
    elif not passed and problem.status == "todo":
        problem.status = "attempted"
        session.add(problem)

    session.commit()
    session.refresh(submission)

    return templates.TemplateResponse(
        "_submission_result.html",
        {"request": request, "submission": submission, "result": result},
    )


@app.post("/problems/{problem_id}/hint")
def problem_hint(
    problem_id: int, request: Request, session: Session = Depends(get_session)
):
    problem = session.get(Problem, problem_id)
    hint_text = get_hint(
        problem_title=problem.title,
        problem_notes=problem.notes,
        difficulty=problem.difficulty,
    )
    return templates.TemplateResponse(
        "_hint_result.html", {"request": request, "hint": hint_text}
    )


@app.post("/problems/{problem_id}/solution")
def problem_solution(
    problem_id: int, request: Request, session: Session = Depends(get_session)
):
    problem = session.get(Problem, problem_id)
    if not problem.cached_solution:
        problem.cached_solution = get_solution(
            problem_title=problem.title,
            problem_notes=problem.notes,
            difficulty=problem.difficulty,
            function_name=problem.function_name or "solve",
            starter_code=problem.starter_code,
        )
        session.add(problem)
        session.commit()
    return templates.TemplateResponse(
        "_solution_result.html", {"request": request, "solution": problem.cached_solution}
    )


@app.get("/learn")
def learn(request: Request, session: Session = Depends(get_session)):
    existing = {tp.topic for tp in session.exec(select(TopicProgress)).all()}
    for category in CURRICULUM:
        for topic in category["topics"]:
            if topic["name"] not in existing:
                session.add(TopicProgress(topic=topic["name"]))
    session.commit()

    progress = session.exec(select(TopicProgress)).all()
    done_map = {p.topic: p.done for p in progress}

    return templates.TemplateResponse(
        "learn.html",
        {"request": request, "curriculum": CURRICULUM, "done_map": done_map},
    )


def _find_topic(name: str) -> dict:
    for category in CURRICULUM:
        for t in category["topics"]:
            if t["name"] == name:
                return t
    return {"name": name, "explanation": "", "template": ""}


@app.post("/learn/toggle")
def toggle_topic(
    request: Request, topic: str = Form(...), session: Session = Depends(get_session)
):
    tp = session.exec(select(TopicProgress).where(TopicProgress.topic == topic)).first()
    tp.done = not tp.done
    session.add(tp)
    session.commit()
    return templates.TemplateResponse(
        "_topic_item.html",
        {"request": request, "topic": _find_topic(topic), "done": tp.done},
    )
