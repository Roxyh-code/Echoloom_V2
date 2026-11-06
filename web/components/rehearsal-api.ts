import type { Character } from "./api";
export type Actor = {
  slot?: number;
  id: string;
  source_character_id: string | null;
  name: string;
  avatar: string | null;
  description: string;
  profile: Record<string, unknown>;
  snapshot_revision: number;
};
export type Setup = {
  premise: string;
  goal: string;
  format: "prose" | "script";
  relation: string;
  location: string;
  time: string;
  knowledge_a: string;
  knowledge_b: string;
  rules: string[];
  language: "en" | "zh";
};
export const blankSetup: Setup = {
  premise: "",
  goal: "",
  format: "prose",
  relation: "",
  location: "",
  time: "",
  knowledge_a: "",
  knowledge_b: "",
  rules: [],
  language: "en",
};
export type Block = {
  id: string;
  type: "narration" | "action" | "dialogue";
  character_id: string | null;
  text: string;
  locked: boolean;
  user_edited: boolean;
  operation_id: string;
};
export type State = {
  knowledge: Record<string, string>;
  world_facts: Fact[];
  beliefs: Fact[];
  goals: Fact[];
  relationships: Fact[];
  threads: Fact[];
};
export type Fact = {
  text: string;
  known_by: string[];
  source_node: string;
  source_block: string;
};
export type Node = {
  id: string;
  parent: string | null;
  blocks: Block[];
  state: State;
  source: string;
  reason: string;
  operation_id: string;
  state_review?: boolean;
};
export type Version = {
  id: string;
  head: string | null;
  label: string;
  reason: string;
  parent_version: string | null;
  fork_node: string | null;
  setup: Setup;
  takeover: string | null;
  position: number;
  revealed?: number;
  instructions: { id: string; text: string; active: boolean }[];
};
export type Scene = {
  id: string;
  revision: number;
  updated_at: string;
  active_job?: string | null;
  source_updated?: boolean;
  document: {
    title: string;
    status: "draft" | "rehearsing" | "saved";
    demo: boolean;
    cast: Actor[];
    setup: Setup;
    initial_state: State;
    nodes: Record<string, Node>;
    versions: Record<string, Version>;
    active_version: string;
    result: null | {
      version_id: string;
      head: string;
      stamp: string;
      state: State;
    };
    source: null | {
      scene_id: string;
      version_id: string;
      head: string;
      title: string;
      stamp: string;
    };
    feedback: { node_id: string; correction: string }[];
  };
};
export type Job = {
  id: string;
  status: string;
  version_id: string;
  events: {
    sequence: number;
    type: string;
    block_id?: string;
    error?: string;
    ending?: boolean;
  }[];
  scene: Scene;
};
export type Choice = {
  id: string;
  title: string;
  choice: string;
  consequence: string;
};
export type Review = { summary: string; changes: string[]; threads: string[] };
export type Command = {
  kind: string;
  version_id?: string;
  node_id?: string;
  block_id?: string;
  target_id?: string;
  text?: string;
  name?: string;
  persistent?: boolean;
  edit_type?: string;
  input_type?: string;
  setup?: Setup;
  position?: number;
  revealed?: number;
  character_ids?: (string | null)[];
};
export { type Character };
export const operation = () => crypto.randomUUID();
export function chain(scene: Scene, head: string | null): Node[] {
  const nodes: Node[] = [];
  const seen = new Set<string>();
  while (head && scene.document.nodes[head] && !seen.has(head)) {
    seen.add(head);
    const n: Node = scene.document.nodes[head];
    nodes.unshift(n);
    head = n.parent;
  }
  return nodes;
}
export class RehearsalError extends Error {
  constructor(
    message: string,
    public status: number,
    public dependencies?: { id: string; title: string }[],
  ) {
    super(message);
  }
}
export async function rehearsal<T>(
  path: string,
  body?: unknown,
  method?: string,
): Promise<T> {
  const r = await fetch("/api/rehearsal" + path, {
    method: method || (body ? "POST" : "GET"),
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!r.ok) {
    if (r.status === 401)
      window.dispatchEvent(new Event("echoloom-auth-required"));
    const e = await r.json().catch(() => ({}));
    const detail = e.detail;
    throw new RehearsalError(
      typeof detail === "string"
        ? detail
        : detail?.message || "Please check your input and try again.",
      r.status,
      detail?.dependencies,
    );
  }
  return r.status === 204 ? (undefined as T) : r.json();
}
let cacheScope = "unverified";
export function scopeCache(owner: string) {
  cacheScope = encodeURIComponent(owner);
}
export function clearSceneCache(id: string) {
  try {
    for (const key of Object.keys(localStorage)) {
      if (key.startsWith("rh:" + cacheScope + ":") && key.includes(id))
        localStorage.removeItem(key);
    }
  } catch {}
}
export function localGet<T>(key: string, fallback: T): T {
  try {
    return (
      JSON.parse(
        localStorage.getItem("rh:" + cacheScope + ":" + key) || "null",
      ) ?? fallback
    );
  } catch {
    return fallback;
  }
}
export function localPut(key: string, value: unknown) {
  try {
    localStorage.setItem("rh:" + cacheScope + ":" + key, JSON.stringify(value));
    return true;
  } catch {
    return false;
  }
}
