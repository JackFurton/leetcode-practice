from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class Problem(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    url: Optional[str] = None  # link to algo.monster / leetcode page
    difficulty: str = "Medium"  # Easy / Medium / Hard
    topic: Optional[str] = None  # e.g. "Two Pointers", "DP"
    status: str = "todo"  # todo / attempted / solved
    notes: Optional[str] = None
    my_notes: Optional[str] = None  # user's own scratch notes, separate from the system notes
    constraints: Optional[str] = None  # one bullet per line, LeetCode-style
    starter_code: Optional[str] = None
    function_name: Optional[str] = None  # name the runner calls, defaults to "solve"
    cached_solution: Optional[str] = None  # generated once, reused on repeat "reveal" clicks
    created_at: datetime = Field(default_factory=datetime.utcnow)
    # spaced repetition
    last_reviewed_at: Optional[datetime] = None
    review_interval_days: int = 1


class TestCase(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    problem_id: int = Field(foreign_key="problem.id")
    # JSON-encoded list of positional args passed to solve(*args)
    input_json: str
    # JSON-encoded expected return value
    expected_json: str


class Submission(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    problem_id: int = Field(foreign_key="problem.id")
    code: str
    language: str = "python"
    passed: bool = False
    # JSON-encoded list of per-test-case results
    results_json: str
    review: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class TopicProgress(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    topic: str = Field(unique=True)
    done: bool = False


class ProblemStarter(SQLModel, table=True):
    """Per-language starter code for a problem, for every language besides
    Python (which stays on Problem.starter_code/function_name for backward
    compatibility). Typed languages also need arg/return type info so the
    runner can render each test case as a correctly-typed literal instead
    of relying on Python's dynamic *args."""

    id: Optional[int] = Field(default=None, primary_key=True)
    problem_id: int = Field(foreign_key="problem.id")
    language: str  # "go", "typescript", ...
    starter_code: str
    function_name: str
    arg_types: str  # JSON list of language-specific type strings, one per positional arg
    return_type: str
    cached_solution: Optional[str] = None


class SqlProblem(SQLModel, table=True):
    """SQL problems don't fit the function-signature shape ProblemStarter
    assumes (no function_name/args), so they get their own table: a schema
    to stand up in a fresh in-memory SQLite db, and the expected result set
    of the canonical query, run and captured for real (not hand-typed) so
    grading can't drift from what the reference query actually returns."""

    id: Optional[int] = Field(default=None, primary_key=True)
    problem_id: int = Field(foreign_key="problem.id")
    setup_sql: str  # CREATE TABLE + INSERT statements, replayed fresh each submission
    starter_code: str  # e.g. "-- write your query below\nSELECT"
    expected_columns: str  # JSON list of column names, for display
    expected_rows: str  # JSON list of row lists, order-insensitive compare
    cached_solution: Optional[str] = None
