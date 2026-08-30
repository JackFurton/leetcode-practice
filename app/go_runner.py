"""Runs a Go submission against real test cases, compiled and executed via
`go run` in a subprocess (real isolation, hard timeout, same idea as
runner.py's Python harness).

Go is statically typed, so unlike Python's `def solve(*args)` we can't just
json.loads the test cases and splat them in at runtime -- each problem needs
to declare its argument/return types (ProblemStarter.arg_types/return_type),
and the harness renders every test case as an actual typed Go literal at
generation time (e.g. JSON [2, 7, 11, 15] + type "[]int" -> the Go source
text "[]int{2, 7, 11, 15}").

Three special type strings trigger structure construction instead of literal
rendering, matching runner.py's wrapper convention (the test-case JSON is
the *same* wrapper dicts runner.py already documents, since these problems
share their TestCase rows with the Python harness):
  "linked_list"       {"type": "linked_list", "value": [1, 2, 3]}
  "linked_list_cycle" {"type": "linked_list_cycle", "value": {"vals": [...], "pos": N}}
  "tree"               {"type": "tree", "value": [4, 2, 7, None, ...]}  # null = gap
A ListNode/TreeNode struct pair plus build/serialize helpers are always
injected into the generated program (unused top-level funcs don't error in
Go, so it's simplest to include them unconditionally).
"""
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

TIMEOUT_SECONDS = 20  # go run compiles + runs; a bit more headroom than Python

STRUCT_HELPERS = '''
type ListNode struct {
	Val  int
	Next *ListNode
}

func intPtr(v int) *int { return &v }

func buildLinkedList(vals []int) *ListNode {
	dummy := &ListNode{}
	cur := dummy
	for _, v := range vals {
		cur.Next = &ListNode{Val: v}
		cur = cur.Next
	}
	return dummy.Next
}

func buildLinkedListCycle(vals []int, pos int) *ListNode {
	nodes := make([]*ListNode, len(vals))
	for i, v := range vals {
		nodes[i] = &ListNode{Val: v}
	}
	for i := 0; i < len(nodes)-1; i++ {
		nodes[i].Next = nodes[i+1]
	}
	if pos >= 0 && len(nodes) > 0 {
		nodes[len(nodes)-1].Next = nodes[pos]
	}
	if len(nodes) == 0 {
		return nil
	}
	return nodes[0]
}

func linkedListToValue(node *ListNode) []int {
	out := []int{}
	seen := map[*ListNode]bool{}
	for node != nil && !seen[node] {
		seen[node] = true
		out = append(out, node.Val)
		node = node.Next
	}
	return out
}

type TreeNode struct {
	Val   int
	Left  *TreeNode
	Right *TreeNode
}

func buildTree(vals []*int) *TreeNode {
	if len(vals) == 0 || vals[0] == nil {
		return nil
	}
	root := &TreeNode{Val: *vals[0]}
	queue := []*TreeNode{root}
	i := 1
	for len(queue) > 0 && i < len(vals) {
		node := queue[0]
		queue = queue[1:]
		if i < len(vals) {
			if vals[i] != nil {
				node.Left = &TreeNode{Val: *vals[i]}
				queue = append(queue, node.Left)
			}
			i++
		}
		if i < len(vals) {
			if vals[i] != nil {
				node.Right = &TreeNode{Val: *vals[i]}
				queue = append(queue, node.Right)
			}
			i++
		}
	}
	return root
}

func treeToValue(root *TreeNode) []*int {
	out := []*int{}
	if root == nil {
		return out
	}
	queue := []*TreeNode{root}
	for len(queue) > 0 {
		node := queue[0]
		queue = queue[1:]
		if node != nil {
			out = append(out, intPtr(node.Val))
			queue = append(queue, node.Left)
			queue = append(queue, node.Right)
		} else {
			out = append(out, nil)
		}
	}
	for len(out) > 0 && out[len(out)-1] == nil {
		out = out[:len(out)-1]
	}
	return out
}
'''

STRUCTURE_TYPES = {"linked_list", "linked_list_cycle", "tree"}


def go_default_starter_code(function_name: str) -> str:
    return f"func {function_name}() {{\n\t// WRITE YOUR BRILLIANT CODE HERE\n}}"


def is_unedited(code: str, starter_code: str) -> bool:
    return code.strip() == starter_code.strip()


