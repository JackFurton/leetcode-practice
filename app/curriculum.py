"""Static topic checklist, loosely mirrors an algo.monster-style pattern track.
Progress per topic is tracked in the TopicProgress table (see models.py)."""

CURRICULUM = [
    {
        "category": "Arrays & Hashing",
        "topics": ["Arrays basics", "Hash maps / sets", "Prefix sums"],
    },
    {
        "category": "Two Pointers",
        "topics": ["Two pointers on sorted array", "Fast/slow pointers"],
    },
    {
        "category": "Sliding Window",
        "topics": ["Fixed size window", "Variable size window"],
    },
    {
        "category": "Stack",
        "topics": ["Monotonic stack", "Valid parentheses patterns"],
    },
    {
        "category": "Binary Search",
        "topics": ["Standard binary search", "Binary search on answer"],
    },
    {
        "category": "Linked List",
        "topics": ["Reversal", "Fast/slow cycle detection", "Merge lists"],
    },
    {
        "category": "Trees",
        "topics": ["DFS traversal", "BFS traversal", "BST properties"],
    },
    {
        "category": "Heap / Priority Queue",
        "topics": ["Top-K problems", "Merge K sorted lists"],
    },
    {
        "category": "Backtracking",
        "topics": ["Subsets / permutations", "Combination sum"],
    },
    {
        "category": "Graphs",
        "topics": ["BFS/DFS on graph", "Topological sort", "Union-Find"],
    },
    {
        "category": "Dynamic Programming",
        "topics": ["1D DP", "2D DP", "Knapsack pattern"],
    },
    {
        "category": "Greedy",
        "topics": ["Interval scheduling", "Greedy exchange argument"],
    },
    {
        "category": "Intervals",
        "topics": ["Merge intervals", "Insert interval"],
    },
    {
        "category": "Trie",
        "topics": ["Prefix tree basics", "Word search II style"],
    },
]
