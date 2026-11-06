import type { Node } from "./rehearsal-api";
/** Lossless boundaries shared with rehearsal_domain.sentences. */
export function sentences(text: string): string[] {
  const chars = Array.from(text),
    units: string[] = [];
  let start = 0,
    i = 0;
  const endings = ".!?。！？",
    closers = "\"'”’)]』」";
  const abbreviations = [
    "Mr.",
    "Mrs.",
    "Ms.",
    "Dr.",
    "Prof.",
    "Sr.",
    "Jr.",
    "St.",
  ];
  while (i < chars.length) {
    const ch = chars[i];
    let end = i + 1,
      boundary = ch === "\n";
    if (endings.includes(ch)) {
      while (end < chars.length && (endings + closers).includes(chars[end]))
        end++;
      boundary =
        "。！？".includes(ch) || end === chars.length || /\s/u.test(chars[end]);
      const word =
        chars
          .slice(start, i + 1)
          .join("")
          .trim()
          .split(/\s+/u)
          .at(-1) || "";
      if (ch === "." && abbreviations.includes(word) && end < chars.length)
        boundary = false;
    }
    if (boundary) {
      while (end < chars.length && /\s/u.test(chars[end])) end++;
      const piece = chars.slice(start, end).join("");
      if (piece.trim()) units.push(piece);
      else if (units.length) units[units.length - 1] += piece;
      start = end;
      i = end;
    } else i++;
  }
  if (start < chars.length) {
    const rest = chars.slice(start).join("");
    if (rest.trim() || !units.length) units.push(rest);
    else units[units.length - 1] += rest;
  }
  return units;
}
export function countLines(nodes: Node[]): number {
  return nodes.reduce(
    (total, n) =>
      total + n.blocks.reduce((sum, b) => sum + sentences(b.text).length, 0),
    0,
  );
}
export function visibleLines(nodes: Node[], limit: number): Node[] {
  const result: Node[] = [];
  let remaining = limit;
  for (const node of nodes) {
    const blocks = [];
    for (const block of node.blocks) {
      if (remaining <= 0) break;
      const parts = sentences(block.text);
      blocks.push(
        remaining >= parts.length
          ? block
          : { ...block, text: parts.slice(0, remaining).join("").trimEnd() },
      );
      remaining -= Math.min(remaining, parts.length);
    }
    if (blocks.length) result.push({ ...node, blocks });
    if (remaining <= 0) break;
  }
  return result;
}

export function readState(
  nodes: Node[],
  limit: number,
  allNodeIds: Set<string>,
) {
  let remaining = limit;
  const completed = new Set<string>();
  let last: Node | undefined;
  for (const node of nodes) {
    let used = false;
    for (const b of node.blocks) {
      if (remaining <= 0) break;
      used = true;
      const size = sentences(b.text).length;
      if (remaining >= size) completed.add(b.id);
      remaining -= Math.min(remaining, size);
    }
    if (used) last = node;
    if (remaining <= 0) break;
  }
  if (!last) return undefined;
  const state = { ...last.state };
  for (const key of [
    "world_facts",
    "beliefs",
    "goals",
    "relationships",
    "threads",
  ] as const) {
    state[key] = state[key].filter(
      (f) => !allNodeIds.has(f.source_node) || completed.has(f.source_block),
    );
  }
  return state;
}
