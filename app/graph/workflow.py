from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, StateGraph

from app.graph.nodes.bug_fixer import bug_fixer_node
from app.graph.nodes.coder import coder_node
from app.graph.nodes.explainer import explainer_node
from app.graph.nodes.final_response_builder import final_response_builder_node
from app.graph.nodes.planner import planner_node
from app.graph.nodes.tester import tester_node
from app.graph.state import CodingState


def route_after_planner(state: CodingState) -> str:
    task_type = state.get("task_type")
    if task_type == "debug":
        return "debug"
    if task_type == "generate":
        return "generate"
    if task_type == "modify":
        return "modify"
    return "question"


def route_after_tester(state: CodingState) -> str:
    if state.get("test_passed") is True:
        return "passed"
    if state.get("test_passed") is False:
        retry_count = int(state.get("retry_count") or 0)
        if retry_count < 2:
            return "retry"
    return "failed"


def build_graph(checkpointer: BaseCheckpointSaver | None = None):
    workflow = StateGraph(CodingState)
    workflow.set_entry_point("planner")
    workflow.add_node("planner", planner_node)
    workflow.add_node("explainer", explainer_node)
    workflow.add_node("coder", coder_node)
    workflow.add_node("tester", tester_node)
    workflow.add_node("bug_fixer", bug_fixer_node)
    workflow.add_node("final_response_builder", final_response_builder_node)
    workflow.add_conditional_edges(
        "planner",
        route_after_planner,
        {
            "question": "explainer",
            "generate": "coder",
            "modify": "coder",
            "debug": "bug_fixer",
        },
    )
    workflow.add_edge("explainer", "final_response_builder")
    workflow.add_edge("coder", "tester")
    workflow.add_conditional_edges(
        "tester",
        route_after_tester,
        {
            "passed": "final_response_builder",
            "retry": "bug_fixer",
            "failed": "final_response_builder",
        },
    )
    workflow.add_edge("bug_fixer", "tester")
    workflow.add_edge("final_response_builder", END)
    return workflow.compile(checkpointer=checkpointer)
