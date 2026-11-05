"use client";
import { use } from "react";
import { StoryReader } from "@/components/story-reader";
export default function StoryPage({
  params,
}: {
  params: Promise<{ id: string; storyId: string }>;
}) {
  const { id, storyId } = use(params);
  return <StoryReader characterId={id} storyId={storyId} />;
}
