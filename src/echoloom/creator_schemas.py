"""Contracts for the mobile creator, with immutable moments and scoped facts."""

from typing import Literal
from uuid import UUID

from pydantic import Field, model_validator

from .schemas import Model, Profile


class CreatorCreate(Model):
    request_id: UUID
    title: str = Field(default="", max_length=100)
    premise: str = Field(min_length=1, max_length=1000)
    character_ids: list[UUID] = Field(default_factory=list, max_length=2)
    mode: Literal["play", "direct"] = "play"
    player_name: str = Field(default="You", min_length=1, max_length=60)
    player_description: str = Field(default="", max_length=300)
    location: str = Field(default="", max_length=300)
    time: str = Field(default="", max_length=100)
    atmosphere: str = Field(default="", max_length=300)
    boundaries: str = Field(default="", max_length=500)
    world_rules: str = Field(default="", max_length=2000)
    demo: bool = False


class CreatorBlock(Model):
    type: Literal["narration", "action", "dialogue"]
    speaker: str | None = Field(default=None, max_length=60)
    text: str = Field(min_length=1, max_length=2000)
    source: Literal["ai", "author", "demo"] = "ai"


class CreatorOutput(Model):
    title: str = Field(default="", max_length=100)
    blocks: list[CreatorBlock] = Field(min_length=1, max_length=8)
    suggestions: list[str] = Field(default_factory=list, max_length=3)


class CreatorAction(Model):
    request_id: UUID
    expected_revision: int = Field(ge=0)
    operation: Literal[
        "continue",
        "direct",
        "rewrite",
        "edit",
        "fork",
        "checkpoint",
        "restore",
        "switch",
        "progress",
        "fact",
        "delete_fact",
        "scene",
        "rename",
        "archive",
        "finish",
        "update_cast",
        "delete_line",
        "delete_checkpoint",
        "setup",
    ]
    line_id: str = Field(default="", max_length=60)
    node_id: str = Field(default="", max_length=60)
    target_id: str = Field(default="", max_length=60)
    content: str = Field(default="", max_length=2000)
    name: str = Field(default="", max_length=100)
    blocks: list[CreatorBlock] = Field(default_factory=list, max_length=9)
    input_type: Literal["direction", "dialogue", "action"] = "direction"
    known_by: list[str] = Field(default_factory=list, max_length=2)
    confirmed: bool = True
    revealed: int = Field(default=0, ge=0, le=8000)

    @model_validator(mode="after")
    def required_content(self):
        if (
            self.operation in ("direct", "rewrite", "fork", "scene", "fact")
            and not self.content
        ):
            raise ValueError("Enter an instruction or content.")
        if self.operation == "edit" and not self.blocks:
            raise ValueError("A moment needs at least one block.")
        return self


class CreatorCharacterInput(Model):
    request_id: UUID
    description: str = Field(min_length=1, max_length=5000)


class CreatorImageInput(Model):
    request_id: UUID
    instruction: str = Field(default="", max_length=2000)
    editing: bool = False
    expected_image_id: UUID | None = None


class CastMember(Model):
    id: str = Field(min_length=1, max_length=60)
    character_id: str | None = Field(default=None, max_length=60)
    profile: Profile
    version: int = Field(default=1, ge=1)
    portrait_id: str | None = Field(default=None, max_length=60)
    portrait_url: str | None = Field(default=None, max_length=250)
    creation_job_id: str | None = Field(default=None, max_length=60)


class Moment(Model):
    id: str = Field(min_length=1, max_length=60)
    parent: str | None = Field(default=None, max_length=60)
    scene_id: str = Field(min_length=1, max_length=60)
    cast_id: str = Field(min_length=1, max_length=60)
    instruction: str = Field(default="", max_length=2000)
    blocks: list[CreatorBlock] = Field(min_length=1, max_length=9)
    suggestions: list[str] = Field(default_factory=list, max_length=3)
    source: Literal["ai", "demo", "author"] = "author"


class Line(Model):
    finished: bool = False
    world_rules: str = Field(default="", max_length=2000)
    id: str = Field(min_length=1, max_length=60)
    name: str = Field(min_length=1, max_length=100)
    head: str | None = Field(default=None, max_length=60)
    cast_id: str = Field(min_length=1, max_length=60)
    origin: str = Field(default="Opening", max_length=120)
    revealed: int = Field(default=0, ge=0, le=8000)


class SceneSetup(Model):
    location: str = Field(default="", max_length=300)
    time: str = Field(default="", max_length=100)
    atmosphere: str = Field(default="", max_length=300)
    boundaries: str = Field(default="", max_length=500)
    id: str = Field(min_length=1, max_length=60)
    title: str = Field(min_length=1, max_length=100)
    premise: str = Field(min_length=1, max_length=2000)


class Checkpoint(Model):
    id: str = Field(min_length=1, max_length=60)
    name: str = Field(min_length=1, max_length=100)
    line: Line
    created_at: str = Field(max_length=60)
    facts: list[dict] = Field(default_factory=list, max_length=500)


