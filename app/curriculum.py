"""Static topic checklist with pattern explanations, algo.monster-style:
what the pattern is, when to reach for it, and a bare-bones template.
Progress per topic is tracked in the TopicProgress table (see models.py).

Each category also lists a couple of catalog problems that exercise it
(`practice`, plain titles, matches Problem.title in seed_catalog.py), and a
handful of the more visual topics carry a small inline SVG (`diagram`) for
the web UI plus a plain-text equivalent (`diagram_ascii`) for the TUI."""

_TWO_POINTERS_ASCII = """\
  l                              r
[ 2] [ 5] [ 7] [11] [14] [20]
 ->                          <-"""

_SLIDING_WINDOW_ASCII = """\
[ 2] [ 5] [ 7] [11] [14] [20]
      \\___ window ___/
                slide ->"""

_BFS_TREE_ASCII = """\
          (1)
        /     \\
     (2)       (3)
     /  \\      /  \\
  (4)  (5)   (6)  (7)

level 1: (1)
level 2: (2) (3)
level 3: (4) (5) (6) (7)"""

_REVERSAL_ASCII = """\
before: (1) -> (2) -> (3) -> (4) -> (5)
after:  (5) -> (4) -> (3) -> (2) -> (1)"""

_TWO_POINTERS_SVG = """<svg viewBox="0 0 320 88" xmlns="http://www.w3.org/2000/svg">
<defs><marker id="tp-arrow" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto"><path d="M0,0 L6,3 L0,6 z" fill="currentColor"/></marker></defs>
<g font-family="ui-monospace,monospace" font-size="13" fill="currentColor">
<text x="30" y="14" text-anchor="middle">l</text><text x="280" y="14" text-anchor="middle">r</text>
</g>
<g stroke="currentColor" stroke-width="1.5" fill="none">
<rect x="10" y="22" width="40" height="32"/><rect x="60" y="22" width="40" height="32"/>
<rect x="110" y="22" width="40" height="32"/><rect x="160" y="22" width="40" height="32"/>
<rect x="210" y="22" width="40" height="32"/><rect x="260" y="22" width="40" height="32"/>
</g>
<g font-family="ui-monospace,monospace" font-size="13" fill="currentColor">
<text x="30" y="43" text-anchor="middle">2</text><text x="80" y="43" text-anchor="middle">5</text>
<text x="130" y="43" text-anchor="middle">7</text><text x="180" y="43" text-anchor="middle">11</text>
<text x="230" y="43" text-anchor="middle">14</text><text x="280" y="43" text-anchor="middle">20</text>
</g>
<g stroke="currentColor" stroke-width="1.5">
<line x1="18" y1="68" x2="42" y2="68" marker-end="url(#tp-arrow)"/>
<line x1="292" y1="68" x2="268" y2="68" marker-end="url(#tp-arrow)"/>
</g>
</svg>"""

_SLIDING_WINDOW_SVG = """<svg viewBox="0 0 320 90" xmlns="http://www.w3.org/2000/svg">
<defs><marker id="sw-arrow" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto"><path d="M0,0 L6,3 L0,6 z" fill="currentColor"/></marker></defs>
<g stroke="currentColor" stroke-width="1.5" fill="none">
<rect x="10" y="22" width="40" height="32"/><rect x="60" y="22" width="40" height="32"/>
<rect x="110" y="22" width="40" height="32"/><rect x="160" y="22" width="40" height="32"/>
<rect x="210" y="22" width="40" height="32"/><rect x="260" y="22" width="40" height="32"/>
</g>
<rect x="58" y="16" width="154" height="44" fill="none" stroke="currentColor" stroke-width="2" stroke-dasharray="4 3"/>
<g font-family="ui-monospace,monospace" font-size="12" fill="currentColor">
<text x="135" y="12" text-anchor="middle">window</text>
</g>
<g stroke="currentColor" stroke-width="1.5">
<line x1="225" y1="72" x2="255" y2="72" marker-end="url(#sw-arrow)"/>
</g>
<g font-family="ui-monospace,monospace" font-size="12" fill="currentColor">
<text x="190" y="84" text-anchor="middle">slide</text>
</g>
</svg>"""

