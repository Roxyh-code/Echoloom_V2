from copy import deepcopy

import pytest
from echoloom.providers import ProviderError
from echoloom.rehearsal_graph import build_rehearsal_graph
from echoloom.rehearsal_schema import ConsistencyReview
from langgraph.checkpoint.sqlite import SqliteSaver
from test_rehearsal import create, quick


class QualityProvider:
    def __init__(self, base, report=False):
        self.base = base
        self.report = report
        self.writes = 0
        self.reviews = 0
        self.fail_review = False
        self.bad_quote = False
        self.change_unflagged = False
        self.unchanged = False
        self.last_review_messages = None

    def rehearsal(self, messages):
        return self.base.rehearsal(messages)

    def rehearsal_once(self, messages):
        self.writes += 1
        if self.writes == 1:
            self.original = self.base.rehearsal(messages)
            return self.original
        result = self.original.model_copy(deep=True)
        if not self.unchanged:
            result.blocks[0].text = "They wait beneath the station lights."
        if self.change_unflagged:
            result.blocks[1].text = "An unrelated change."
        return result

    def rehearsal_consistency(self, messages):
        self.reviews += 1
        self.last_review_messages = messages
        if self.fail_review:
            raise ProviderError("Simulated reviewer failure")
        issues = []
        if self.report:
            issues.append(
                {
                    "block_index": 0,
                    "kind": "hard_rule",
                    "evidence": "invented quote" if self.bad_quote else "The rain",
                    "rule_quote": "No rain in this scene.",
                    "explanation": "The narration introduces rain despite an explicit rule.",
                    "suggested_fix": "Remove the rain reference.",
                }
            )
        return ConsistencyReview(issues=issues)


def inputs(setup):
    c, text, _, settings, _ = setup
    scene = create(
        c,
        False,
        character_ids=[quick(c, "Lin"), quick(c, "Xu")],
        setup={
            "premise": "Two old friends meet at the station.",
            "rules": ["No rain in this scene."],
            "language": "en",
        },
    )
    doc = scene["document"]
    return (
        text,
        settings.model_copy(update={"rehearsal_consistency_enabled": True}),
        {
            "document": doc,
            "scene_version": doc["versions"][doc["active_version"]],
            "request_event": {"kind": "continue", "text": ""},
        },
    )


def test_clean_review_skips_repair(setup, tmp_path):
    base, settings, initial = inputs(setup)
    provider = QualityProvider(base)
    with SqliteSaver.from_conn_string(str(tmp_path / "quality.db")) as cp:
        graph = build_rehearsal_graph(provider, settings, cp)
        result = graph.invoke(
            initial, {"configurable": {"thread_id": "clean"}}, durability="sync"
        )
    assert provider.writes == provider.reviews == 1
    assert result["quality_status"] == "no_issue_found"
    assert result["repair_attempts"] == 0


def test_supported_issue_repairs_only_flagged_text(setup, tmp_path):
    base, settings, initial = inputs(setup)
    provider = QualityProvider(base, report=True)
    with SqliteSaver.from_conn_string(str(tmp_path / "quality.db")) as cp:
        result = build_rehearsal_graph(provider, settings, cp).invoke(
            initial, {"configurable": {"thread_id": "repair"}}, durability="sync"
        )
    assert provider.writes == 2
    assert provider.reviews == 1
    assert result["repair_attempts"] == 1
    assert result["quality_status"] == "repaired_unverified"
    assert (
        result["performance"]["blocks"][1]
        == provider.original.model_dump()["blocks"][1]
    )


@pytest.mark.parametrize("problem", ["bad_quote", "change_unflagged", "unchanged"])
def test_invalid_review_or_repair_fails_explicitly(setup, tmp_path, problem):
    base, settings, initial = inputs(setup)
    provider = QualityProvider(base, report=True)
    setattr(provider, problem, True)
    with SqliteSaver.from_conn_string(str(tmp_path / "quality.db")) as cp:
        graph = build_rehearsal_graph(provider, settings, cp)
        with pytest.raises(ProviderError):
            graph.invoke(
                initial, {"configurable": {"thread_id": problem}}, durability="sync"
            )
    assert provider.writes <= 2


def test_review_failure_resumes_without_regenerating(setup, tmp_path):
    base, settings, initial = inputs(setup)
    provider = QualityProvider(base)
    provider.fail_review = True
    path = str(tmp_path / "quality.db")
    config = {"configurable": {"thread_id": "resume"}}
    with SqliteSaver.from_conn_string(path) as cp:
        graph = build_rehearsal_graph(provider, settings, cp)
        with pytest.raises(ProviderError):
            graph.invoke(initial, config, durability="sync")
        assert graph.get_state(config).next == ("review_consistency",)
    provider.fail_review = False
    # Reopen the persisted DB and reconstruct the graph as a restarted worker would.
    with SqliteSaver.from_conn_string(path) as cp:
        result = build_rehearsal_graph(provider, settings, cp).invoke(
            None, config, durability="sync"
        )
    assert provider.writes == 1
    assert provider.reviews == 2
    assert result["quality_status"] == "no_issue_found"


def test_disabled_quality_uses_existing_provider(setup, tmp_path):
    base, settings, initial = inputs(setup)
    settings = settings.model_copy(update={"rehearsal_consistency_enabled": False})
    with SqliteSaver.from_conn_string(str(tmp_path / "quality.db")) as cp:
        result = build_rehearsal_graph(base, settings, cp).invoke(
            initial, {"configurable": {"thread_id": "baseline"}}, durability="sync"
        )
    assert result["quality_status"] == "disabled"
    assert sum(kind == "rehearsal" for kind, _ in base.calls) == 1


def test_other_branch_text_not_sent_to_reviewer(setup, tmp_path):
    base, settings, initial = inputs(setup)
    initial = deepcopy(initial)
    initial["document"]["nodes"]["unrelated"] = {
        "id": "unrelated",
        "parent": None,
        "blocks": [{"text": "OTHER_BRANCH_SECRET"}],
    }
    provider = QualityProvider(base)
    with SqliteSaver.from_conn_string(str(tmp_path / "quality.db")) as cp:
        build_rehearsal_graph(provider, settings, cp).invoke(
            initial, {"configurable": {"thread_id": "isolation"}}, durability="sync"
        )
    assert "OTHER_BRANCH_SECRET" not in str(provider.last_review_messages)
