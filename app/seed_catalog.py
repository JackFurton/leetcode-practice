"""Starter problem catalog: a Blind-75-style spread of Easy/Medium problems
covering every category in curriculum.py. Fully static, no network call, so
first boot is instant. Seeded once on first boot only (if the problems table
is empty) with title/difficulty/topic/notes/starter code/test cases baked in.

Notes are original short summaries, not copied from LeetCode's problem text.
Structure test cases (linked list / tree args or expected values) use the
wrapper convention documented in runner.py.
"""
import json

from sqlmodel import Session, select

from app.models import Problem, TestCase

# each entry: (title, url, difficulty, topic, notes, starter_code, test_cases)
# test_cases: list of (args_list, expected_value)
CATALOG = [
    (
        "1. Two Sum",
        "https://leetcode.com/problems/two-sum/",
        "Easy",
        "Array, Hash Table",
        "Given an array of integers and a target, return the indices of the two numbers "
        "that add up to target. Exactly one valid answer exists, don't reuse an element.",
        "def solve(nums, target):\n    pass",
        [
            ([[2, 7, 11, 15], 9], [0, 1]),
            ([[3, 2, 4], 6], [1, 2]),
        ],
    ),
    (
        "217. Contains Duplicate",
        "https://leetcode.com/problems/contains-duplicate/",
        "Easy",
        "Array, Hash Table",
        "Return True if any value appears at least twice in the array, False if every "
        "element is distinct.",
        "def solve(nums):\n    pass",
        [
            ([[1, 2, 3, 1]], True),
            ([[1, 2, 3, 4]], False),
        ],
    ),
    (
        "242. Valid Anagram",
        "https://leetcode.com/problems/valid-anagram/",
        "Easy",
        "String, Hash Table",
        "Given two strings s and t, return True if t is an anagram of s (same letters, "
        "same counts, any order).",
        "def solve(s, t):\n    pass",
        [
            (["anagram", "nagaram"], True),
            (["rat", "car"], False),
        ],
    ),
    (
        "125. Valid Palindrome",
        "https://leetcode.com/problems/valid-palindrome/",
        "Easy",
        "String, Two Pointers",
        "Given a string, ignore non-alphanumeric characters and case, and return True if "
        "what's left reads the same forwards and backwards.",
        "def solve(s):\n    pass",
        [
            (["A man, a plan, a canal: Panama"], True),
            (["race a car"], False),
        ],
    ),
    (
        "167. Two Sum II - Input Array Is Sorted",
        "https://leetcode.com/problems/two-sum-ii-input-array-is-sorted/",
        "Medium",
        "Array, Two Pointers",
        "Same as Two Sum, but the array is sorted ascending and the answer should be "
        "1-indexed positions (not 0-indexed). Solve it in O(1) extra space.",
        "def solve(numbers, target):\n    pass",
        [
            ([[2, 7, 11, 15], 9], [1, 2]),
            ([[2, 3, 4], 6], [1, 3]),
        ],
    ),
    (
        "121. Best Time to Buy and Sell Stock",
        "https://leetcode.com/problems/best-time-to-buy-and-sell-stock/",
        "Easy",
        "Array, Sliding Window, DP",
        "prices[i] is the stock price on day i. Pick one day to buy and a later day to "
        "sell to maximize profit. Return 0 if no profit is possible.",
        "def solve(prices):\n    pass",
        [
            ([[7, 1, 5, 3, 6, 4]], 5),
            ([[7, 6, 4, 3, 1]], 0),
        ],
    ),
    (
        "3. Longest Substring Without Repeating Characters",
        "https://leetcode.com/problems/longest-substring-without-repeating-characters/",
        "Medium",
        "String, Sliding Window, Hash Table",
        "Return the length of the longest substring of s that has no repeated characters.",
        "def solve(s):\n    pass",
        [
            (["abcabcbb"], 3),
            (["bbbbb"], 1),
            (["pwwkew"], 3),
        ],
    ),
    (
        "20. Valid Parentheses",
        "https://leetcode.com/problems/valid-parentheses/",
        "Easy",
        "String, Stack",
        "Given a string of just '()[]{}' characters, return True if every bracket is "
        "closed by the matching type in the correct order.",
        "def solve(s):\n    pass",
        [
            (["()[]{}"], True),
            (["(]"], False),
        ],
    ),
    (
        "704. Binary Search",
        "https://leetcode.com/problems/binary-search/",
        "Easy",
        "Array, Binary Search",
        "Given a sorted array of distinct integers and a target, return its index, or -1 "
        "if not present. Must run in O(log n).",
        "def solve(nums, target):\n    pass",
        [
            ([[-1, 0, 3, 5, 9, 12], 9], 4),
            ([[-1, 0, 3, 5, 9, 12], 2], -1),
        ],
    ),
    (
        "33. Search in Rotated Sorted Array",
        "https://leetcode.com/problems/search-in-rotated-sorted-array/",
        "Medium",
        "Array, Binary Search",
        "An ascending array was rotated at some unknown pivot. Given the rotated array and "
        "a target, return its index in O(log n), or -1 if absent.",
        "def solve(nums, target):\n    pass",
        [
            ([[4, 5, 6, 7, 0, 1, 2], 0], 4),
            ([[4, 5, 6, 7, 0, 1, 2], 3], -1),
        ],
    ),
    (
        "206. Reverse Linked List",
        "https://leetcode.com/problems/reverse-linked-list/",
        "Easy",
        "Linked List",
        "Reverse a singly linked list and return the new head.",
        "def solve(head):\n    pass",
        [
            (
                [{"type": "linked_list", "value": [1, 2, 3, 4, 5]}],
                {"type": "linked_list", "value": [5, 4, 3, 2, 1]},
            ),
            (
                [{"type": "linked_list", "value": [1, 2]}],
                {"type": "linked_list", "value": [2, 1]},
            ),
        ],
    ),
    (
        "21. Merge Two Sorted Lists",
        "https://leetcode.com/problems/merge-two-sorted-lists/",
        "Easy",
        "Linked List",
        "Merge two sorted linked lists into one sorted linked list by splicing their nodes "
        "together, and return its head.",
        "def solve(list1, list2):\n    pass",
        [
            (
                [
                    {"type": "linked_list", "value": [1, 2, 4]},
                    {"type": "linked_list", "value": [1, 3, 4]},
                ],
                {"type": "linked_list", "value": [1, 1, 2, 3, 4, 4]},
            ),
            (
                [
                    {"type": "linked_list", "value": []},
                    {"type": "linked_list", "value": []},
                ],
                {"type": "linked_list", "value": []},
            ),
        ],
    ),
    (
        "141. Linked List Cycle",
        "https://leetcode.com/problems/linked-list-cycle/",
        "Easy",
        "Linked List, Two Pointers",
        "Return True if the linked list has a cycle in it (some node's next eventually "
        "points back to a previous node), False otherwise. Do it in O(1) space.",
        "def solve(head):\n    pass",
        [
            ([{"type": "linked_list_cycle", "value": {"vals": [3, 2, 0, -4], "pos": 1}}], True),
            ([{"type": "linked_list_cycle", "value": {"vals": [1], "pos": -1}}], False),
        ],
    ),
    (
        "226. Invert Binary Tree",
        "https://leetcode.com/problems/invert-binary-tree/",
        "Easy",
        "Tree, DFS, BFS",
        "Given the root of a binary tree, swap every left/right child pair (mirror the "
        "tree) and return the new root.",
        "def solve(root):\n    pass",
        [
            (
                [{"type": "tree", "value": [4, 2, 7, 1, 3, 6, 9]}],
                {"type": "tree", "value": [4, 7, 2, 9, 6, 3, 1]},
            ),
            (
                [{"type": "tree", "value": []}],
                {"type": "tree", "value": []},
            ),
        ],
    ),
    (
        "104. Maximum Depth of Binary Tree",
        "https://leetcode.com/problems/maximum-depth-of-binary-tree/",
        "Easy",
        "Tree, DFS, BFS",
        "Return the number of nodes along the longest path from root to a leaf.",
        "def solve(root):\n    pass",
        [
            ([{"type": "tree", "value": [3, 9, 20, None, None, 15, 7]}], 3),
            ([{"type": "tree", "value": []}], 0),
        ],
    ),
    (
        "100. Same Tree",
        "https://leetcode.com/problems/same-tree/",
        "Easy",
        "Tree, DFS",
        "Given the roots of two binary trees, return True if they are structurally "
        "identical with the same node values.",
        "def solve(p, q):\n    pass",
        [
            ([{"type": "tree", "value": [1, 2, 3]}, {"type": "tree", "value": [1, 2, 3]}], True),
            ([{"type": "tree", "value": [1, 2]}, {"type": "tree", "value": [1, None, 2]}], False),
        ],
    ),
    (
        "215. Kth Largest Element in an Array",
        "https://leetcode.com/problems/kth-largest-element-in-an-array/",
        "Medium",
        "Array, Heap, Sorting",
        "Return the kth largest element in the array (kth largest in sorted order, not "
        "the kth distinct value).",
        "def solve(nums, k):\n    pass",
        [
            ([[3, 2, 1, 5, 6, 4], 2], 5),
            ([[3, 2, 3, 1, 2, 4, 5, 5, 6], 4], 4),
        ],
    ),
    (
        "78. Subsets",
        "https://leetcode.com/problems/subsets/",
        "Medium",
        "Array, Backtracking",
        "Given an array of unique integers, return every possible subset (the power set). "
        "Any order of subsets, and any order within a subset, is accepted.",
        "def solve(nums):\n    pass",
        [
            (
                [[1, 2, 3]],
                {
                    "type": "list_of_lists_unordered",
                    "value": [[], [1], [2], [3], [1, 2], [1, 3], [2, 3], [1, 2, 3]],
                },
            ),
            ([[0]], {"type": "list_of_lists_unordered", "value": [[], [0]]}),
        ],
    ),
    (
        "39. Combination Sum",
        "https://leetcode.com/problems/combination-sum/",
        "Medium",
        "Array, Backtracking",
        "Given distinct candidates and a target, return all unique combinations (numbers "
        "can repeat) that sum to target. Order of combinations/elements doesn't matter.",
        "def solve(candidates, target):\n    pass",
        [
            (
                [[2, 3, 6, 7], 7],
                {"type": "list_of_lists_unordered", "value": [[2, 2, 3], [7]]},
            ),
            (
                [[2, 3, 5], 8],
                {"type": "list_of_lists_unordered", "value": [[2, 2, 2, 2], [2, 3, 3], [3, 5]]},
            ),
        ],
    ),
    (
        "200. Number of Islands",
        "https://leetcode.com/problems/number-of-islands/",
        "Medium",
        "Array, Graph, BFS, DFS",
        "grid is a 2D array of '1' (land) and '0' (water). Return the number of islands "
        "(connected groups of land, horizontally/vertically adjacent).",
        "def solve(grid):\n    pass",
        [
            (
                [[["1", "1", "0", "0", "0"], ["1", "1", "0", "0", "0"],
                  ["0", "0", "1", "0", "0"], ["0", "0", "0", "1", "1"]]],
                3,
            ),
        ],
    ),
    (
        "133. Clone Graph",
        "https://leetcode.com/problems/clone-graph/",
        "Medium",
        "Graph, DFS, BFS, Hash Table",
        "Given a reference node in a connected undirected graph (each node has a val and a "
        "list of neighbors), return a deep copy of the whole graph. No auto-graded test "
        "cases for this one, graph structures don't serialize cleanly to JSON, verify by "
        "hand or on leetcode.com directly.",
        "class Node:\n    def __init__(self, val=0, neighbors=None):\n        self.val = val\n        self.neighbors = neighbors or []\n\n\ndef solve(node):\n    pass",
        [],
    ),
    (
        "70. Climbing Stairs",
        "https://leetcode.com/problems/climbing-stairs/",
        "Easy",
        "DP, Math",
        "You can climb 1 or 2 steps at a time. Given n steps total, return how many "
        "distinct ways there are to reach the top.",
        "def solve(n):\n    pass",
        [
            ([2], 2),
            ([3], 3),
        ],
    ),
    (
        "198. House Robber",
        "https://leetcode.com/problems/house-robber/",
        "Medium",
        "Array, DP",
        "Each house has nums[i] money. You can't rob two adjacent houses. Return the max "
        "total you can rob.",
        "def solve(nums):\n    pass",
        [
            ([[1, 2, 3, 1]], 4),
            ([[2, 7, 9, 3, 1]], 12),
        ],
    ),
    (
        "322. Coin Change",
        "https://leetcode.com/problems/coin-change/",
        "Medium",
        "Array, DP",
        "Given coin denominations and a target amount, return the fewest coins needed to "
        "make that amount (unlimited supply of each coin), or -1 if impossible.",
        "def solve(coins, amount):\n    pass",
        [
            ([[1, 2, 5], 11], 3),
            ([[2], 3], -1),
        ],
    ),
    (
        "53. Maximum Subarray",
        "https://leetcode.com/problems/maximum-subarray/",
        "Medium",
        "Array, DP, Greedy",
        "Return the largest possible sum of a contiguous, non-empty subarray.",
        "def solve(nums):\n    pass",
        [
            ([[-2, 1, -3, 4, -1, 2, 1, -5, 4]], 6),
            ([[1]], 1),
        ],
    ),
    (
        "56. Merge Intervals",
        "https://leetcode.com/problems/merge-intervals/",
        "Medium",
        "Array, Sorting, Intervals",
        "Given a list of intervals, merge every pair that overlaps and return the merged "
        "list sorted by start.",
        "def solve(intervals):\n    pass",
        [
            ([[[1, 3], [2, 6], [8, 10], [15, 18]]], [[1, 6], [8, 10], [15, 18]]),
        ],
    ),
    (
        "208. Implement Trie (Prefix Tree)",
        "https://leetcode.com/problems/implement-trie-prefix-tree/",
        "Medium",
        "Design, Trie, Hash Table",
        "Implement a Trie class with insert(word), search(word) (exact match), and "
        "startsWith(prefix) methods. This is a class-design problem, not a single function, "
        "so no auto-graded test cases here, exercise the class methods manually.",
        "class Trie:\n    def __init__(self):\n        pass\n\n    def insert(self, word):\n        pass\n\n    def search(self, word):\n        pass\n\n    def startsWith(self, prefix):\n        pass",
        [],
    ),
]


def seed_catalog(session: Session) -> None:
    if session.exec(select(Problem)).first() is not None:
        return  # already has problems, don't touch existing data

    print(f"Seeding starter catalog ({len(CATALOG)} problems)...")
    for title, url, difficulty, topic, notes, starter_code, test_cases in CATALOG:
        problem = Problem(
            title=title,
            url=url,
            difficulty=difficulty,
            topic=topic,
            notes=notes,
            starter_code=starter_code,
        )
        session.add(problem)
        session.flush()  # assigns problem.id without a full commit
        for args, expected in test_cases:
            session.add(
                TestCase(
                    problem_id=problem.id,
                    input_json=json.dumps(args),
                    expected_json=json.dumps(expected),
                )
            )
    session.commit()
    print("Catalog seed done.")
