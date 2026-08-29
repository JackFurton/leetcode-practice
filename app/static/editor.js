// Lightweight indentation-aware behavior for the code textarea: Tab/Shift+Tab
// indent/dedent, Enter continues the current line's indent and adds one more
// level after a line that opens a block. Rules are keyed by data-lang on the
// textarea (only "python" for now, add more entries as languages are added).
(function () {
  const INDENT = "    ";

  const RULES = {
    python: {
      opensBlock: (line) => /:\s*$/.test(line.trimEnd()),
    },
    default: {
      opensBlock: () => false,
    },
  };

  function currentLineStart(value, pos) {
    return value.lastIndexOf("\n", pos - 1) + 1;
  }

  function handleTab(e, textarea) {
    e.preventDefault();
    const { value } = textarea;
    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;

    if (start === end && !e.shiftKey) {
      textarea.setRangeText(INDENT, start, end, "end");
      return;
    }

    const lineStart = currentLineStart(value, start);
    let lineEnd = value.indexOf("\n", end);
    if (lineEnd === -1) lineEnd = value.length;
    const lines = value.slice(lineStart, lineEnd).split("\n");

    let firstLineDelta = 0;
    let totalDelta = 0;
    const newLines = lines.map((line, i) => {
      if (e.shiftKey) {
        const removed = line.match(/^ {1,4}/);
        if (!removed) return line;
        if (i === 0) firstLineDelta -= removed[0].length;
        totalDelta -= removed[0].length;
        return line.slice(removed[0].length);
      }
      if (i === 0) firstLineDelta += INDENT.length;
      totalDelta += INDENT.length;
      return INDENT + line;
    });

    textarea.setRangeText(newLines.join("\n"), lineStart, lineEnd, "preserve");
    textarea.selectionStart = Math.max(lineStart, start + firstLineDelta);
    textarea.selectionEnd = end + totalDelta;
  }

  function handleEnter(e, textarea, rules) {
    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    if (start !== end) return; // let the browser replace the selection normally

    const { value } = textarea;
    const lineStart = currentLineStart(value, start);
    const currentLine = value.slice(lineStart, start);
    const leading = (currentLine.match(/^[ \t]*/) || [""])[0];
    const indent = rules.opensBlock(currentLine) ? leading + INDENT : leading;

    e.preventDefault();
    const insertion = "\n" + indent;
    textarea.setRangeText(insertion, start, end, "end");
  }

  function init(textarea) {
    const rules = RULES[textarea.dataset.lang] || RULES.default;
    textarea.addEventListener("keydown", (e) => {
      if (e.key === "Tab") handleTab(e, textarea);
      else if (e.key === "Enter") handleEnter(e, textarea, rules);
    });
  }

  document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll(".code-editor").forEach(init);
  });
})();
