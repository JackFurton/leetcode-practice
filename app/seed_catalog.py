"""Starter problem catalog: a Blind-75-style spread of Easy/Medium problems
covering every category in curriculum.py. Fully static, no network call, so
first boot is instant. Seeded once on first boot only (if the problems table
is empty) with title/difficulty/topic/notes/starter code/test cases baked in.

Notes are original short summaries, not copied from LeetCode's problem text.
Structure test cases (linked list / tree args or expected values) use the
wrapper convention documented in runner.py.
"""
import json
import re

from sqlmodel import Session, select

from app.models import Problem, TestCase

_TOP_LEVEL_DEF = re.compile(r"^def (\w+)\(", re.MULTILINE)


def _extract_function_name(starter_code: str) -> str | None:
    """Pulls the name of the top-level function out of a starter_code
    snippet (None for class-design problems like Trie, which have no
    top-level function to call)."""
    m = _TOP_LEVEL_DEF.search(starter_code)
    return m.group(1) if m else None


# LeetCode-style constraints, one bullet per problem title, own wording/values.
CONSTRAINTS_BY_TITLE = {
    "1. Two Sum": [
        "2 <= nums.length <= 10^4",
        "-10^9 <= nums[i] <= 10^9",
        "-10^9 <= target <= 10^9",
        "Exactly one valid answer exists",
    ],
    "217. Contains Duplicate": [
        "1 <= nums.length <= 10^5",
        "-10^9 <= nums[i] <= 10^9",
    ],
    "242. Valid Anagram": [
        "1 <= s.length, t.length <= 5 * 10^4",
        "s and t consist of lowercase English letters",
    ],
    "125. Valid Palindrome": [
        "1 <= s.length <= 2 * 10^5",
        "s consists only of printable ASCII characters",
    ],
    "167. Two Sum II - Input Array Is Sorted": [
        "2 <= numbers.length <= 3 * 10^4",
        "-1000 <= numbers[i] <= 1000",
        "numbers is sorted in non-decreasing order",
        "Exactly one valid answer exists",
    ],
    "121. Best Time to Buy and Sell Stock": [
        "1 <= prices.length <= 10^5",
        "0 <= prices[i] <= 10^4",
    ],
    "3. Longest Substring Without Repeating Characters": [
        "0 <= s.length <= 5 * 10^4",
        "s consists of English letters, digits, symbols, and spaces",
    ],
    "20. Valid Parentheses": [
        "1 <= s.length <= 10^4",
        "s consists only of the characters '()[]{}'",
    ],
    "704. Binary Search": [
        "1 <= nums.length <= 10^4",
        "-10^4 < nums[i], target < 10^4",
        "nums is sorted ascending with all distinct values",
    ],
    "33. Search in Rotated Sorted Array": [
        "1 <= nums.length <= 5000",
        "-10^4 <= nums[i] <= 10^4",
        "All values in nums are unique",
        "nums was originally sorted ascending, then rotated at an unknown pivot",
    ],
    "206. Reverse Linked List": [
        "Number of nodes: 0 to 5000",
        "-5000 <= Node.val <= 5000",
    ],
    "21. Merge Two Sorted Lists": [
        "Number of nodes in both lists combined: 0 to 50",
        "-100 <= Node.val <= 100",
        "Both list1 and list2 are sorted in non-decreasing order",
    ],
    "141. Linked List Cycle": [
        "Number of nodes: 0 to 10^4",
        "-10^5 <= Node.val <= 10^5",
    ],
    "226. Invert Binary Tree": [
        "Number of nodes: 0 to 100",
        "-100 <= Node.val <= 100",
    ],
    "104. Maximum Depth of Binary Tree": [
        "Number of nodes: 0 to 10^4",
        "-100 <= Node.val <= 100",
    ],
    "100. Same Tree": [
        "Number of nodes in both trees: 0 to 100",
        "-10^4 <= Node.val <= 10^4",
    ],
    "215. Kth Largest Element in an Array": [
        "1 <= k <= nums.length <= 10^5",
        "-10^4 <= nums[i] <= 10^4",
    ],
    "78. Subsets": [
        "1 <= nums.length <= 10",
        "-10 <= nums[i] <= 10",
        "All elements of nums are unique",
    ],
    "39. Combination Sum": [
        "1 <= candidates.length <= 30",
        "2 <= candidates[i] <= 40",
        "All elements of candidates are unique",
        "1 <= target <= 40",
    ],
    "200. Number of Islands": [
        "1 <= grid.length, grid[i].length <= 300",
        "grid[i][j] is '0' or '1'",
    ],
    "133. Clone Graph": [
        "Number of nodes: 0 to 100",
        "1 <= Node.val <= 100",
        "No repeated edges, no self-loops",
    ],
    "70. Climbing Stairs": [
        "1 <= n <= 45",
    ],
    "198. House Robber": [
        "1 <= nums.length <= 100",
        "0 <= nums[i] <= 400",
    ],
    "322. Coin Change": [
        "1 <= coins.length <= 12",
        "1 <= coins[i] <= 2^31 - 1",
        "0 <= amount <= 10^4",
    ],
    "53. Maximum Subarray": [
        "1 <= nums.length <= 10^5",
        "-10^4 <= nums[i] <= 10^4",
    ],
    "56. Merge Intervals": [
        "1 <= intervals.length <= 10^4",
        "intervals[i].length == 2",
        "0 <= start <= end <= 10^4",
    ],
    "208. Implement Trie (Prefix Tree)": [
        "1 <= word.length, prefix.length <= 2000",
        "word and prefix consist of lowercase English letters",
        "At most 3 * 10^4 total calls to insert/search/startsWith",
    ],
}

