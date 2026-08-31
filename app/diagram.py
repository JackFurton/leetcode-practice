"""Auto-generated per-problem SVG diagrams, built from a test case's own
input data (Example 1) rather than hand-drawn per problem -- an array
renders as boxes, a linked_list/tree wrapper (see runner.py's docstring for
the convention) renders as boxes-with-arrows or a real tree layout. Distinct
from curriculum.py's hand-authored *pattern*-level diagrams (two pointers,
sliding window, ...), which stay hand-drawn since they illustrate a
technique, not a specific problem's data.

Same "currentColor" + ui-monospace styling convention as curriculum.py's
SVGs so both pick up color from the wrapping `.diagram` CSS class.
"""
import json
from xml.sax.saxutils import escape as _xml_escape

BOX = 40


def _esc(v) -> str:
    return _xml_escape(str(v))


def _wrap(label: str, inner: str) -> str:
    return f'<div class="diagram"><div class="diagram-label">{_esc(label)}</div>{inner}</div>'


def _is_wrapper(v) -> bool:
    return isinstance(v, dict) and set(v.keys()) == {"type", "value"}


def _array_svg(values: list, label: str) -> str:
    n = len(values)
    step = BOX + 6
    width = n * step + 10
    height = 54
    rects, texts = [], []
    for i, v in enumerate(values):
        x = 5 + i * step
        rects.append(f'<rect x="{x}" y="10" width="{BOX}" height="32"/>')
        texts.append(f'<text x="{x + BOX / 2}" y="30" text-anchor="middle">{_esc(v)}</text>')
    svg = (
        f'<svg viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">'
        f'<g stroke="currentColor" stroke-width="1.5" fill="none">{"".join(rects)}</g>'
        f'<g font-family="ui-monospace,monospace" font-size="13" fill="currentColor">'
        f'{"".join(texts)}</g></svg>'
    )
    return _wrap(label, svg)


def _matrix_svg(rows: list, label: str) -> str:
    ncols = max((len(r) for r in rows), default=0)
    step = BOX + 6
    width = ncols * step + 10
    height = len(rows) * step + 10
    rects, texts = [], []
    for ri, row in enumerate(rows):
        for ci, v in enumerate(row):
            x = 5 + ci * step
            y = 5 + ri * step
            rects.append(f'<rect x="{x}" y="{y}" width="{BOX}" height="32"/>')
            texts.append(f'<text x="{x + BOX / 2}" y="{y + 20}" text-anchor="middle">{_esc(v)}</text>')
    svg = (
        f'<svg viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">'
        f'<g stroke="currentColor" stroke-width="1.5" fill="none">{"".join(rects)}</g>'
        f'<g font-family="ui-monospace,monospace" font-size="13" fill="currentColor">'
        f'{"".join(texts)}</g></svg>'
    )
    return _wrap(label, svg)


def _linked_list_svg(values: list, label: str, cycle_pos: int | None = None) -> str:
    n = len(values)
    if n == 0:
        return _wrap(label, '<div class="diagram-empty">empty list</div>')

    step = BOX + 24
    width = n * step + 40
    has_cycle = cycle_pos is not None and cycle_pos >= 0
    height = 100 if has_cycle else 60

    defs = (
        '<defs><marker id="ll-arrow" markerWidth="8" markerHeight="8" refX="6" refY="3" '
        'orient="auto"><path d="M0,0 L6,3 L0,6 z" fill="currentColor"/></marker></defs>'
    )
    rects, texts, arrows = [], [], []
    for i, v in enumerate(values):
        x = 10 + i * step
        rects.append(f'<rect x="{x}" y="14" width="{BOX}" height="32"/>')
        texts.append(f'<text x="{x + BOX / 2}" y="34" text-anchor="middle">{_esc(v)}</text>')
        if i < n - 1:
            arrows.append(
                f'<line x1="{x + BOX}" y1="30" x2="{x + step - 2}" y2="30" '
                f'marker-end="url(#ll-arrow)"/>'
            )

    end_x = 10 + (n - 1) * step + BOX
    if has_cycle:
        target_x = 10 + cycle_pos * step + BOX / 2
        arrows.append(
            f'<path d="M{end_x + 2},30 C{end_x + 40},70 {target_x},70 {target_x},46" '
            f'fill="none" marker-end="url(#ll-arrow)"/>'
        )
    else:
        texts.append(
            f'<text x="{end_x + 20}" y="34" text-anchor="middle" font-size="11" '
            f'fill="currentColor" opacity="0.6">None</text>'
        )

    svg = (
        f'<svg viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">{defs}'
        f'<g stroke="currentColor" stroke-width="1.5" fill="none">{"".join(rects)}</g>'
        f'<g stroke="currentColor" stroke-width="1.5">{"".join(arrows)}</g>'
        f'<g font-family="ui-monospace,monospace" font-size="13" fill="currentColor">'
        f'{"".join(texts)}</g></svg>'
    )
    return _wrap(label, svg)


