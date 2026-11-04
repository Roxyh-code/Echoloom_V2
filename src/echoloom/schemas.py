from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

Text = Annotated[str, StringConstraints(max_length=4000)]
Short = Annotated[str, StringConstraints(max_length=500)]
Items = Annotated[list[Short], Field(max_length=30)]


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Appearance(Model):
    age_description: Short = ""
    hair: Short = ""
    eyes: Short = ""
    clothing: Short = ""
    other_details: Short = ""


class Personality(Model):
    core_traits: Items = Field(default_factory=list)
    values: Items = Field(default_factory=list)
    motivations: Items = Field(default_factory=list)
    behavioral_patterns: Items = Field(default_factory=list)


class SpeechStyle(Model):
    tone: Short = ""
    vocabulary: Short = ""
    speaking_habits: Items = Field(default_factory=list)


class Interaction(Model):
    conversation_style: Short = ""
    relationship_context: Short = ""


class Profile(Model):
    name: str = Field(min_length=1, max_length=100)
    short_description: Short = ""
    appearance: Appearance = Field(default_factory=Appearance)
    personality: Personality = Field(default_factory=Personality)
    backstory: Text = ""
    speech_style: SpeechStyle = Field(default_factory=SpeechStyle)
    interaction_preferences: Interaction = Field(default_factory=Interaction)
    visual_style: Literal["Anime", "Cartoon", "Semi-realistic", "Realistic"] = "Anime"


class GenerateInput(Model):
    description: str = Field(min_length=1, max_length=20000)


class ProfileUpdate(Model):
    profile: Profile
    expected_version: int = Field(ge=1)


class RefineInput(Model):
    instruction: str = Field(min_length=1, max_length=2000)
    expected_version: int = Field(ge=1)


class ConfirmInput(Model):
    proposal_id: UUID


class RestoreInput(Model):
    version: int = Field(ge=1)
    expected_version: int = Field(ge=1)


class ChatInput(Model):
    content: str = Field(min_length=1, max_length=4000)
    request_id: UUID


class ImageInput(Model):
    instruction: str = Field(default="", max_length=2000)
    expected_image_id: UUID | None = None


# Only explicit leaf paths can be changed by the refinement model.
PATCH_PATHS = {
    "name",
    "short_description",
    "backstory",
    "visual_style",
    *(f"appearance.{key}" for key in Appearance.model_fields),
    *(f"personality.{key}" for key in Personality.model_fields),
    *(f"speech_style.{key}" for key in SpeechStyle.model_fields),
    *(f"interaction_preferences.{key}" for key in Interaction.model_fields),
}


class Change(Model):
    path: str
    value: str | list[str]


class Refinement(Model):
    changes: list[Change] = Field(min_length=1, max_length=20)
    explanation: str = Field(max_length=2000)


def apply_changes(profile: Profile, proposal: Refinement) -> tuple[Profile, list[dict]]:
    data = profile.model_dump()
    diff = []
    seen = set()
    for change in proposal.changes:
        if change.path not in PATCH_PATHS or change.path in seen:
            raise ValueError("Invalid or repeated profile field")
        seen.add(change.path)
        parts = change.path.split(".")
        parent = data if len(parts) == 1 else data[parts[0]]
        before = parent[parts[-1]]
        parent[parts[-1]] = change.value
        if before != change.value:
            diff.append({"path": change.path, "before": before, "after": change.value})
    return Profile.model_validate(data), diff