_BFS_TREE_SVG = """<svg viewBox="0 0 260 130" xmlns="http://www.w3.org/2000/svg">
<g stroke="currentColor" stroke-width="1.5">
<line x1="130" y1="20" x2="70" y2="65"/><line x1="130" y1="20" x2="190" y2="65"/>
<line x1="70" y1="65" x2="40" y2="110"/><line x1="70" y1="65" x2="100" y2="110"/>
<line x1="190" y1="65" x2="160" y2="110"/><line x1="190" y1="65" x2="220" y2="110"/>
</g>
<line x1="0" y1="42" x2="260" y2="42" stroke="currentColor" stroke-width="1" stroke-dasharray="2 3" opacity="0.5"/>
<line x1="0" y1="87" x2="260" y2="87" stroke="currentColor" stroke-width="1" stroke-dasharray="2 3" opacity="0.5"/>
<g stroke="currentColor" stroke-width="1.5" fill="#000">
<circle cx="130" cy="20" r="13"/><circle cx="70" cy="65" r="13"/><circle cx="190" cy="65" r="13"/>
<circle cx="40" cy="110" r="13"/><circle cx="100" cy="110" r="13"/><circle cx="160" cy="110" r="13"/><circle cx="220" cy="110" r="13"/>
</g>
<g font-family="ui-monospace,monospace" font-size="12" fill="currentColor" text-anchor="middle">
<text x="130" y="24">1</text><text x="70" y="69">2</text><text x="190" y="69">3</text>
<text x="40" y="114">4</text><text x="100" y="114">5</text><text x="160" y="114">6</text><text x="220" y="114">7</text>
</g>
</svg>"""

_REVERSAL_SVG = """<svg viewBox="0 0 300 90" xmlns="http://www.w3.org/2000/svg">
<defs><marker id="rev-arrow" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto"><path d="M0,0 L6,3 L0,6 z" fill="currentColor"/></marker></defs>
<g font-family="ui-monospace,monospace" font-size="11" fill="currentColor"><text x="4" y="16">before</text></g>
<g stroke="currentColor" stroke-width="1.5" fill="none">
<rect x="10" y="22" width="36" height="26"/><rect x="70" y="22" width="36" height="26"/>
<rect x="130" y="22" width="36" height="26"/><rect x="190" y="22" width="36" height="26"/>
</g>
<g stroke="currentColor" stroke-width="1.5">
<line x1="46" y1="35" x2="68" y2="35" marker-end="url(#rev-arrow)"/>
<line x1="106" y1="35" x2="128" y2="35" marker-end="url(#rev-arrow)"/>
<line x1="166" y1="35" x2="188" y2="35" marker-end="url(#rev-arrow)"/>
</g>
<g font-family="ui-monospace,monospace" font-size="11" fill="currentColor"><text x="4" y="70">after</text></g>
<g stroke="currentColor" stroke-width="1.5" fill="none">
<rect x="10" y="60" width="36" height="26"/><rect x="70" y="60" width="36" height="26"/>
<rect x="130" y="60" width="36" height="26"/><rect x="190" y="60" width="36" height="26"/>
</g>
<g stroke="currentColor" stroke-width="1.5">
<line x1="68" y1="73" x2="46" y2="73" marker-end="url(#rev-arrow)"/>
<line x1="128" y1="73" x2="106" y2="73" marker-end="url(#rev-arrow)"/>
<line x1="188" y1="73" x2="166" y2="73" marker-end="url(#rev-arrow)"/>
</g>
</svg>"""

