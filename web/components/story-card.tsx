import Link from "next/link";
import { statusLabel, StoryCardData } from "./story-api";
export function StoryCard({ card }: { card: StoryCardData }) {
  return (
    <article className="story-card" id={`story-event-${card.id}`}>
      <p className="eyebrow">
        ✧ AN ACTIVITY WITH {card.character_name || "YOUR CHARACTER"}
      </p>
      <h3>{card.title}</h3>
      <p className="story-preview">{card.preview}</p>
      <div className="story-card-footer">
        <span className="story-status">{statusLabel[card.status]}</span>
        {card.story_id && card.status !== "deleted" ? (
          <Link
            className="button"
            href={`/characters/${card.character_id}/stories/${card.story_id}`}
          >
            {card.status === "completed"
              ? "Revisit"
              : card.status === "ready"
                ? "Begin"
                : "Continue"}{" "}
            →
          </Link>
        ) : (
          <span className="muted small">This story was deleted.</span>
        )}
      </div>
      {card.last_error && (
        <p className="notice">
          Generation did not finish. Open the story to retry.
        </p>
      )}
    </article>
  );
}
