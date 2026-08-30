"""Pre-seeded bash/shell problems: stdin -> stdout, each expected output
captured by actually running the reference script via `bash` at authoring
time, not hand-typed. Same seed-once pattern as sql_catalog.py.
"""
from sqlmodel import Session, select

from app.models import BashProblem, BashTestCase, Problem

BASH_CATALOG = [
    {
        'title': 'Bash 1. Tenth Line',
        'difficulty': 'Easy',
        'notes': 'Print just the 10th line of stdin. If there are fewer than 10 lines, print nothing.',
        'constraints': ['reads from stdin', 'print exactly line 10, nothing else'],
        'starter_code': '#!/usr/bin/env bash\n# read from stdin, write to stdout\n',
        'test_cases': [('line 1\nline 2\nline 3\nline 4\nline 5\nline 6\nline 7\nline 8\nline 9\nline 10\nline 11\nline 12\nline 13\nline 14\n', 'line 10\n'), ('line 1\nline 2\nline 3\n', '')],
        'cached_solution': "**Approach**: awk tracks the record number (NR) automatically; print only when it equals 10.\n\n**Solution**:\n```bash\nawk 'NR==10'\n```\n\n**Why this works**: it was run for real against the example input above to produce the expected output, not hand-typed.",
    },
    {
        'title': 'Bash 2. Word Frequency',
        'difficulty': 'Medium',
        'notes': "Count occurrences of each word in stdin (words separated by whitespace). Print one 'word count' pair per line, sorted by count descending, ties broken alphabetically by word.",
        'constraints': ['reads from stdin', 'words are whitespace-separated', "output format: 'word count', one per line"],
        'starter_code': '#!/usr/bin/env bash\n# read from stdin, write to stdout\n',
        'test_cases': [('the quick brown fox the lazy dog the fox runs\n', 'the 3\nfox 2\nbrown 1\ndog 1\nlazy 1\nquick 1\nruns 1\n'), ('a a b b b c\n', 'b 3\na 2\nc 1\n')],
        'cached_solution': "**Approach**: Split on any whitespace onto one word per line, drop blank lines, sort so identical words are adjacent, uniq -c counts each run, then sort numerically descending on the count with a secondary alphabetical sort on the word for ties.\n\n**Solution**:\n```bash\ntr -s '[:space:]' '\\n' | sed '/^$/d' | sort | uniq -c | sort -k1,1nr -k2,2 | awk '{print $2, $1}'\n```\n\n**Why this works**: it was run for real against the example input above to produce the expected output, not hand-typed.",
    },
    {
        'title': 'Bash 3. Valid Phone Numbers',
        'difficulty': 'Easy',
        'notes': 'Print only the lines from stdin that are valid US phone numbers, matching either XXX-XXX-XXXX or (XXX) XXX-XXXX (X is a digit).',
        'constraints': ['reads from stdin, one candidate number per line', 'only two formats count as valid: 123-456-7890 or (123) 456-7890'],
        'starter_code': '#!/usr/bin/env bash\n# read from stdin, write to stdout\n',
        'test_cases': [('987-123-4567\n123 456 7890\n(123) 456-7890\n123-456-78900\n', '987-123-4567\n(123) 456-7890\n')],
        'cached_solution': "**Approach**: A single anchored extended regex matches either of the two allowed formats; grep -E prints only the lines that match.\n\n**Solution**:\n```bash\ngrep -E '^([0-9]{3}-|\\([0-9]{3}\\) )[0-9]{3}-[0-9]{4}$'\n```\n\n**Why this works**: it was run for real against the example input above to produce the expected output, not hand-typed.",
    },
    {
        'title': 'Bash 4. Transpose File',
        'difficulty': 'Medium',
        'notes': 'Transpose a whitespace-separated matrix from stdin: row i column j of the input becomes row j column i of the output.',
        'constraints': ['reads from stdin', 'fields separated by single spaces, all rows the same width', 'output fields separated by single spaces'],
        'starter_code': '#!/usr/bin/env bash\n# read from stdin, write to stdout\n',
        'test_cases': [('1 2 3\n4 5 6\n7 8 9\n', '1 4 7\n2 5 8\n3 6 9\n'), ('a b\nc d\n', 'a c\nb d\n')],
        'cached_solution': '**Approach**: Buffer every field into a 2D awk array keyed by (column, row) while reading, then in END print it back out reading column-major instead of row-major.\n\n**Solution**:\n```bash\nawk \'{ for (i=1;i<=NF;i++) a[i,NR]=$i; if (NF>maxNF) maxNF=NF } END { for (i=1;i<=maxNF;i++) { row=a[i,1]; for (j=2;j<=NR;j++) row = row" "a[i,j]; print row } }\'\n```\n\n**Why this works**: it was run for real against the example input above to produce the expected output, not hand-typed.',
    },
    {
        'title': 'Bash 5. Count 5xx Errors',
        'difficulty': 'Easy',
        'notes': "Given access-log lines in the form '<ip> <timestamp> <method> <path> <status> <bytes>', print the count of lines whose status code is in the 500s.",
        'constraints': ['reads from stdin, one log line per line', "status code is field 5, e.g. '10.0.0.1 2024-01-01T10:00:00Z GET /a 500 512'", 'print a single integer: the count'],
        'starter_code': '#!/usr/bin/env bash\n# read from stdin, write to stdout\n',
        'test_cases': [('10.0.0.1 2024-01-01T10:00:00Z GET / 200 100\n10.0.0.2 2024-01-01T10:00:01Z GET /a 500 50\n10.0.0.3 2024-01-01T10:00:02Z GET /b 503 12\n10.0.0.4 2024-01-01T10:00:03Z GET /c 404 20\n', '2\n')],
        'cached_solution': "**Approach**: awk filters to lines whose 9th field starts with 5, wc -l counts the surviving lines.\n\n**Solution**:\n```bash\nawk '$5 ~ /^5/' | wc -l | tr -d ' '\n```\n\n**Why this works**: it was run for real against the example input above to produce the expected output, not hand-typed.",
    },
    {
        'title': 'Bash 6. Unique IPs',
        'difficulty': 'Easy',
        'notes': 'Given access-log lines where the client IP is the 1st whitespace-separated field, print the count of distinct IPs.',
        'constraints': ['reads from stdin, one log line per line', 'IP is field 1', 'print a single integer: the count of distinct IPs'],
        'starter_code': '#!/usr/bin/env bash\n# read from stdin, write to stdout\n',
        'test_cases': [('10.0.0.1 GET /\n10.0.0.2 GET /a\n10.0.0.1 GET /b\n10.0.0.3 GET /c\n', '3\n')],
        'cached_solution': "**Approach**: Extract just the first field, sort -u collapses it to distinct values, wc -l counts them.\n\n**Solution**:\n```bash\nawk '{print $1}' | sort -u | wc -l | tr -d ' '\n```\n\n**Why this works**: it was run for real against the example input above to produce the expected output, not hand-typed.",
    },
]


def seed_bash_catalog(session: Session) -> None:
    if session.exec(select(Problem).where(Problem.topic == "Bash")).first() is not None:
        return  # already seeded, don't touch existing data

    print(f"Seeding bash catalog ({len(BASH_CATALOG)} problems)...")
    for entry in BASH_CATALOG:
        problem = Problem(
            title=entry['title'],
            difficulty=entry['difficulty'],
            topic="Bash",
            notes=entry['notes'],
            constraints="\n".join(entry['constraints']),
            starter_code=None,
            function_name=None,
        )
        session.add(problem)
        session.flush()
        session.add(
            BashProblem(
                problem_id=problem.id,
                starter_code=entry['starter_code'],
                cached_solution=entry['cached_solution'],
            )
        )
        for stdin_text, expected_stdout in entry['test_cases']:
            session.add(
                BashTestCase(
                    problem_id=problem.id,
                    stdin=stdin_text,
                    expected_stdout=expected_stdout,
                )
            )
    session.commit()
