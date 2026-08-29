import json

from fastapi import FastAPI, Form, Request, Depends
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select

from app.db import get_session, init_db
from app.models import Problem, Submission, TestCase
from app.runner import run_submission
from app.claude_client import review_submission

app = FastAPI(title="LC Trainer")
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/")
def index(request: Request, session: Session = Depends(get_session)):
    problems = session.exec(select(Problem).order_by(Problem.created_at.desc())).all()
    return templates.TemplateResponse(
        "index.html", {"request": request, "problems": problems}
    )


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

    if passed and problem.status != "solved":
        problem.status = "solved"
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
