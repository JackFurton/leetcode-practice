import json
from datetime import datetime, timedelta

from fastapi import FastAPI, Form, HTTPException, Request, Depends
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select

from app.curriculum import CURRICULUM
from app.db import get_session, init_db
from app.leetcode_client import fetch_problem
from app.models import Problem, Submission, TestCase, TopicProgress
from app.runner import run_submission
from app.claude_client import review_submission

MAX_REVIEW_INTERVAL_DAYS = 30

app = FastAPI(title="LC Trainer")
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/")
def index(request: Request, session: Session = Depends(get_session)):
    problems = session.exec(select(Problem).order_by(Problem.created_at.desc())).all()

    now = datetime.utcnow()
    due_for_review = [
        p
        for p in problems
        if p.status == "solved"
        and p.last_reviewed_at is not None
        and now >= p.last_reviewed_at + timedelta(days=p.review_interval_days)
    ]

    return templates.TemplateResponse(
        "index.html",
        {"request": request, "problems": problems, "due_for_review": due_for_review},
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
    return templates.TemplateResponse(
        "problem.html",
        {
            "request": request,
            "problem": problem,
            "test_cases": test_cases,
            "submissions": submissions,
        },
    )


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
    result = run_submission(code, cases)

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


@app.get("/learn")
def learn(request: Request, session: Session = Depends(get_session)):
    existing = {tp.topic for tp in session.exec(select(TopicProgress)).all()}
    for category in CURRICULUM:
        for topic in category["topics"]:
            if topic not in existing:
                session.add(TopicProgress(topic=topic))
    session.commit()

    progress = session.exec(select(TopicProgress)).all()
    done_map = {p.topic: p.done for p in progress}

    return templates.TemplateResponse(
        "learn.html",
        {"request": request, "curriculum": CURRICULUM, "done_map": done_map},
    )


@app.post("/learn/toggle")
def toggle_topic(
    request: Request, topic: str = Form(...), session: Session = Depends(get_session)
):
    tp = session.exec(select(TopicProgress).where(TopicProgress.topic == topic)).first()
    tp.done = not tp.done
    session.add(tp)
    session.commit()
    return templates.TemplateResponse(
        "_topic_item.html", {"request": request, "topic": topic, "done": tp.done}
    )