CURRICULUM = [
    {
        "category": "Arrays & Hashing",
        "practice": ["1. Two Sum", "217. Contains Duplicate", "242. Valid Anagram"],
        "topics": [
            {
                "name": "Arrays basics",
                "explanation": "Iterate, index, mutate in place. Most interview problems start here "
                "before layering on a pattern. Watch for off-by-one errors and whether you can "
                "solve it in one pass instead of two.",
                "template": "for i, val in enumerate(arr):\n    ...",
            },
            {
                "name": "Hash maps / sets",
                "explanation": "Trade space for O(1) average lookup. Reach for this whenever you "
                "catch yourself writing a nested loop just to check 'have I seen this value / "
                "does its complement exist'.",
                "template": "seen = {}\nfor i, val in enumerate(arr):\n    if target - val in seen:\n        return [seen[target - val], i]\n    seen[val] = i",
            },
            {
                "name": "Prefix sums",
                "explanation": "Precompute running totals so any range-sum query becomes O(1) "
                "instead of O(n). Good whenever a problem asks about sums over subarrays "
                "repeatedly.",
                "template": "prefix = [0] * (len(arr) + 1)\nfor i, val in enumerate(arr):\n    prefix[i + 1] = prefix[i] + val\n# sum(arr[l:r]) == prefix[r] - prefix[l]",
            },
        ],
    },
    {
        "category": "Two Pointers",
        "practice": ["125. Valid Palindrome", "167. Two Sum II - Input Array Is Sorted"],
        "topics": [
            {
                "name": "Two pointers on sorted array",
                "explanation": "One pointer from each end, move the one that's making the "
                "condition worse. Needs sorted (or sortable) input. O(n) instead of the O(n^2) "
                "brute force pair check.",
                "template": "l, r = 0, len(arr) - 1\nwhile l < r:\n    s = arr[l] + arr[r]\n    if s == target:\n        return [l, r]\n    elif s < target:\n        l += 1\n    else:\n        r -= 1",
                "diagram": _TWO_POINTERS_SVG,
                "diagram_ascii": _TWO_POINTERS_ASCII,
            },
            {
                "name": "Fast/slow pointers",
                "explanation": "One pointer moves 2x speed of the other. Classic use: cycle "
                "detection and finding the middle of a linked list in one pass.",
                "template": "slow = fast = head\nwhile fast and fast.next:\n    slow = slow.next\n    fast = fast.next.next\n    if slow == fast:\n        return True  # cycle",
            },
        ],
    },
    {
        "category": "Sliding Window",
        "practice": [
            "121. Best Time to Buy and Sell Stock",
            "3. Longest Substring Without Repeating Characters",
        ],
        "topics": [
            {
                "name": "Fixed size window",
                "explanation": "Window size k never changes. Slide it one step at a time, "
                "add the new element, remove the one that fell off, update your running "
                "answer in O(1) per step.",
                "template": "window_sum = sum(arr[:k])\nbest = window_sum\nfor i in range(k, len(arr)):\n    window_sum += arr[i] - arr[i - k]\n    best = max(best, window_sum)",
            },
            {
                "name": "Variable size window",
                "explanation": "Grow the right edge until the window is invalid, then shrink "
                "from the left until it's valid again. Right pointer only ever moves forward, "
                "so total work is O(n) even though it looks nested.",
                "template": "l = 0\nfor r in range(len(arr)):\n    # expand: include arr[r]\n    while <window invalid>:\n        # shrink: remove arr[l]\n        l += 1\n    best = max(best, r - l + 1)",
                "diagram": _SLIDING_WINDOW_SVG,
                "diagram_ascii": _SLIDING_WINDOW_ASCII,
            },
        ],
    },
    {
        "category": "Stack",
        "practice": ["20. Valid Parentheses"],
        "topics": [
            {
                "name": "Monotonic stack",
                "explanation": "Keep the stack increasing or decreasing by popping elements "
                "that violate the order before pushing. Good for 'next greater/smaller element' "
                "style problems in O(n) instead of O(n^2).",
                "template": "stack = []\nfor i, val in enumerate(arr):\n    while stack and arr[stack[-1]] < val:\n        j = stack.pop()\n        # arr[i] is the next greater element for arr[j]\n    stack.append(i)",
            },
            {
                "name": "Valid parentheses patterns",
                "explanation": "Push opening brackets, pop and check on closing brackets. Any "
                "nested/matching-pair problem (brackets, tags, nested structure validation) is "
                "this pattern in disguise.",
                "template": "stack = []\npairs = {')': '(', ']': '[', '}': '{'}\nfor ch in s:\n    if ch in pairs:\n        if not stack or stack.pop() != pairs[ch]:\n            return False\n    else:\n        stack.append(ch)\nreturn not stack",
            },
        ],
    },
    {
        "category": "Binary Search",
        "practice": ["704. Binary Search", "33. Search in Rotated Sorted Array"],
        "topics": [
            {
                "name": "Standard binary search",
                "explanation": "Halve the search space every step, O(log n). Needs the array "
                "sorted (or the search space monotonic in some way you can exploit).",
                "template": "lo, hi = 0, len(arr) - 1\nwhile lo <= hi:\n    mid = (lo + hi) // 2\n    if arr[mid] == target:\n        return mid\n    elif arr[mid] < target:\n        lo = mid + 1\n    else:\n        hi = mid - 1\nreturn -1",
            },
            {
                "name": "Binary search on answer",
                "explanation": "The array itself isn't sorted, but the answer space is monotonic "
                "('if X works, everything bigger/smaller than X also works'). Binary search over "
                "possible answers, checking feasibility each time.",
                "template": "lo, hi = min_possible, max_possible\nwhile lo < hi:\n    mid = (lo + hi) // 2\n    if feasible(mid):\n        hi = mid\n    else:\n        lo = mid + 1\nreturn lo",
            },
        ],
    },
    {
        "category": "Linked List",
        "practice": [
            "206. Reverse Linked List",
            "21. Merge Two Sorted Lists",
            "141. Linked List Cycle",
        ],
        "topics": [
            {
                "name": "Reversal",
                "explanation": "Walk the list once, flipping each node's `.next` to point "
                "backward. Track prev/curr/next explicitly, easy to lose a reference if you "
                "reorder the three lines.",
                "template": "prev = None\ncurr = head\nwhile curr:\n    nxt = curr.next\n    curr.next = prev\n    prev = curr\n    curr = nxt\nreturn prev",
                "diagram": _REVERSAL_SVG,
                "diagram_ascii": _REVERSAL_ASCII,
            },
            {
                "name": "Fast/slow cycle detection",
                "explanation": "See Two Pointers > Fast/slow pointers, same technique applied "
                "specifically to linked lists.",
                "template": "slow = fast = head\nwhile fast and fast.next:\n    slow, fast = slow.next, fast.next.next\n    if slow is fast:\n        return True",
            },
            {
                "name": "Merge lists",
                "explanation": "Use a dummy head node so you never special-case 'is this the "
                "first node'. Walk both lists, always attach the smaller current node.",
                "template": "dummy = ListNode()\ntail = dummy\nwhile l1 and l2:\n    if l1.val <= l2.val:\n        tail.next, l1 = l1, l1.next\n    else:\n        tail.next, l2 = l2, l2.next\n    tail = tail.next\ntail.next = l1 or l2\nreturn dummy.next",
            },
        ],
    },
    {
        "category": "Trees",
        "practice": [
            "226. Invert Binary Tree",
            "104. Maximum Depth of Binary Tree",
            "100. Same Tree",
        ],
        "topics": [
            {
                "name": "DFS traversal",
                "explanation": "Recurse into left, then right (or whatever order the problem "
                "needs). Most tree problems are 'do something at this node, then let the "
                "recursion handle the subtrees'.",
                "template": "def dfs(node):\n    if not node:\n        return\n    dfs(node.left)\n    dfs(node.right)",
            },
            {
                "name": "BFS traversal",
                "explanation": "Level-by-level using a queue. Reach for this whenever a problem "
                "explicitly mentions 'level' or you need shortest-path-in-unweighted-tree "
                "behavior.",
                "template": "from collections import deque\nq = deque([root])\nwhile q:\n    for _ in range(len(q)):\n        node = q.popleft()\n        if node.left: q.append(node.left)\n        if node.right: q.append(node.right)",
                "diagram": _BFS_TREE_SVG,
                "diagram_ascii": _BFS_TREE_ASCII,
            },
            {
                "name": "BST properties",
                "explanation": "Left subtree < node < right subtree, always. In-order traversal "
                "of a BST yields sorted values, that fact solves half the BST problems on its "
                "own.",
                "template": "def valid(node, low, high):\n    if not node:\n        return True\n    if not (low < node.val < high):\n        return False\n    return valid(node.left, low, node.val) and valid(node.right, node.val, high)",
            },
        ],
    },
    {
        "category": "Heap / Priority Queue",
        "practice": ["215. Kth Largest Element in an Array"],
        "topics": [
            {
                "name": "Top-K problems",
                "explanation": "Keep a heap of size k instead of sorting everything. "
                "O(n log k) beats O(n log n) when k is small relative to n.",
                "template": "import heapq\nheap = []\nfor val in arr:\n    heapq.heappush(heap, val)\n    if len(heap) > k:\n        heapq.heappop(heap)\n# heap[0] is the kth largest",
            },
            {
                "name": "Merge K sorted lists",
                "explanation": "Push the head of every list into a min-heap, pop the smallest, "
                "push its successor. O(n log k) where k is the number of lists.",
                "template": "import heapq\nheap = [(node.val, i, node) for i, node in enumerate(heads) if node]\nheapq.heapify(heap)\nwhile heap:\n    val, i, node = heapq.heappop(heap)\n    if node.next:\n        heapq.heappush(heap, (node.next.val, i, node.next))",
            },
        ],
    },
    {
        "category": "Backtracking",
        "practice": ["78. Subsets", "39. Combination Sum"],
        "topics": [
            {
                "name": "Subsets / permutations",
                "explanation": "Build a path, recurse, then undo the last choice before trying "
                "the next one ('choose, explore, un-choose'). Exponential by nature, the "
                "template stays the same regardless of what you're enumerating.",
                "template": "def backtrack(start, path):\n    result.append(path[:])\n    for i in range(start, len(nums)):\n        path.append(nums[i])\n        backtrack(i + 1, path)\n        path.pop()",
            },
            {
                "name": "Combination sum",
                "explanation": "Same backtracking skeleton, plus a running total and a prune "
                "condition (stop exploring once the total exceeds target).",
                "template": "def backtrack(start, path, total):\n    if total == target:\n        result.append(path[:])\n        return\n    if total > target:\n        return\n    for i in range(start, len(candidates)):\n        path.append(candidates[i])\n        backtrack(i, path, total + candidates[i])\n        path.pop()",
            },
        ],
    },
    {
        "category": "Graphs",
        "practice": ["200. Number of Islands", "133. Clone Graph"],
        "topics": [
            {
                "name": "BFS/DFS on graph",
                "explanation": "Same traversal ideas as trees, but you now need a `visited` "
                "set since graphs can have cycles. Grid problems (number of islands, etc.) are "
                "graphs in disguise, adjacent cells are edges.",
                "template": "visited = set()\ndef dfs(node):\n    if node in visited:\n        return\n    visited.add(node)\n    for neighbor in graph[node]:\n        dfs(neighbor)",
            },
            {
                "name": "Topological sort",
                "explanation": "Ordering of nodes so every edge points forward, only exists if "
                "the graph is a DAG (no cycles). Kahn's algorithm: repeatedly remove nodes with "
                "in-degree 0.",
                "template": "from collections import deque\nq = deque([n for n in nodes if indegree[n] == 0])\norder = []\nwhile q:\n    n = q.popleft()\n    order.append(n)\n    for neighbor in graph[n]:\n        indegree[neighbor] -= 1\n        if indegree[neighbor] == 0:\n            q.append(neighbor)",
            },
            {
                "name": "Union-Find",
                "explanation": "Track connected components efficiently with path compression "
                "and union by rank. Reach for this on 'are these two things connected / how "
                "many groups' problems where you'd otherwise re-run BFS repeatedly.",
                "template": "parent = list(range(n))\ndef find(x):\n    if parent[x] != x:\n        parent[x] = find(parent[x])\n    return parent[x]\ndef union(a, b):\n    parent[find(a)] = find(b)",
            },
        ],
    },
    {
        "category": "Dynamic Programming",
        "practice": ["70. Climbing Stairs", "198. House Robber", "322. Coin Change"],
        "topics": [
            {
                "name": "1D DP",
                "explanation": "State depends on a single index, answer at i built from answers "
                "at smaller indices. Find the recurrence first, coding it is the easy part.",
                "template": "dp = [0] * (n + 1)\ndp[0], dp[1] = base_case_0, base_case_1\nfor i in range(2, n + 1):\n    dp[i] = dp[i - 1] + dp[i - 2]  # example recurrence",
            },
            {
                "name": "2D DP",
                "explanation": "State needs two indices (two strings, a grid, an index plus a "
                "capacity). Same idea as 1D, just a table instead of an array. Many 2D DPs can "
                "be space-optimized down to two rolling rows.",
                "template": "dp = [[0] * (m + 1) for _ in range(n + 1)]\nfor i in range(1, n + 1):\n    for j in range(1, m + 1):\n        dp[i][j] = ...  # combine dp[i-1][j], dp[i][j-1], dp[i-1][j-1]",
            },
            {
                "name": "Knapsack pattern",
                "explanation": "Choose or skip each item under a capacity constraint. "
                "0/1 knapsack (each item once) vs unbounded (coin change: reuse items) is the "
                "key distinction, it changes the loop order.",
                "template": "dp = [float('inf')] * (amount + 1)\ndp[0] = 0\nfor coin in coins:\n    for a in range(coin, amount + 1):\n        dp[a] = min(dp[a], dp[a - coin] + 1)",
            },
        ],
    },
    {
        "category": "Greedy",
        "practice": ["53. Maximum Subarray"],
        "topics": [
            {
                "name": "Interval scheduling",
                "explanation": "Sort by end time, greedily take the interval that ends soonest "
                "whenever it doesn't conflict. Works because 'ends soonest' always leaves the "
                "most room for what's left, provably optimal for this problem shape.",
                "template": "intervals.sort(key=lambda x: x[1])\ncount, last_end = 0, float('-inf')\nfor s, e in intervals:\n    if s >= last_end:\n        count += 1\n        last_end = e",
            },
            {
                "name": "Greedy exchange argument",
                "explanation": "The general justification behind greedy solutions: show that "
                "any optimal solution can be transformed into the greedy one without making it "
                "worse. If you can't articulate why greedy is safe here, it probably isn't, "
                "reach for DP instead.",
                "template": "# no single template, the skill is proving greedy is safe, not writing the loop",
            },
        ],
    },
    {
        "category": "Intervals",
        "practice": ["56. Merge Intervals"],
        "topics": [
            {
                "name": "Merge intervals",
                "explanation": "Sort by start time, then walk through merging any interval that "
                "overlaps with the last one you kept.",
                "template": "intervals.sort(key=lambda x: x[0])\nmerged = [intervals[0]]\nfor s, e in intervals[1:]:\n    if s <= merged[-1][1]:\n        merged[-1][1] = max(merged[-1][1], e)\n    else:\n        merged.append([s, e])",
            },
            {
                "name": "Insert interval",
                "explanation": "Same merging idea, but you're threading one new interval into an "
                "already-sorted, already-non-overlapping list. Three phases: intervals fully "
                "before, the merge zone, intervals fully after.",
                "template": "# 1) append intervals ending before new starts\n# 2) merge all overlapping intervals into new\n# 3) append the rest",
            },
        ],
    },
    {
        "category": "Trie",
        "practice": ["208. Implement Trie (Prefix Tree)"],
        "topics": [
            {
                "name": "Prefix tree basics",
                "explanation": "Each node is a dict of children keyed by character, plus an "
                "'end of word' flag. O(word length) insert/search regardless of how many words "
                "are stored, the win over a plain set is prefix queries.",
                "template": "class TrieNode:\n    def __init__(self):\n        self.children = {}\n        self.is_word = False\n\ndef insert(root, word):\n    node = root\n    for ch in word:\n        node = node.children.setdefault(ch, TrieNode())\n    node.is_word = True",
            },
            {
                "name": "Word search II style",
                "explanation": "Build a trie of the target words, then DFS the grid, pruning "
                "any path whose prefix isn't in the trie. Turns an otherwise exponential search "
                "into something tractable.",
                "template": "def dfs(r, c, node, path):\n    ch = grid[r][c]\n    if ch not in node.children:\n        return\n    node = node.children[ch]\n    if node.is_word:\n        found.add(path + ch)\n    # explore neighbors with node, path + ch",
            },
        ],
    },
]

# title -> category name, derived from each category's practice list, used
# for the breadcrumb on problem pages ("Two Pointers > 125. Valid Palindrome").
CATEGORY_BY_TITLE = {
    title: category["category"] for category in CURRICULUM for title in category.get("practice", [])
}
