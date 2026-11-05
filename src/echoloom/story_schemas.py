"""Strict story contracts, separate from ordinary chat turns."""

from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field, model_validator

from .schemas import Model


class StoryCreate(Model):
    conversation_id: UUID
    request_id: UUID
    description: str = Field(min_length=1, max_length=2000)
    player_name: str = Field(default="You", min_length=1, max_length=100)
    relationship: str = Field(default="", max_length=500)
    atmosphere: str = Field(default="", max_length=100)
    constraints: str = Field(default="", max_length=500)


class StoryAction(Model):
    request_id: UUID
    expected_revision: int = Field(ge=0)
    operation: Literal[
        "start", "continue", "decide", "interject", "rewrite", "undo", "end"
    ]
    decision_id: UUID | None = None
    option_id: UUID | None = None
    content: str = Field(default="", max_length=2000)
    input_type: Literal["dialogue", "action", "direction"] = "direction"
    revealed_block_id: UUID | None = None
    skip_generation: bool = False

    @model_validator(mode="after")
    def operation_fields(self):
        if self.operation in {"interject", "rewrite"} and not self.content:
            raise ValueError("Enter an instruction or your own contribution")
        if self.operation == "decide":
            if not self.decision_id or bool(self.option_id) == bool(self.content):
                raise ValueError(
                    "A decision requires its ID and exactly one option or free response"
                )
        elif self.decision_id or self.option_id:
            raise ValueError("Decision fields are only valid for decide")
        if self.operation != "interject" and self.revealed_block_id:
            raise ValueError("Revealed block belongs only to interject")
        if self.operation != "end" and self.skip_generation:
            raise ValueError("Direct completion belongs only to end")
        if self.operation in {"start", "continue", "undo", "end"} and self.content:
            raise ValueError("This operation does not take content")
        return self


class ReadingProgress(Model):
    expected_revision: int = Field(ge=0)
    segment_id: UUID
    last_revealed_block_id: UUID | None = None


class GeneratedBlock(Model):
    type: Literal["narration", "dialogue", "action"]
    speaker: Literal["player", "character"] | None
    text: str = Field(min_length=1, max_length=800)
    requires_player_decision: bool = False

    @model_validator(mode="after")
    def speaker_matches(self):
        if (self.type == "narration") != (self.speaker is None):
            raise ValueError(
                "Narration has no speaker; dialogue and action require one"
            )
        return self


class GeneratedOption(Model):
    intent: str = Field(min_length=1, max_length=200)


class GeneratedEnding(Model):
    type: Literal["continue", "decision", "ending"]
    question: str = Field(default="", max_length=500)
    options: list[GeneratedOption] = Field(default_factory=list, max_length=3)

    @model_validator(mode="after")
    def decision_shape(self):
        if self.type == "decision":
            intents = [" ".join(o.intent.split()).casefold() for o in self.options]
            if (
                not self.question
                or len(intents) < 2
                or len(set(intents)) != len(intents)
            ):
                raise ValueError(
                    "A decision needs a question and 2-3 distinct intentions"
                )
        elif self.options or self.question:
            raise ValueError(
                "Non-decision endings cannot contain a question or options"
            )
        return self


class StoryOutput(Model):
    title: str = Field(default="", max_length=100)
    blocks: list[GeneratedBlock] = Field(min_length=1, max_length=12)
    ending: GeneratedEnding
    summary: str = Field(min_length=1, max_length=2000)
    confirmed_facts: list[Annotated[str, Field(min_length=1, max_length=400)]] = Field(
        default_factory=list, max_length=30
    )
