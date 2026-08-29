"""Runs a user's submitted Python code against test cases in a separate
subprocess (real isolation + hard timeout), and reports pass/fail per case.

Test case args/expected values are plain JSON (int, str, list, bool, ...) by
default. For problems whose real LeetCode signature takes/returns a linked
list or tree, an arg or expected value can instead be a wrapper dict:
  {"type": "linked_list", "value": [1, 2, 3]}
  {"type": "linked_list_cycle", "value": {"vals": [3, 2, 0, -4], "pos": 1}}
  {"type": "tree", "value": [4, 2, 7, 1, 3, 6, 9]}   # level-order, null = gap
  {"type": "list_of_lists_unordered", "value": [[1, 2], [3]]}  # order-independent
The harness converts wrapper args into real ListNode/TreeNode objects before
calling solve(), so your code reads exactly like a normal LeetCode solution.

Only for Python submissions right now. Not sandboxed against malicious code
(no seccomp/docker) -- fine for a local, single-user tool running code you
wrote yourself, but don't paste code you don't trust.
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

TIMEOUT_SECONDS = 5

HARNESS_HEADER = '''
import json, traceback

class ListNode:
    def __init__(self, val=0, next=None):
        self.val = val
        self.next = next

def _build_linked_list(vals):
    dummy = ListNode()
    cur = dummy
    for v in vals:
        cur.next = ListNode(v)
        cur = cur.next
    return dummy.next

def _build_linked_list_cycle(vals, pos):
    nodes = [ListNode(v) for v in vals]
    for i in range(len(nodes) - 1):
        nodes[i].next = nodes[i + 1]
    if pos >= 0 and nodes:
        nodes[-1].next = nodes[pos]
    return nodes[0] if nodes else None

def _linked_list_to_value(node, limit=10000):
    out = []
    seen = set()
    while node is not None and id(node) not in seen:
        seen.add(id(node))
        out.append(node.val)
        node = node.next
        if len(out) > limit:
            break
    return out

class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right

def _build_tree(vals):
    vals = list(vals)
    if not vals or vals[0] is None:
        return None
    it = iter(vals)
    root = TreeNode(next(it))
    queue = [root]
    while queue:
        node = queue.pop(0)
        try:
            v = next(it)
        except StopIteration:
            break
        if v is not None:
            node.left = TreeNode(v)
            queue.append(node.left)
        try:
            v = next(it)
        except StopIteration:
            break
        if v is not None:
            node.right = TreeNode(v)
            queue.append(node.right)
    return root

def _tree_to_value(root):
    if root is None:
        return []
    out = []
    queue = [root]
    while queue:
        node = queue.pop(0)
        if node is not None:
            out.append(node.val)
            queue.append(node.left)
            queue.append(node.right)
        else:
            out.append(None)
    while out and out[-1] is None:
        out.pop()
    return out

def _normalize_ll(ll):
    return sorted(tuple(sorted(inner)) for inner in ll)

def _convert_arg(a):
    if isinstance(a, dict) and set(a.keys()) == {"type", "value"}:
        t, v = a["type"], a["value"]
        if t == "linked_list":
            return _build_linked_list(v)
        if t == "linked_list_cycle":
            return _build_linked_list_cycle(v["vals"], v["pos"])
        if t == "tree":
            return _build_tree(v)
    return a

def _normalize_for_compare(value, expected_wrapper):
    if isinstance(expected_wrapper, dict) and set(expected_wrapper.keys()) == {"type", "value"}:
        t = expected_wrapper["type"]
        target = expected_wrapper["value"]
        if t == "linked_list":
            return _linked_list_to_value(value), target
        if t == "tree":
            return _tree_to_value(value), target
        if t == "list_of_lists_unordered":
            return _normalize_ll(value), _normalize_ll(target)
        return value, target
    return value, expected_wrapper

'''

HARNESS_FOOTER = '''
_cases = json.loads(__CASES_JSON__)
_results = []
for _raw_args, _expected_wrapper in _cases:
    entry = {"input": _raw_args}
    try:
        args = [_convert_arg(a) for a in _raw_args]
        actual = solve(*args)
        actual_norm, expected_norm = _normalize_for_compare(actual, _expected_wrapper)
        entry["actual"] = actual_norm
        entry["expected"] = expected_norm
        entry["passed"] = actual_norm == expected_norm
    except Exception as e:
        entry["actual"] = None
        entry["expected"] = (
            _expected_wrapper.get("value")
            if isinstance(_expected_wrapper, dict) and "value" in _expected_wrapper
            else _expected_wrapper
        )
        entry["passed"] = False
        entry["error"] = f"{type(e).__name__}: {e}"
    _results.append(entry)

print("__RESULTS_JSON__" + json.dumps(_results))
'''


def run_submission(code: str, test_cases: list[tuple[list, object]]) -> dict:
    """test_cases: list of (args_list, expected_value). Either may contain
    the structure wrapper dicts described in the module docstring.

    Returns {"ok": bool, "results": [...], "error": str | None}
    """
    cases_json = json.dumps(test_cases)
    footer = HARNESS_FOOTER.replace("__CASES_JSON__", repr(cases_json))
    script = HARNESS_HEADER + code + "\n" + footer

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, encoding="utf-8"
    ) as f:
        f.write(script)
        tmp_path = Path(f.name)

    try:
        proc = subprocess.run(
            [sys.executable, str(tmp_path)],
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "results": [], "error": f"Timed out after {TIMEOUT_SECONDS}s"}
    finally:
        tmp_path.unlink(missing_ok=True)

    marker = "__RESULTS_JSON__"
    if marker in proc.stdout:
        results = json.loads(proc.stdout.split(marker, 1)[1].strip())
        return {"ok": True, "results": results, "error": None}

    # code failed before printing results (syntax error, missing solve(), etc)
    return {"ok": False, "results": [], "error": proc.stderr.strip() or "Unknown error"}
