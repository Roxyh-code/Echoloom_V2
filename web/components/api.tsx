export type Profile = {
  wants: string;
  why_it_matters: string;
  fear: string;
  private_information: string;
  name: string;
  short_description: string;
  backstory: string;
  visual_style: string;
  appearance: Record<string, string>;
  personality: Record<string, string[]>;
  speech_style: { tone: string; vocabulary: string; speaking_habits: string[] };
  interaction_preferences: Record<string, string>;
};
export type Character = {
  id: string;
  profile: Profile;
  profile_version: number;
  current_image_id: string | null;
  conversation_id: string;
  original_description: string;
  created_at: string;
  updated_at: string;
};
export type Portrait = {
  id: string;
  version: number;
  parent_image_id: string | null;
  url: string;
  prompt: string;
  created_at: string;
};
export type Message = {
  source_type?: "user_chat" | "calendar_companion";
  id: string;
  role: "user" | "assistant";
  content: string;
  profile_version: number;
  request_id: string;
};
export type Proposal = {
  proposal_id: string;
  changes: {
    path: string;
    before: string | string[];
    after: string | string[];
  }[];
  explanation: string;
};
export type Revision = {
  version: number;
  change_summary: string;
  created_at: string;
  profile: Profile;
};
export type Health = {
  creator_database_ready?: boolean;
  text_configured: boolean;
  image_configured: boolean;
  max_profile_input_chars: number;
  database_ready: boolean;
};
export async function api<T>(
  path: string,
  body?: unknown,
  method?: string,
): Promise<T> {
  const response = await fetch(`/api${path}`, {
    method: method || (body === undefined ? "GET" : "POST"),
    headers: body === undefined ? {} : { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
    cache: "no-store",
  });
  if (!response.ok) {
    if (response.status === 401 && typeof window !== "undefined")
      window.dispatchEvent(new Event("echoloom-auth-required"));
    const data = await response.json().catch(() => null);
    const detail = data?.detail;
    throw new Error(
      typeof detail === "string"
        ? detail
        : Array.isArray(detail)
          ? "Invalid input. Check field values and length limits."
          : "The service is unavailable. Check that the backend is running, then retry.",
    );
  }
  return response.status === 204 ? (undefined as T) : response.json();
}
export function portraitUrl(character: Character) {
  return character.current_image_id
    ? `/api/characters/${character.id}/images/${character.current_image_id}/file`
    : null;
}
export function Avatar({
  character,
  large = false,
}: {
  character: Character;
  large?: boolean;
}) {
  const url = portraitUrl(character);
  return (
    <div className={`avatar ${large ? "large" : ""}`}>
      {url ? (
        <img src={url} alt={`Portrait of ${character.profile.name}`} />
      ) : (
        <span>{character.profile.name.slice(0, 1)}</span>
      )}
    </div>
  );
}