# Pre-baked reference solutions for the catalog's gradable problems, generated
# offline and verified against the real seeded test cases (see the repo's test
# suite), not Claude-generated. Reveal Solution serves these directly for these
# 25 problems, zero API calls, zero cost, works with no key configured at all.
# Anything not listed here (Clone Graph, Trie, or a problem you add yourself)
# falls back to generating one live via Claude on first reveal.
REFERENCE_SOLUTIONS_BY_TITLE = {
    '1. Two Sum': (
        "**Approach**: Track values you've already seen in a hash map as you scan once. For each number, check whether its complement (target - num) was seen already.\n\n**Solution**:\n```python\ndef two_sum(nums, target):\n    seen = {}\n    for i, n in enumerate(nums):\n        if target - n in seen:\n            return [seen[target - n], i]\n        seen[n] = i\n    return []\n```\n\n**Complexity**: Time O(n), space O(n): one pass, O(1) average hash map lookups.\n\n**Why this works**: The complement check only ever looks at previously-seen indices, so you never reuse the same element twice, and you never need a second loop."
    ),
    '217. Contains Duplicate': (
        "**Approach**: A set collapses duplicates. If converting to a set shrinks the length, something repeated.\n\n**Solution**:\n```python\ndef contains_duplicate(nums):\n    return len(nums) != len(set(nums))\n```\n\n**Complexity**: Time O(n), space O(n): building the set is one pass.\n\n**Why this works**: len(set(nums)) is exactly the count of distinct values, so comparing it to len(nums) directly answers 'was anything repeated'."
    ),
    '242. Valid Anagram': (
        '**Approach**: Two strings are anagrams exactly when they contain the same multiset of characters, and sorting normalizes that.\n\n**Solution**:\n```python\ndef valid_anagram(s, t):\n    return sorted(s) == sorted(t)\n```\n\n**Complexity**: Time O(n log n), space O(n) for the sorted copies. A Counter-based approach gets this to O(n) if you need it.\n\n**Why this works**: Sorting is a canonical form for a multiset of characters: two strings have identical letter counts if and only if their sorted forms match.'
    ),
    '125. Valid Palindrome': (
        "**Approach**: Strip everything that isn't alphanumeric, lowercase what's left, and compare it to its reverse.\n\n**Solution**:\n```python\ndef valid_palindrome(s):\n    filtered = [c.lower() for c in s if c.isalnum()]\n    return filtered == filtered[::-1]\n```\n\n**Complexity**: Time O(n), space O(n) for the filtered copy.\n\n**Why this works**: A palindrome reads the same forwards and backwards by definition, filtering first makes punctuation/case irrelevant to that comparison."
    ),
    '167. Two Sum II - Input Array Is Sorted': (
        "**Approach**: Sorted input means two pointers from each end: if the sum's too big, move the right pointer in; too small, move the left pointer out.\n\n**Solution**:\n```python\ndef two_sum_ii(numbers, target):\n    l, r = 0, len(numbers) - 1\n    while l < r:\n        s = numbers[l] + numbers[r]\n        if s == target:\n            return [l + 1, r + 1]\n        elif s < target:\n            l += 1\n        else:\n            r -= 1\n    return []\n```\n\n**Complexity**: Time O(n), space O(1): each pointer moves at most n times total.\n\n**Why this works**: Because the array is sorted, moving the low pointer only increases the sum and moving the high pointer only decreases it, so every step is safe and no valid pair is ever skipped."
    ),
    '121. Best Time to Buy and Sell Stock': (
        "**Approach**: Track the lowest price seen so far, and at each day check the profit if you sold today.\n\n**Solution**:\n```python\ndef max_profit(prices):\n    min_price = float('inf')\n    best = 0\n    for p in prices:\n        min_price = min(min_price, p)\n        best = max(best, p - min_price)\n    return best\n```\n\n**Complexity**: Time O(n), space O(1): single pass.\n\n**Why this works**: The best sell day for a fixed buy day is irrelevant, what matters is the lowest price seen before today, so tracking a running minimum is enough."
    ),
    '3. Longest Substring Without Repeating Characters': (
        "**Approach**: Variable sliding window: expand right, and whenever a repeat shows up inside the window, shrink from the left past the previous occurrence.\n\n**Solution**:\n```python\ndef length_of_longest_substring(s):\n    seen = {}\n    best = 0\n    left = 0\n    for right, ch in enumerate(s):\n        if ch in seen and seen[ch] >= left:\n            left = seen[ch] + 1\n        seen[ch] = right\n        best = max(best, right - left + 1)\n    return best\n```\n\n**Complexity**: Time O(n), space O(min(n, charset)): left only ever moves forward.\n\n**Why this works**: seen[ch] >= left guarantees the previous occurrence is actually inside the current window before jumping left past it, otherwise you'd wrongly shrink the window because of a character outside it."
    ),
    '20. Valid Parentheses': (
        "**Approach**: Push opening brackets, and on a closing bracket check it matches whatever is on top of the stack.\n\n**Solution**:\n```python\ndef is_valid(s):\n    stack = []\n    pairs = {')': '(', ']': '[', '}': '{'}\n    for ch in s:\n        if ch in pairs:\n            if not stack or stack.pop() != pairs[ch]:\n                return False\n        else:\n            stack.append(ch)\n    return not stack\n```\n\n**Complexity**: Time O(n), space O(n) worst case (all openers).\n\n**Why this works**: A stack naturally models nesting, the most recently opened bracket must be the next one closed, which is exactly LIFO order."
    ),
    '704. Binary Search': (
        '**Approach**: Classic binary search: halve the search space based on whether the middle is too small or too large.\n\n**Solution**:\n```python\ndef binary_search(nums, target):\n    lo, hi = 0, len(nums) - 1\n    while lo <= hi:\n        mid = (lo + hi) // 2\n        if nums[mid] == target:\n            return mid\n        elif nums[mid] < target:\n            lo = mid + 1\n        else:\n            hi = mid - 1\n    return -1\n```\n\n**Complexity**: Time O(log n), space O(1).\n\n**Why this works**: Sorted input means everything left of a too-small mid is also too small (and symmetrically on the right), so an entire half can be discarded every step.'
    ),
    '33. Search in Rotated Sorted Array': (
        '**Approach**: At least one half of the array (split at mid) is always properly sorted. Check which half that is, then decide if target falls in it.\n\n**Solution**:\n```python\ndef search(nums, target):\n    lo, hi = 0, len(nums) - 1\n    while lo <= hi:\n        mid = (lo + hi) // 2\n        if nums[mid] == target:\n            return mid\n        if nums[lo] <= nums[mid]:\n            if nums[lo] <= target < nums[mid]:\n                hi = mid - 1\n            else:\n                lo = mid + 1\n        else:\n            if nums[mid] < target <= nums[hi]:\n                lo = mid + 1\n            else:\n                hi = mid - 1\n    return -1\n```\n\n**Complexity**: Time O(log n), space O(1).\n\n**Why this works**: A single rotation point means one side of any split is always a normal sorted run, so you can always tell which half to keep searching.'
    ),
    '206. Reverse Linked List': (
        "**Approach**: Walk the list once, flipping each node's next pointer to point backward.\n\n**Solution**:\n```python\ndef reverse_list(head):\n    prev = None\n    curr = head\n    while curr:\n        nxt = curr.next\n        curr.next = prev\n        prev = curr\n        curr = nxt\n    return prev\n```\n\n**Complexity**: Time O(n), space O(1).\n\n**Why this works**: Saving next before overwriting curr.next is what keeps the walk from losing the rest of the list once a pointer gets flipped."
    ),
    '21. Merge Two Sorted Lists': (
        "**Approach**: A dummy head node avoids special-casing 'is this the first node', then just always attach whichever current node is smaller.\n\n**Solution**:\n```python\ndef merge_two_lists(list1, list2):\n    dummy = ListNode()\n    tail = dummy\n    while list1 and list2:\n        if list1.val <= list2.val:\n            tail.next, list1 = list1, list1.next\n        else:\n            tail.next, list2 = list2, list2.next\n        tail = tail.next\n    tail.next = list1 or list2\n    return dummy.next\n```\n\n**Complexity**: Time O(n + m), space O(1) extra (reuses existing nodes).\n\n**Why this works**: Both inputs are already sorted, so the smallest unattached node between the two lists is always a safe next pick for the merged result."
    ),
    '141. Linked List Cycle': (
        "**Approach**: Two pointers, one moving twice as fast. If there's a cycle they must eventually land on the same node.\n\n**Solution**:\n```python\ndef has_cycle(head):\n    slow = fast = head\n    while fast and fast.next:\n        slow = slow.next\n        fast = fast.next.next\n        if slow is fast:\n            return True\n    return False\n```\n\n**Complexity**: Time O(n), space O(1).\n\n**Why this works**: Inside a cycle the gap between slow and fast shrinks by one every step, so they're guaranteed to meet; if there's no cycle, fast simply hits the end first."
    ),
    '226. Invert Binary Tree': (
        "**Approach**: Recursively swap every node's left and right children.\n\n**Solution**:\n```python\ndef invert_tree(root):\n    if not root:\n        return None\n    root.left, root.right = invert_tree(root.right), invert_tree(root.left)\n    return root\n```\n\n**Complexity**: Time O(n), space O(h) for the recursion stack (h = tree height).\n\n**Why this works**: Inverting a tree is exactly 'invert both subtrees, then swap which side they're attached to', which is what the recursive swap does bottom-up."
    ),
    '104. Maximum Depth of Binary Tree': (
        "**Approach**: The depth of a tree is 1 plus the deeper of its two subtrees' depths.\n\n**Solution**:\n```python\ndef max_depth(root):\n    if not root:\n        return 0\n    return 1 + max(max_depth(root.left), max_depth(root.right))\n```\n\n**Complexity**: Time O(n), space O(h) for the recursion stack.\n\n**Why this works**: Every node contributes exactly one level, so the longest root-to-leaf path is naturally the max of the two subtrees' depths plus one."
    ),
    '100. Same Tree': (
        "**Approach**: Two trees are the same if their roots match and both subtree pairs are also the same, recursively.\n\n**Solution**:\n```python\ndef is_same_tree(p, q):\n    if not p and not q:\n        return True\n    if not p or not q or p.val != q.val:\n        return False\n    return is_same_tree(p.left, q.left) and is_same_tree(p.right, q.right)\n```\n\n**Complexity**: Time O(n), space O(h) for the recursion stack.\n\n**Why this works**: Structural equality of a tree decomposes cleanly into 'roots equal' plus 'left subtrees equal' plus 'right subtrees equal'."
    ),
    '215. Kth Largest Element in an Array': (
        '**Approach**: Keep a min-heap capped at size k, the smallest element in it is the kth largest overall.\n\n**Solution**:\n```python\ndef find_kth_largest(nums, k):\n    import heapq\n    heap = []\n    for n in nums:\n        heapq.heappush(heap, n)\n        if len(heap) > k:\n            heapq.heappop(heap)\n    return heap[0]\n```\n\n**Complexity**: Time O(n log k), space O(k), better than full O(n log n) sorting when k is small.\n\n**Why this works**: Popping the minimum whenever the heap grows past k guarantees the heap always holds exactly the k largest values seen, and heap[0] is the smallest of those, i.e. the kth largest overall.'
    ),
    '78. Subsets': (
        '**Approach**: Backtracking: at each step either the current path is a valid subset (always, actually), then try including each remaining element in turn.\n\n**Solution**:\n```python\ndef subsets(nums):\n    result = []\n    path = []\n    def backtrack(start):\n        result.append(path[:])\n        for i in range(start, len(nums)):\n            path.append(nums[i])\n            backtrack(i + 1)\n            path.pop()\n    backtrack(0)\n    return result\n```\n\n**Complexity**: Time/space O(n * 2^n): there are 2^n subsets, each up to length n.\n\n**Why this works**: Recording path at the top of every call captures every prefix reached during the search, and only ever moving start forward ensures each subset is generated exactly once.'
    ),
    '39. Combination Sum': (
        '**Approach**: Same backtracking shape as subsets, but track a running total and stop early once it exceeds target. Reusing the same index (not i+1) allows repeats.\n\n**Solution**:\n```python\ndef combination_sum(candidates, target):\n    result = []\n    path = []\n    def backtrack(start, total):\n        if total == target:\n            result.append(path[:])\n            return\n        if total > target:\n            return\n        for i in range(start, len(candidates)):\n            path.append(candidates[i])\n            backtrack(i, total + candidates[i])\n            path.pop()\n    backtrack(0, 0)\n    return result\n```\n\n**Complexity**: Time is exponential in the worst case, bounded by target/min(candidates) levels of recursion.\n\n**Why this works**: Passing i (not i+1) into the recursive call is what allows the same number to be picked again, and the total > target check prunes branches that can never reach target.'
    ),
    '200. Number of Islands': (
        "**Approach**: DFS/flood-fill from every unvisited land cell, marking everything reachable as visited; each flood-fill is one island.\n\n**Solution**:\n```python\ndef num_islands(grid):\n    if not grid:\n        return 0\n    rows, cols = len(grid), len(grid[0])\n    visited = set()\n    def dfs(r, c):\n        if (r < 0 or r >= rows or c < 0 or c >= cols\n                or grid[r][c] == '0' or (r, c) in visited):\n            return\n        visited.add((r, c))\n        dfs(r + 1, c); dfs(r - 1, c); dfs(r, c + 1); dfs(r, c - 1)\n    count = 0\n    for r in range(rows):\n        for c in range(cols):\n            if grid[r][c] == '1' and (r, c) not in visited:\n                dfs(r, c)\n                count += 1\n    return count\n```\n\n**Complexity**: Time O(rows * cols), space O(rows * cols) for the visited set (and recursion stack).\n\n**Why this works**: Every land cell reachable from a given starting cell belongs to the same island by definition, so one DFS per unvisited land cell finds exactly one island each."
    ),
    '70. Climbing Stairs': (
        '**Approach**: The number of ways to reach step n is the ways to reach n-1 plus the ways to reach n-2 (your last move was either a 1-step or a 2-step).\n\n**Solution**:\n```python\ndef climb_stairs(n):\n    if n <= 2:\n        return n\n    a, b = 1, 2\n    for _ in range(3, n + 1):\n        a, b = b, a + b\n    return b\n```\n\n**Complexity**: Time O(n), space O(1): this is Fibonacci with two rolling variables instead of an array.\n\n**Why this works**: Any way to reach step n arrives via step n-1 or step n-2, and those two cases are disjoint and exhaustive, which is exactly the Fibonacci recurrence.'
    ),
    '198. House Robber': (
        "**Approach**: At each house, decide: skip it (keep previous best) or rob it (best from two houses back plus this house's money).\n\n**Solution**:\n```python\ndef rob(nums):\n    prev, curr = 0, 0\n    for n in nums:\n        prev, curr = curr, max(curr, prev + n)\n    return curr\n```\n\n**Complexity**: Time O(n), space O(1): two rolling variables instead of a dp array.\n\n**Why this works**: curr always holds the best total using houses seen so far; either you skip the new house (curr stays) or rob it (prev, which excludes the adjacent house, plus n), and the recurrence takes the better of the two."
    ),
    '322. Coin Change': (
        "**Approach**: Bottom-up DP: dp[a] is the fewest coins to make amount a, built from smaller amounts by trying every coin.\n\n**Solution**:\n```python\ndef coin_change(coins, amount):\n    dp = [0] + [float('inf')] * amount\n    for a in range(1, amount + 1):\n        for c in coins:\n            if c <= a:\n                dp[a] = min(dp[a], dp[a - c] + 1)\n    return dp[amount] if dp[amount] != float('inf') else -1\n```\n\n**Complexity**: Time O(amount * len(coins)), space O(amount).\n\n**Why this works**: Any optimal way to make amount a used some coin c last, leaving amount a-c to make optimally, so dp[a] is the best over all choices of that last coin."
    ),
    '53. Maximum Subarray': (
        "**Approach**: Kadane's algorithm: extend the current subarray if it's still helping, otherwise start fresh from the current element.\n\n**Solution**:\n```python\ndef max_subarray(nums):\n    best = curr = nums[0]\n    for n in nums[1:]:\n        curr = max(n, curr + n)\n        best = max(best, curr)\n    return best\n```\n\n**Complexity**: Time O(n), space O(1).\n\n**Why this works**: A negative running sum can only drag down any subarray that includes it, so once curr goes negative it's never worth carrying forward, restarting from the current element is always at least as good."
    ),
    '56. Merge Intervals': (
        "**Approach**: Sort by start time, then walk through merging any interval that overlaps with the last one kept.\n\n**Solution**:\n```python\ndef merge(intervals):\n    intervals.sort(key=lambda x: x[0])\n    merged = [intervals[0]]\n    for s, e in intervals[1:]:\n        if s <= merged[-1][1]:\n            merged[-1][1] = max(merged[-1][1], e)\n        else:\n            merged.append([s, e])\n    return merged\n```\n\n**Complexity**: Time O(n log n) for the sort, O(n) for the merge pass.\n\n**Why this works**: Once sorted by start, two intervals can only possibly overlap if they're adjacent in that order, so a single linear pass catches every merge."
    ),
}

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
        "def two_sum(nums, target):\n    # WRITE YOUR BRILLIANT CODE HERE\n    pass",
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
        "def contains_duplicate(nums):\n    # WRITE YOUR BRILLIANT CODE HERE\n    pass",
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
        "def valid_anagram(s, t):\n    # WRITE YOUR BRILLIANT CODE HERE\n    pass",
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
        "def valid_palindrome(s):\n    # WRITE YOUR BRILLIANT CODE HERE\n    pass",
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
        "def two_sum_ii(numbers, target):\n    # WRITE YOUR BRILLIANT CODE HERE\n    pass",
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
        "def max_profit(prices):\n    # WRITE YOUR BRILLIANT CODE HERE\n    pass",
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
        "def length_of_longest_substring(s):\n    # WRITE YOUR BRILLIANT CODE HERE\n    pass",
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
        "def is_valid(s):\n    # WRITE YOUR BRILLIANT CODE HERE\n    pass",
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
        "def binary_search(nums, target):\n    # WRITE YOUR BRILLIANT CODE HERE\n    pass",
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
        "def search(nums, target):\n    # WRITE YOUR BRILLIANT CODE HERE\n    pass",
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
        "def reverse_list(head):\n    # WRITE YOUR BRILLIANT CODE HERE\n    pass",
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
        "def merge_two_lists(list1, list2):\n    # WRITE YOUR BRILLIANT CODE HERE\n    pass",
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
        "def has_cycle(head):\n    # WRITE YOUR BRILLIANT CODE HERE\n    pass",
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
        "def invert_tree(root):\n    # WRITE YOUR BRILLIANT CODE HERE\n    pass",
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
        "def max_depth(root):\n    # WRITE YOUR BRILLIANT CODE HERE\n    pass",
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
        "def is_same_tree(p, q):\n    # WRITE YOUR BRILLIANT CODE HERE\n    pass",
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
        "def find_kth_largest(nums, k):\n    # WRITE YOUR BRILLIANT CODE HERE\n    pass",
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
        "def subsets(nums):\n    # WRITE YOUR BRILLIANT CODE HERE\n    pass",
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
        "def combination_sum(candidates, target):\n    # WRITE YOUR BRILLIANT CODE HERE\n    pass",
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
        "def num_islands(grid):\n    # WRITE YOUR BRILLIANT CODE HERE\n    pass",
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
        "class Node:\n    def __init__(self, val=0, neighbors=None):\n        self.val = val\n        self.neighbors = neighbors or []\n\n\ndef clone_graph(node):\n    # WRITE YOUR BRILLIANT CODE HERE\n    pass",
        [],
    ),
    (
        "70. Climbing Stairs",
        "https://leetcode.com/problems/climbing-stairs/",
        "Easy",
        "DP, Math",
        "You can climb 1 or 2 steps at a time. Given n steps total, return how many "
        "distinct ways there are to reach the top.",
        "def climb_stairs(n):\n    # WRITE YOUR BRILLIANT CODE HERE\n    pass",
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
        "def rob(nums):\n    # WRITE YOUR BRILLIANT CODE HERE\n    pass",
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
        "def coin_change(coins, amount):\n    # WRITE YOUR BRILLIANT CODE HERE\n    pass",
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
        "def max_subarray(nums):\n    # WRITE YOUR BRILLIANT CODE HERE\n    pass",
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
        "def merge(intervals):\n    # WRITE YOUR BRILLIANT CODE HERE\n    pass",
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
        "class Trie:\n    def __init__(self):\n        # WRITE YOUR BRILLIANT CODE HERE\n        pass\n\n    def insert(self, word):\n        # WRITE YOUR BRILLIANT CODE HERE\n        pass\n\n    def search(self, word):\n        # WRITE YOUR BRILLIANT CODE HERE\n        pass\n\n    def startsWith(self, prefix):\n        # WRITE YOUR BRILLIANT CODE HERE\n        pass",
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
            constraints="\n".join(CONSTRAINTS_BY_TITLE.get(title, [])) or None,
            starter_code=starter_code,
            function_name=_extract_function_name(starter_code),
            cached_solution=REFERENCE_SOLUTIONS_BY_TITLE.get(title),
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