def _build_tree_nodes(values: list):
    if not values or values[0] is None:
        return None
    it = iter(values)
    root = {"val": next(it), "left": None, "right": None}
    queue = [root]
    while queue:
        node = queue.pop(0)
        try:
            v = next(it)
        except StopIteration:
            break
        if v is not None:
            node["left"] = {"val": v, "left": None, "right": None}
            queue.append(node["left"])
        try:
            v = next(it)
        except StopIteration:
            break
        if v is not None:
            node["right"] = {"val": v, "left": None, "right": None}
            queue.append(node["right"])
    return root


def _tree_svg(values: list, label: str) -> str:
    root = _build_tree_nodes(values)
    if root is None:
        return _wrap(label, '<div class="diagram-empty">empty tree</div>')

    # in-order x-assignment gives a readable (if not perfectly compact) layout
    coords: dict[int, list[int]] = {}
    counter = [0]
    max_depth = [0]

    def assign(node, depth):
        if node is None:
            return
        assign(node["left"], depth + 1)
        coords[id(node)] = [counter[0], depth]
        counter[0] += 1
        max_depth[0] = max(max_depth[0], depth)
        assign(node["right"], depth + 1)

    assign(root, 0)

    step_x = BOX
    step_y = BOX + 24
    width = counter[0] * step_x + 20
    height = (max_depth[0] + 1) * step_y + 20

    def pos(node):
        x, y = coords[id(node)]
        return 10 + x * step_x + step_x / 2, 20 + y * step_y

    lines, circles, texts = [], [], []

    def emit(node):
        if node is None:
            return
        cx, cy = pos(node)
        if node["left"] is not None:
            lx, ly = pos(node["left"])
            lines.append(f'<line x1="{cx}" y1="{cy}" x2="{lx}" y2="{ly}"/>')
        if node["right"] is not None:
            rx, ry = pos(node["right"])
            lines.append(f'<line x1="{cx}" y1="{cy}" x2="{rx}" y2="{ry}"/>')
        circles.append(f'<circle cx="{cx}" cy="{cy}" r="15"/>')
        texts.append(f'<text x="{cx}" y="{cy + 4}" text-anchor="middle">{_esc(node["val"])}</text>')
        emit(node["left"])
        emit(node["right"])

    emit(root)

    svg = (
        f'<svg viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">'
        f'<g stroke="currentColor" stroke-width="1.5">{"".join(lines)}</g>'
        f'<g stroke="currentColor" stroke-width="1.5" fill="none">{"".join(circles)}</g>'
        f'<g font-family="ui-monospace,monospace" font-size="12" fill="currentColor">'
        f'{"".join(texts)}</g></svg>'
    )
    return _wrap(label, svg)


def _render_value(value, label: str) -> str | None:
    if _is_wrapper(value):
        t, v = value["type"], value["value"]
        if t == "linked_list":
            return _linked_list_svg(v, label)
        if t == "linked_list_cycle":
            return _linked_list_svg(v["vals"], label, cycle_pos=v["pos"])
        if t == "tree":
            return _tree_svg(v, label)
        return None  # list_of_lists_unordered etc: no useful positional diagram
    if isinstance(value, list) and value:
        if all(isinstance(x, list) for x in value):
            return _matrix_svg(value, label)
        if all(isinstance(x, (int, float, str, bool)) or x is None for x in value):
            return _array_svg(value, label)
    return None  # scalars (int/str/bool/None) or empty arrays: not worth a diagram


def diagram_for_test_case(input_json: str) -> str | None:
    """input_json: a TestCase.input_json string (a JSON list of positional
    args). Returns concatenated <div class="diagram">...</div> blocks for
    whichever args are structured enough to visualize, or None if none are."""
    args = json.loads(input_json)
    labels_needed = len(args) > 1
    parts = []
    for i, a in enumerate(args):
        svg = _render_value(a, label=f"arg {i + 1}" if labels_needed else "input")
        if svg:
            parts.append(svg)
    return "\n".join(parts) if parts else None
