"""Rehearsal contracts: two actors, explicit state and immutable text blocks."""

from typing import Literal
from uuid import UUID

from pydantic import Field, model_validator

from .schemas import Model


class Setup(Model):
    premise: str = Field(default="", max_length=2000)
    goal: str = Field(default="", max_length=500)
    format: Literal["prose", "script"] = "prose"
    relation: str = Field(default="", max_length=1000)
    location: str = Field(default="", max_length=1000)
    time: str = Field(default="", max_length=1000)
    knowledge_a: str = Field(default="", max_length=1000)
    knowledge_b: str = Field(default="", max_length=1000)
    rules: list[str] = Field(default_factory=list, max_length=10)
    language: Literal["zh", "en"] = "en"

    @model_validator(mode="after")
    def rules_length(self):
        if any(not r.strip() or len(r) > 200 for r in self.rules):
            raise ValueError("Each rule must contain 1–200 characters.")
        return self


class CreateScene(Model):
    operation_id: UUID
    character_ids: list[UUID] = Field(default_factory=list, max_length=2)
    setup: Setup = Field(default_factory=Setup)
    demo: bool = False
    source_scene_id: UUID | None = None


class QuickCharacter(Model):
    operation_id: UUID
    name: str = Field(min_length=1, max_length=30)
    description: str = Field(min_length=10, max_length=1500)


class Block(Model):
    type: Literal["narration", "dialogue", "action"]
    character_id: str | None = Field(default=None, max_length=60)
    text: str = Field(min_length=1, max_length=2000)


class StateChange(Model):
    after_block: int = Field(default=0, ge=0, le=7)
    text: str = Field(min_length=1, max_length=500)
    known_by: list[str] = Field(default_factory=list, max_length=2)
    kind: Literal["fact", "belief", "goal", "relationship", "thread"] = "fact"


class Performance(Model):
    conflicts: list[str] = Field(default_factory=list, max_length=5)
    blocks: list[Block] = Field(default_factory=list, max_length=8)
    changes: list[StateChange] = Field(default_factory=list, max_length=12)
    ending: bool = False


class Direction(Model):
    id: str = Field(min_length=1, max_length=60)
    title: str = Field(min_length=1, max_length=60)
    choice: str = Field(min_length=1, max_length=300)
    consequence: str = Field(min_length=1, max_length=300)


class Directions(Model):
    options: list[Direction] = Field(min_length=2, max_length=2)


class Review(Model):
    summary: str = Field(max_length=1500)
    changes: list[str] = Field(default_factory=list, max_length=6)
    threads: list[str] = Field(default_factory=list, max_length=6)


class Command(Model):
    operation_id: UUID
    expected_revision: int = Field(ge=0)
    kind: Literal[
        "cast",
        "setup",
        "continue",
        "direction",
        "event",
        "takeover",
        "release",
        "speak",
        "branch",
        "edit",
        "replay",
        "switch",
        "rename",
        "result",
        "progress",
        "read",
        "settle",
        "delete_version",
        "stop_instruction",
        "feedback",
    ]
    version_id: str = Field(default="", max_length=60)
    node_id: str = Field(default="", max_length=60)
    block_id: str = Field(default="", max_length=60)
    target_id: str = Field(default="", max_length=60)
    text: str = Field(default="", max_length=2000)
    name: str = Field(default="", max_length=100)
    persistent: bool = False
    edit_type: Literal["wording", "plot"] = "plot"
    input_type: Literal["dialogue", "action"] = "dialogue"
    character_ids: list[UUID | None] = Field(default_factory=list, max_length=2)
    setup: Setup | None = None
    position: int = Field(default=0, ge=0, le=100000)
    revealed: int = Field(default=0, ge=0, le=100000)

    @model_validator(mode="after")
    def nonempty(self):
        if (
            self.kind in ("direction", "event", "speak", "branch", "edit", "feedback")
            and not self.text
        ):
            raise ValueError("Enter your contribution.")
        if self.kind in ("direction", "event") and len(self.text) > 1000:
            raise ValueError("Instructions are limited to 1000 characters.")
        return self


class QueryOperation(Model):
    operation_id: UUID
    version_id: str = Field(default="", max_length=60)
    node_id: str = Field(default="", max_length=60)


class ExportOptions(Model):
    version_id: str = ""
    format: Literal["txt", "md"] = "txt"
    include_title: bool = True
    include_names: bool = True
