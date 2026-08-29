"""Starter problem catalog: a Blind-75-style spread of Easy/Medium problems
covering every category in curriculum.py. Seeded once on first boot (only
if the problems table is empty) by fetching real data for each from
LeetCode's public API.
"""
from sqlmodel import Session, select

from app.leetcode_client import fetch_problem
from app.models import Problem

STARTER_SLUGS = [
    # Arrays & Hashing
    "two-sum",
    "contains-duplicate",
    "valid-anagram",
    # Two Pointers
    "valid-palindrome",
    "two-sum-ii-input-array-is-sorted",
    # Sliding Window
    "best-time-to-buy-and-sell-stock",
    "longest-substring-without-repeating-characters",
    # Stack
    "valid-parentheses",
    # Binary Search
    "binary-search",
    "search-in-rotated-sorted-array",
    # Linked List
    "reverse-linked-list",
    "merge-two-sorted-lists",
    "linked-list-cycle",
    # Trees
    "invert-binary-tree",
    "maximum-depth-of-binary-tree",
    "same-tree",
    # Heap / Priority Queue
    "kth-largest-element-in-an-array",
    # Backtracking
    "subsets",
    "combination-sum",
    # Graphs
    "number-of-islands",
    "clone-graph",
    # Dynamic Programming
    "climbing-stairs",
    "house-robber",
    "coin-change",
    # Greedy
    "maximum-subarray",
    # Intervals
    "merge-intervals",
    # Trie
    "implement-trie-prefix-tree",
]


def seed_catalog(session: Session) -> None:
    if session.exec(select(Problem)).first() is not None:
        return  # already has problems, don't touch existing data

    print(f"Seeding starter catalog ({len(STARTER_SLUGS)} problems)...")
    for slug in STARTER_SLUGS:
        url = f"https://leetcode.com/problems/{slug}/"
        try:
            data = fetch_problem(url)
        except Exception as e:
            print(f"  skip {slug}: {e}")
            continue
        if data:
            session.add(Problem(**data))
            print(f"  added {data['title']}")
        else:
            print(f"  skip {slug}: no data returned")
    session.commit()
    print("Catalog seed done.")