def _go_literal(value, go_type: str) -> str:
    if go_type == "int":
        return str(value)
    if go_type == "bool":
        return "true" if value else "false"
    if go_type == "string":
        return json.dumps(value)
    if go_type.startswith("[]"):
        inner = go_type[2:]
        items = ", ".join(_go_literal(v, inner) for v in value)
        return f"{go_type}{{{items}}}"
    raise ValueError(f"unsupported Go type for literal rendering: {go_type!r}")


def _go_tree_literal(value) -> str:
    items = ["nil" if v is None else f"intPtr({v})" for v in value]
    return "[]*int{" + ", ".join(items) + "}"


def _render_arg(raw_value, go_type: str) -> str:
    """raw_value is a test-case arg, either a plain JSON value or one of the
    structure-wrapper dicts described in the module docstring, depending on
    go_type. Returns a Go expression to embed in the generated program."""
    if go_type == "linked_list":
        return f"buildLinkedList({_go_literal(raw_value['value'], '[]int')})"
    if go_type == "linked_list_cycle":
        vals = _go_literal(raw_value["value"]["vals"], "[]int")
        pos = _go_literal(raw_value["value"]["pos"], "int")
        return f"buildLinkedListCycle({vals}, {pos})"
    if go_type == "tree":
        return f"buildTree({_go_tree_literal(raw_value['value'])})"
    return _go_literal(raw_value, go_type)


def run_go_submission(
    code: str,
    test_cases: list[tuple[list, object]],
    function_name: str,
    arg_types: list[str],
    return_type: str,
) -> dict:
    """test_cases: list of (args_list, expected_value), same shape as
    runner.run_submission -- either may contain the structure-wrapper dicts
    described in the module docstring. Returns
    {"ok": bool, "results": [...], "error": str | None}."""
    if not shutil.which("go"):
        return {
            "ok": False,
            "results": [],
            "error": "Go toolchain not found. Install it from https://go.dev/dl/ "
            "and make sure `go` is on your PATH.",
        }

    if not function_name.isidentifier():
        raise ValueError(f"Invalid function_name: {function_name!r}")

    blocks = []
    for args, expected in test_cases:
        try:
            arg_literals = ", ".join(
                _render_arg(a, t) for a, t in zip(args, arg_types)
            )
            if return_type == "linked_list":
                expected_literal = _go_literal(expected["value"], "[]int")
                convert = "linkedListToValue"
            elif return_type == "tree":
                expected_literal = _go_tree_literal(expected["value"])
                convert = "treeToValue"
            else:
                expected_literal = _go_literal(expected, return_type)
                convert = None
        except (ValueError, TypeError, KeyError) as e:
            return {"ok": False, "results": [], "error": f"Bad test case data: {e}"}

        if convert:
            actual_expr = f"{convert}({function_name}({arg_literals}))"
        else:
            actual_expr = f"{function_name}({arg_literals})"

        blocks.append(
            "\t{\n"
            f"\t\tactual := {actual_expr}\n"
            f"\t\texpected := {expected_literal}\n"
            "\t\tresults = append(results, __result{"
            "Expected: expected, Actual: actual, Passed: reflect.DeepEqual(actual, expected)"
            "})\n"
            "\t}\n"
        )

    script = (
        "package main\n\n"
        'import (\n\t"encoding/json"\n\t"fmt"\n\t"reflect"\n)\n\n'
        f"{STRUCT_HELPERS}\n"
        f"{code}\n\n"
        "type __result struct {\n"
        '\tExpected interface{} `json:"expected"`\n'
        '\tActual   interface{} `json:"actual"`\n'
        '\tPassed   bool        `json:"passed"`\n'
        "}\n\n"
        "func main() {\n"
        "\tvar results []__result\n\n"
        + "".join(blocks)
        + '\n\tout, _ := json.Marshal(results)\n'
        '\tfmt.Println("__RESULTS_JSON__" + string(out))\n'
        "}\n"
    )

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".go", delete=False, encoding="utf-8"
    ) as f:
        f.write(script)
        tmp_path = Path(f.name)

    try:
        proc = subprocess.run(
            ["go", "run", str(tmp_path)],
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
        raw_results = json.loads(proc.stdout.split(marker, 1)[1].strip())
        results = []
        for (args, _expected), r in zip(test_cases, raw_results):
            results.append(
                {
                    "input": args,
                    "expected": r["expected"],
                    "actual": r["actual"],
                    "passed": r["passed"],
                }
            )
        return {"ok": True, "results": results, "error": None}

    # compile error or panic before the marker was printed
    return {"ok": False, "results": [], "error": proc.stderr.strip() or "Unknown error"}
