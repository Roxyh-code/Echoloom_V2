import type { Message, Profile } from "./api";
export type StoryCardData = {
  kind: "story_card";
  id: string;
  story_id: string | null;
  character_id: string | null;
  conversation_id: string;
  title: string;
  preview: string;
  character_name: string;
  status: StoryStatus | "deleted";
  last_error: string | null;
  timeline_order: number;
};
export type TimelineItem =
  (Message & { kind: "text"; timeline_order: number }) | StoryCardData;
export type StoryStatus =
  "ready" | "generating" | "active" | "awaiting_choice" | "completed";
export type StoryBlock = {
  id: string;
  type: "narration" | "dialogue" | "action";
  speaker: "player" | "character" | null;
  text: string;
  source: "ai" | "user";
};
export type StoryEnding = {
  type: "continue" | "decision" | "ending";
  id?: string;
  question?: string;
  options?: { id: string; intent: string }[];
  selected_option_id?: string;
  custom_input?: string;
};
export type StorySegment = {
  id: string;
  parent_segment_id: string | null;
  revision: number;
  input_event: Record<string, unknown>;
  blocks: StoryBlock[];
  ending: StoryEnding;
  summary: string;
  confirmed_facts: string[];
};
export type Story = {
  id: string;
  character_id: string;
  origin_conversation_id: string;
  event_id: string;
  title: string;
  character_snapshot: Profile;
  profile_version: number;
  portrait_id: string | null;
  player_name: string;
  setup: {
    description: string;
    relationship: string;
    atmosphere: string;
    constraints: string;
  };
  status: StoryStatus;
  last_error: string | null;
  retry_action?: StoryAction | null;
  revision: number;
  active_segment_id: string | null;
  progress: {
    segment_id: string | null;
    last_revealed_block_id: string | null;
  };
  segments: StorySegment[];
  can_undo: boolean;
};
export type StoryAction = {
  request_id: string;
  expected_revision: number;
  operation:
    "start" | "continue" | "decide" | "interject" | "rewrite" | "undo" | "end";
  decision_id?: string;
  option_id?: string;
  content?: string;
  input_type?: "dialogue" | "action" | "direction";
  revealed_block_id?: string | null;
  skip_generation?: boolean;
};
export type ActionResult = {
  story: Story;
  result: unknown;
  current_revision: number;
  replayed: boolean;
};
export const statusLabel: Record<StoryStatus | "deleted", string> = {
  ready: "Not started",
  generating: "Preparing",
  active: "In progress",
  awaiting_choice: "Waiting for your choice",
  completed: "Completed",
  deleted: "Deleted",
};
