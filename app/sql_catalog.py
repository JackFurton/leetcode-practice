"""Pre-seeded SQL problems: a schema (CREATE TABLE + INSERT) and a
canonical query, run for real via sqlite3 at authoring time to capture
expected_columns/expected_rows, so grading can never drift from what the
reference query actually returns. Same seed-once pattern as seed_catalog.py.
"""
import json

from sqlmodel import Session, select

from app.models import Problem, SqlProblem

SQL_CATALOG = [
    {
        'title': 'SQL 1. Combine Two Tables',
        'difficulty': 'Easy',
        'notes': "Return each employee's name alongside their department's name. Employees with no department (dept_id is NULL) should still show up, with a NULL department name.",
        'constraints': ['employees(id, name, dept_id)', 'departments(id, name)', 'dept_id may be NULL', 'keep every employee, even with no matching department'],
        'setup_sql': "CREATE TABLE employees (id INTEGER PRIMARY KEY, name TEXT, dept_id INTEGER);\n        CREATE TABLE departments (id INTEGER PRIMARY KEY, name TEXT);\n        INSERT INTO employees VALUES (1, 'Ada', 10), (2, 'Grace', 20), (3, 'Linus', NULL);\n        INSERT INTO departments VALUES (10, 'Engineering'), (20, 'Research');",
        'starter_code': '-- write your query below\nSELECT',
        'expected_columns': ['name', 'dept_name'],
        'expected_rows': [['Ada', 'Engineering'], ['Grace', 'Research'], ['Linus', None]],
        'cached_solution': "**Approach**: A LEFT JOIN from employees to departments keeps every employee row even when dept_id doesn't match anything (or is NULL) -- an INNER JOIN would silently drop Linus.\n\n**Solution**:\n```sql\nSELECT employees.name AS name, departments.name AS dept_name\n        FROM employees\n        LEFT JOIN departments ON employees.dept_id = departments.id\n```\n\n**Why this works**: it was run against the real schema above to produce the expected result, not hand-typed.",
    },
    {
        'title': 'SQL 2. Second Highest Salary',
        'difficulty': 'Medium',
        'notes': 'Return the second highest distinct salary from the employees table. If there is no second highest salary (fewer than 2 distinct salaries), return NULL.',
        'constraints': ['employees(id, name, salary)', "distinct salaries, so ties don't shift the ranking", "return NULL, not an empty result, when there's no second value"],
        'setup_sql': "CREATE TABLE employees (id INTEGER PRIMARY KEY, name TEXT, salary INTEGER);\n        INSERT INTO employees VALUES (1, 'Ada', 90000), (2, 'Grace', 120000),\n            (3, 'Linus', 120000), (4, 'Margaret', 75000);",
        'starter_code': '-- write your query below\nSELECT',
        'expected_columns': ['second_highest'],
        'expected_rows': [[90000]],
        'cached_solution': '**Approach**: DISTINCT collapses tied salaries before ranking, then ORDER BY ... DESC LIMIT 1 OFFSET 1 skips the top value to land on the second. Wrapping it in a subquery makes a missing row become NULL instead of an empty result set.\n\n**Solution**:\n```sql\nSELECT (\n            SELECT DISTINCT salary FROM employees\n            ORDER BY salary DESC LIMIT 1 OFFSET 1\n        ) AS second_highest\n```\n\n**Why this works**: it was run against the real schema above to produce the expected result, not hand-typed.',
    },
    {
        'title': 'SQL 3. Duplicate Emails',
        'difficulty': 'Easy',
        'notes': 'Return every email address that appears more than once in the emails table.',
        'constraints': ['emails(id, email)', 'one row per email that repeats, not per occurrence'],
        'setup_sql': "CREATE TABLE emails (id INTEGER PRIMARY KEY, email TEXT);\n        INSERT INTO emails VALUES (1, 'a@x.com'), (2, 'b@x.com'), (3, 'a@x.com'),\n            (4, 'c@x.com'), (5, 'a@x.com');",
        'starter_code': '-- write your query below\nSELECT',
        'expected_columns': ['email'],
        'expected_rows': [['a@x.com']],
        'cached_solution': '**Approach**: GROUP BY email collapses repeats into one row per distinct email, and HAVING COUNT(*) > 1 filters to just the ones that actually repeated (HAVING, not WHERE, because it filters on an aggregate).\n\n**Solution**:\n```sql\nSELECT email FROM emails\n        GROUP BY email\n        HAVING COUNT(*) > 1\n```\n\n**Why this works**: it was run against the real schema above to produce the expected result, not hand-typed.',
    },
    {
        'title': 'SQL 4. Department Top Earner',
        'difficulty': 'Medium',
        'notes': "For each department, return the department's name, the employee's name, and their salary, for whichever employee(s) earn the max salary in that department (a tie means both show up).",
        'constraints': ['departments(id, name)', 'employees(id, name, salary, dept_id)', 'ties in a department both show up'],
        'setup_sql': "CREATE TABLE departments (id INTEGER PRIMARY KEY, name TEXT);\n        CREATE TABLE employees (id INTEGER PRIMARY KEY, name TEXT, salary INTEGER, dept_id INTEGER);\n        INSERT INTO departments VALUES (10, 'Engineering'), (20, 'Research');\n        INSERT INTO employees VALUES\n            (1, 'Ada', 120000, 10), (2, 'Grace', 120000, 10),\n            (3, 'Linus', 95000, 10), (4, 'Margaret', 110000, 20);",
        'starter_code': '-- write your query below\nSELECT',
        'expected_columns': ['dept_name', 'employee_name', 'salary'],
        'expected_rows': [['Engineering', 'Ada', 120000], ['Engineering', 'Grace', 120000], ['Research', 'Margaret', 110000]],
        'cached_solution': "**Approach**: A correlated subquery finds each department's own max salary, then the outer query keeps only employees matching that max within their own department -- naturally including ties.\n\n**Solution**:\n```sql\nSELECT departments.name AS dept_name, employees.name AS employee_name, employees.salary AS salary\n        FROM employees\n        JOIN departments ON employees.dept_id = departments.id\n        WHERE employees.salary = (\n            SELECT MAX(e2.salary) FROM employees e2 WHERE e2.dept_id = employees.dept_id\n        )\n```\n\n**Why this works**: it was run against the real schema above to produce the expected result, not hand-typed.",
    },
    {
        'title': 'SQL 5. Customers Who Never Order',
        'difficulty': 'Easy',
        'notes': 'Return the names of customers who have never placed an order.',
        'constraints': ['customers(id, name)', 'orders(id, customer_id)'],
        'setup_sql': "CREATE TABLE customers (id INTEGER PRIMARY KEY, name TEXT);\n        CREATE TABLE orders (id INTEGER PRIMARY KEY, customer_id INTEGER);\n        INSERT INTO customers VALUES (1, 'Ada'), (2, 'Grace'), (3, 'Linus');\n        INSERT INTO orders VALUES (100, 1), (101, 1), (102, 2);",
        'starter_code': '-- write your query below\nSELECT',
        'expected_columns': ['name'],
        'expected_rows': [['Linus']],
        'cached_solution': '**Approach**: LEFT JOIN customers to orders, then WHERE orders.id IS NULL keeps only the customers whose join found nothing to attach.\n\n**Solution**:\n```sql\nSELECT customers.name AS name\n        FROM customers\n        LEFT JOIN orders ON customers.id = orders.customer_id\n        WHERE orders.id IS NULL\n```\n\n**Why this works**: it was run against the real schema above to produce the expected result, not hand-typed.',
    },
    {
        'title': 'SQL 6. Rising Temperature',
        'difficulty': 'Easy',
        'notes': "Return the ids of weather records where the temperature was higher than the previous calendar day's temperature.",
        'constraints': ['weather(id, record_date, temperature)', 'record_date is an ISO date string, one row per day'],
        'setup_sql': "CREATE TABLE weather (id INTEGER PRIMARY KEY, record_date TEXT, temperature INTEGER);\n        INSERT INTO weather VALUES\n            (1, '2024-01-01', 50), (2, '2024-01-02', 55), (3, '2024-01-03', 52),\n            (4, '2024-01-04', 60);",
        'starter_code': '-- write your query below\nSELECT',
        'expected_columns': ['id'],
        'expected_rows': [[2], [4]],
        'cached_solution': "**Approach**: Self-join weather to itself where one row's date is exactly one day after the other's, then keep the pairs where the later day's temperature is higher.\n\n**Solution**:\n```sql\nSELECT w1.id AS id\n        FROM weather w1\n        JOIN weather w2 ON date(w1.record_date) = date(w2.record_date, '+1 day')\n        WHERE w1.temperature > w2.temperature\n```\n\n**Why this works**: it was run against the real schema above to produce the expected result, not hand-typed.",
    },
]


def seed_sql_catalog(session: Session) -> None:
    if session.exec(select(Problem).where(Problem.topic == "SQL")).first() is not None:
        return  # already seeded, don't touch existing data

    print(f"Seeding SQL catalog ({len(SQL_CATALOG)} problems)...")
    for entry in SQL_CATALOG:
        problem = Problem(
            title=entry['title'],
            difficulty=entry['difficulty'],
            topic="SQL",
            notes=entry['notes'],
            constraints="\n".join(entry['constraints']),
            starter_code=None,
            function_name=None,
        )
        session.add(problem)
        session.flush()
        session.add(
            SqlProblem(
                problem_id=problem.id,
                setup_sql=entry['setup_sql'],
                starter_code=entry['starter_code'],
                expected_columns=json.dumps(entry['expected_columns']),
                expected_rows=json.dumps(entry['expected_rows']),
                cached_solution=entry['cached_solution'],
            )
        )
    session.commit()
