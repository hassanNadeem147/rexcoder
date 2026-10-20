from app.graph.state import CodingState


async def final_response_builder_node(state: CodingState) -> dict:
    task_type = state.get("task_type") or "question"

    if task_type == "question":
        final_output = state.get("final_output") or "No explanation was generated."
    else:
        parts = []
        if state.get("coder_output"):
            parts.append(f"Implementation summary:\n{state.get('coder_output')}")
        if state.get("tester_output"):
            parts.append(f"Testing summary:\n{state.get('tester_output')}")
        if state.get("bug_fixer_output"):
            parts.append(f"Bug fix summary:\n{state.get('bug_fixer_output')}")
        if not parts:
            final_output = "The workflow completed without a detailed final result."
        else:
            final_output = "\n\n".join(parts)

    return {"final_output": final_output}
