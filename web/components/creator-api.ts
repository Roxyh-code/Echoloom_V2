import { api, Character, Profile } from "./api";
export type Block = {
  type: "narration" | "action" | "dialogue";
  speaker: string | null;
  text: string;
  source?: "ai" | "author" | "demo";
};
export type Member = {
  id: string;
  character_id: string | null;
  profile: Profile & {
    wants: string;
    why_it_matters: string;
    fear: string;
    private_information: string;
  };
  version: number;
  portrait_id: string | null;
  portrait_url: string | null;
};
export type Moment = {
  id: string;
  parent: string | null;
  scene_id: string;
  cast_id: string;
  instruction: string;
  blocks: Block[];
  suggestions: string[];
  source: "ai" | "demo" | "author";
};
export type Line = {
  finished?: boolean;
  world_rules?: string;
  id: string;
  name: string;
  head: string | null;
  cast_id: string;
  origin: string;
  revealed: number;
};
export type Fact = {
  id: string;
  line_id: string;
  source: string | null;
  text: string;
  known_by: string[];
  status: "confirmed" | "suggested" | "needs_review";
};
export type Checkpoint = {
  id: string;
  name: string;
  line: Line;
  created_at: string;
  facts: Fact[];
};
export type Document = {
  schema_version: 1;
  title: string;
  premise: string;
  mode: "play" | "direct";
  demo: boolean;
  archived: boolean;
  finished: boolean;
  active_line: string;
  casts: Record<string, Member[]>;
  scenes: Record<string, { id: string; title: string; premise: string }>;
  nodes: Record<string, Moment>;
  lines: Record<string, Line>;
  checkpoints: Checkpoint[];
  facts: Fact[];
};
export type Work = {
  id: string;
  revision: number;
  document: Document;
  updated_at: string;
};
export type CreatorCharacter = Character & { archived: boolean };
export function chain(doc: Document, head: string | null): Moment[] {
  const a: Moment[] = [];
  const seen = new Set<string>();
  while (head) {
    if (seen.has(head) || !doc.nodes[head])
      throw new Error("Invalid storyline.");
    seen.add(head);
    const n = doc.nodes[head];
    a.unshift(n);
    head = n.parent;
  }
  return a;
}
export async function creator<T>(
  path: string,
  body?: unknown,
  method?: string,
) {
  return api<T>("/creator" + path, body, method);
}
export function download(text: string, name: string, type = "text/plain") {
  const url = URL.createObjectURL(new Blob([text], { type }));
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  document.body.append(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 30000);
}
