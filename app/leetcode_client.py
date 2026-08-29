"""Auto-fetch problem title/difficulty/tags/description from a LeetCode
problem URL via LeetCode's public GraphQL endpoint. No auth needed for
public problem data."""
import html
import re

import httpx

GRAPHQL_URL = "https://leetcode.com/graphql"

QUERY = """
query questionData($titleSlug: String!) {
  question(titleSlug: $titleSlug) {
    questionFrontendId
    title
    difficulty
    content
    topicTags { name }
  }
}
"""


def extract_slug(url: str) -> str | None:
    m = re.search(r"leetcode\.com/problems/([a-z0-9\-]+)", url)
    return m.group(1) if m else None


def _html_to_text(raw: str) -> str:
    text = re.sub(r"<[^>]+>", "\n", raw or "")
    text = html.unescape(text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text


def fetch_problem(url: str) -> dict | None:
    """Returns {title, difficulty, topic, notes, url} or None if not a
    recognized LeetCode URL / problem not found."""
    slug = extract_slug(url)
    if not slug:
        return None

    resp = httpx.post(
        GRAPHQL_URL,
        json={"query": QUERY, "variables": {"titleSlug": slug}},
        headers={
            "Content-Type": "application/json",
            "Referer": f"https://leetcode.com/problems/{slug}/",
        },
        timeout=10,
    )
    resp.raise_for_status()
    question = resp.json().get("data", {}).get("question")
    if not question:
        return None

    topics = ", ".join(t["name"] for t in question.get("topicTags", []))
    return {
        "title": f"{question['questionFrontendId']}. {question['title']}",
        "difficulty": question["difficulty"],
        "topic": topics,
        "notes": _html_to_text(question.get("content", ""))[:4000],
        "url": url,
    }
