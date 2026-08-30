"""Pre-seeded system design prompts: classic interview-style scenarios
spanning the usual difficulty range. No test cases here (see
DESIGN_CATALOG_README in the module docstring of models.py) -- grading is
Claude reading the free-text answer against these constraints, not running
anything."""
from sqlmodel import Session, select

from app.models import DesignProblem

DESIGN_CATALOG = [
    {
        "title": "URL Shortener",
        "topic": "URL shortener",
        "difficulty": "Easy",
        "prompt": (
            "Design a service like bit.ly: given a long URL, return a short one; given the "
            "short one, redirect to the original."
        ),
        "constraints": [
            "100M new URLs/day, 100:1 read:write ratio",
            "short URLs should be as short as practical, ideally 7 characters or fewer",
            "redirects should be fast (aim for under 100ms)",
            "URLs should not be predictable/guessable in sequence",
            "links should be able to expire",
        ],
    },
    {
        "title": "Rate Limiter",
        "topic": "rate limiter",
        "difficulty": "Medium",
        "prompt": (
            "Design a rate limiter for an API gateway: reject requests from a client once they "
            "exceed N requests per time window."
        ),
        "constraints": [
            "must work across multiple gateway instances (distributed, not per-process)",
            "target under 10ms added latency per request",
            "support different limits per API key/tier",
            "should degrade gracefully if the shared state store is briefly unavailable",
        ],
    },
    {
        "title": "Chat System",
        "topic": "chat system",
        "difficulty": "Hard",
        "prompt": (
            "Design a one-on-one and small-group chat system like WhatsApp: send/receive "
            "messages in near real time, see delivery/read status, work across devices."
        ),
        "constraints": [
            "50M daily active users",
            "messages should arrive in well under 1 second when both parties are online",
            "must support offline delivery (message waits until the recipient reconnects)",
            "group chats up to 100 participants",
            "message history should be retrievable when a user reinstalls the app",
        ],
    },
    {
        "title": "News Feed",
        "topic": "news feed",
        "difficulty": "Hard",
        "prompt": (
            "Design a social media feed: users follow other users, and see a reverse-"
            "chronological (or ranked) feed of their followees' posts."
        ),
        "constraints": [
            "300M users, some accounts followed by millions (celebrities)",
            "feed load should feel instant (low hundreds of ms)",
            "posting should not be slow even for a celebrity with millions of followers",
            "feed doesn't need to be perfectly real-time, a few seconds of staleness is fine",
        ],
    },
    {
        "title": "Distributed Key-Value Store",
        "topic": "key-value store",
        "difficulty": "Hard",
        "prompt": (
            "Design a distributed key-value store (think a simplified DynamoDB/Cassandra): "
            "put(key, value) and get(key), horizontally scalable, tolerant of node failure."
        ),
        "constraints": [
            "must survive losing a minority of nodes with no data loss",
            "favor availability over strict consistency (eventual consistency is acceptable)",
            "even distribution of keys across nodes, no hot spots",
            "adding/removing a node shouldn't require reshuffling all the data",
        ],
    },
    {
        "title": "Job Queue / Task Scheduler",
        "topic": "job queue",
        "difficulty": "Medium",
        "prompt": (
            "Design a background job system: producers enqueue jobs (some scheduled for "
            "the future), workers pull and execute them, failed jobs get retried."
        ),
        "constraints": [
            "10K jobs/second at peak",
            "a job must not be processed by two workers at once",
            "failed jobs retry with backoff, and eventually go to a dead-letter queue",
            "support jobs scheduled to run at a specific future time",
            "a crashed worker mid-job shouldn't silently lose that job",
        ],
    },
    {
        "title": "Web Crawler",
        "topic": "web crawler",
        "difficulty": "Medium",
        "prompt": (
            "Design a web crawler: given a set of seed URLs, crawl the web, store page "
            "content, and discover new URLs to crawl from links on each page."
        ),
        "constraints": [
            "billions of pages over time",
            "must respect robots.txt and not hammer any single host",
            "should not crawl the same URL repeatedly in a short window",
            "crawling should be parallelizable across many workers",
            "must handle crawler traps (infinite link chains, e.g. calendar pages)",
        ],
    },
    {
        "title": "Notification System",
        "topic": "notifications",
        "difficulty": "Medium",
        "prompt": (
            "Design a notification system that can deliver a notification to a user via "
            "push, email, and SMS, triggered by events from other internal services."
        ),
        "constraints": [
            "10M notifications/day across all channels",
            "if push delivery fails, fall back to email",
            "a user should not get duplicate notifications for the same event",
            "must support per-user preferences (which channels, opted out of what)",
            "one slow/down channel (e.g. an SMS provider outage) shouldn't back up the others",
        ],
    },
]


def seed_design_catalog(session: Session) -> None:
    if session.exec(select(DesignProblem)).first() is not None:
        return  # already seeded, don't touch existing data

    print(f"Seeding system design catalog ({len(DESIGN_CATALOG)} problems)...")
    for entry in DESIGN_CATALOG:
        session.add(
            DesignProblem(
                title=entry["title"],
                prompt=entry["prompt"],
                constraints="\n".join(entry["constraints"]),
                difficulty=entry["difficulty"],
                topic=entry["topic"],
            )
        )
    session.commit()
