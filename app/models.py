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
    created_at: datetime = Field(default_factory=datetime.utcnow)


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