class StoryFact(Model):
    id: str = Field(min_length=1, max_length=60)
    line_id: str = Field(max_length=60)
    source: str | None = Field(default=None, max_length=60)
    text: str = Field(min_length=1, max_length=2000)
    known_by: list[str] = Field(default_factory=list, max_length=2)
    status: Literal["confirmed", "suggested", "needs_review"] = "suggested"


class CreatorDocument(Model):
    schema_version: Literal[1] = 1
    title: str = Field(min_length=1, max_length=100)
    premise: str = Field(min_length=1, max_length=1000)
    mode: Literal["play", "direct"]
    demo: bool
    archived: bool = False
    finished: bool = False
    active_line: str = Field(max_length=60)
    casts: dict[str, list[CastMember]]
    scenes: dict[str, SceneSetup]
    nodes: dict[str, Moment]
    lines: dict[str, Line]
    checkpoints: list[Checkpoint] = Field(default_factory=list, max_length=100)
    facts: list[StoryFact] = Field(default_factory=list, max_length=500)

    @model_validator(mode="after")
    def graph(self):
        if (
            len(self.nodes) > 1000
            or len(self.lines) > 100
            or len(self.scenes) > 100
            or len(self.casts) > 100
        ):
            raise ValueError(
                "This story has reached the prototype size limit. Export a backup."
            )
        if self.active_line not in self.lines:
            raise ValueError("Missing active storyline")

        def safe_cast(key):
            if key not in self.casts or len(self.casts[key]) != 2:
                raise ValueError("A scene needs two participants")
            members = self.casts[key]
            if len({m.id for m in members}) != 2:
                raise ValueError("Duplicate participant")
            for m in members:
                url = m.portrait_url
                if url and not (
                    url in ("/creator/mira.svg", "/creator/leo.svg")
                    or (
                        m.character_id
                        and m.portrait_id
                        and url
                        == f"/api/characters/{m.character_id}/images/{m.portrait_id}/file"
                    )
                ):
                    raise ValueError("Invalid portrait reference")

        for key in self.casts:
            safe_cast(key)
        for key, n in self.nodes.items():
            safe_cast(n.cast_id)
            if (
                key != n.id
                or n.scene_id not in self.scenes
                or (n.parent and n.parent not in self.nodes)
            ):
                raise ValueError("Invalid moment reference")
            allowed = {m.id for m in self.casts[n.cast_id]}
            for b in n.blocks:
                if b.type == "narration" and b.speaker is not None:
                    raise ValueError("Narration cannot have a speaker")
                if b.type != "narration" and b.speaker not in allowed:
                    raise ValueError("Unknown speaker")
            seen = set()
            cursor = n
            while cursor:
                if cursor.id in seen:
                    raise ValueError("Cyclic moment graph")
                seen.add(cursor.id)
                cursor = self.nodes.get(cursor.parent)
        for key, line in self.lines.items():
            safe_cast(line.cast_id)
            if key != line.id or (line.head and line.head not in self.nodes):
                raise ValueError("Invalid storyline")
        for key, scene in self.scenes.items():
            if key != scene.id:
                raise ValueError("Invalid scene reference")
        for c in self.checkpoints:
            safe_cast(c.line.cast_id)
            if c.line.head and c.line.head not in self.nodes:
                raise ValueError("Missing saved moment")
            for raw in c.facts:
                fact = StoryFact.model_validate(raw)
                allowed = {m.id for m in self.casts[c.line.cast_id]}
                if (
                    fact.line_id != c.line.id
                    or (fact.source and fact.source not in self.nodes)
                    or any(w not in allowed for w in fact.known_by)
                ):
                    raise ValueError("Invalid saved fact reference")
        if len({c.id for c in self.checkpoints}) != len(self.checkpoints):
            raise ValueError("Duplicate saved version")
        if len({f.id for f in self.facts}) != len(self.facts):
            raise ValueError("Duplicate fact")
        for fact in self.facts:
            if fact.line_id not in self.lines or (
                fact.source and fact.source not in self.nodes
            ):
                raise ValueError("Invalid fact source")
            if any(
                w not in {m.id for m in self.casts[self.lines[fact.line_id].cast_id]}
                for w in fact.known_by
            ):
                raise ValueError("Unknown fact participant")
        return self


class CreatorImport(Model):
    request_id: UUID
    document: CreatorDocument


def resolve_creator_speakers(output, cast):
    """Resolve exact, unambiguous names only; never guess an unknown identity."""
    result = CreatorOutput.model_validate(output).model_copy(deep=True)
    allowed = {member["id"] for member in cast}
    aliases = {}
    for member in cast:
        aliases.setdefault(member["profile"]["name"].strip().casefold(), set()).add(
            member["id"]
        )
    for block in result.blocks:
        if block.type == "narration":
            if block.speaker is None or block.speaker.casefold() in (
                "narrator",
                "narration",
            ):
                block.speaker = None
                continue
            raise ValueError("Narration must have speaker null.")
        if block.speaker in allowed:
            continue
        matches = aliases.get((block.speaker or "").strip().casefold(), set())
        if len(matches) != 1:
            raise ValueError("Unknown or ambiguous speaker. Use an exact cast ID.")
        block.speaker = next(iter(matches))
    return result
