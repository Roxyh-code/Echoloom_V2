"""Checkpoint-enabled workflow for one rehearsal segment."""

from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from .rehearsal_domain import context, validate_performance


class RehearsalState(TypedDict, total=False):
    """Data shared by the nodes during one generation operation."""

    document: dict[str, Any]
    scene_version: dict[str, Any]
    request_event: dict[str, Any]

    messages: list[dict[str, Any]]
    performance: dict[str, Any]


def build_rehearsal_graph(
    text_provider,
    settings,
    checkpointer,
):
    """Build the workflow using the existing generation functions."""

    def prepare_context(state: RehearsalState):
        messages = context(
            state["document"],
            state["scene_version"],
            state["request_event"],
            settings,
        )

        return {"messages": messages}

    def generate_performance(state: RehearsalState):
        performance = text_provider.rehearsal(
            state["messages"]
        )

        # Store plain data in checkpoints rather than custom model objects.
        return {
            "performance": performance.model_dump(mode="json")
        }

    def validate_output(state: RehearsalState):
        performance = validate_performance(
            state["performance"],
            state["document"],
            state["scene_version"],
        )

        return {
            "performance": performance.model_dump(mode="json")
        }

    builder = StateGraph(RehearsalState)

    builder.add_node("prepare_context", prepare_context)
    builder.add_node("generate_performance", generate_performance)
    builder.add_node("validate_output", validate_output)

    builder.add_edge(START, "prepare_context")
    builder.add_edge("prepare_context", "generate_performance")
    builder.add_edge("generate_performance", "validate_output")
    builder.add_edge("validate_output", END)

    return builder.compile(checkpointer=checkpointer)