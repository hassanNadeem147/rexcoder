import json
import logging
from uuid import uuid4
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from langchain_core.messages import AIMessage, HumanMessage
from app.schemas.user_query_scheme import (
    UserQueryRequest,
    UserQueryResponse,
)
logger = logging.getLogger(__name__)
router = APIRouter()
def format_sse(event_name: str, data: dict) -> str:
    """Format one Server-Sent Event."""
    # JSON safely encodes newlines and other special characters.
    payload = json.dumps(data, ensure_ascii=False)
    return (
        f"event: {event_name}\n"
        f"data: {payload}\n\n"
    )
def make_initial_state(payload: UserQueryRequest) -> dict:
    """Create input for a new graph run or a follow-up turn."""
    # add_messages appends this new user message to saved history.
    state = {
        "messages": [
            HumanMessage(content=payload.message)
        ],
        "user_query": payload.message,
        # Reset per-request outputs and test status.
        "planner_output": "",
        "coder_output": "",
        "bug_fixer_output": "",
        "tester_output": "",
        "final_output": "",
        "generated_code": "",
        "fixed_code": "",
        "test_command": "",
        "test_result": "",
        "test_status": "not_run",
        "test_passed": None,
        "error_message": "",
        "retry_count": 0,
        "requires_testing": False,
    }
    return state
@router.post("/stream")
async def stream_user_query(
    payload: UserQueryRequest,
    request: Request,
) -> StreamingResponse:
    """Stream workflow progress and the final response to the frontend."""
    # The lifespan initializes the checkpointed graph on application startup.
    graph = getattr(request.app.state, "graph", None)
    if graph is None:
        raise HTTPException(
            status_code=503,
            detail="Workflow graph is not initialized. Restart the API server.",
        )
    # Generate an ID for new conversations.
    # Reuse the supplied ID for follow-up requests.
    thread_id = payload.thread_id or uuid4().hex
    config = {
        "configurable": {
            "thread_id": thread_id,
        }
    }
    input_state = make_initial_state(payload)
    async def event_stream():
        # Send the ID immediately so the frontend can keep it.
        yield format_sse(
            "meta",
            {"thread_id": thread_id},
        )
        try:
            # Stream node updates for progress and model chunks for live text.
            async for chunk in graph.astream(
                input_state,
                config=config,
                stream_mode=["updates", "messages"],
            ):
                mode, data = chunk
                if mode == "updates":
                    for node_name, updates in data.items():
                        progress_messages = {
                            "planner": "Understanding your request...",
                            "explainer": "Preparing the explanation...",
                            "coder": "Generating or updating code...",
                            "bug_fixer": "Investigating and repairing the code...",
                            "tester": "Reviewing the code...",
                            "final_response_builder": "Preparing your final answer...",
                        }
                        progress = {
                            "thread_id": thread_id,
                            "node": node_name,
                            "message": progress_messages.get(
                                node_name,
                                "Working on your request...",
                            ),
                        }
                        if node_name == "planner" and isinstance(updates, dict):
                            progress["task_type"] = updates.get("task_type")
                        yield format_sse("progress", progress)
                elif mode == "messages":
                    message, metadata = data
                    if (
                        metadata.get("langgraph_node") == "explainer"
                        and isinstance(message.content, str)
                        and message.content
                    ):
                        yield format_sse(
                            "token",
                            {"thread_id": thread_id, "text": message.content},
                        )
            # Read the completed checkpoint, which contains the final state.
            snapshot = await graph.aget_state(config)
            final_state = snapshot.values
            answer = final_state.get("final_output", "")
            if not isinstance(answer, str) or not answer.strip():
                yield format_sse(
                    "error",
                    {
                        "thread_id": thread_id,
                        "message": (
                            "The workflow finished without a final answer. "
                            "Check the final response builder."
                        ),
                    },
                )
                return
            task_type = final_state.get("task_type")
            requires_testing = final_state.get("requires_testing")
            code = None
            if task_type in {"generate", "debug", "modify"}:
                code = (
                    final_state.get("current_code")
                    or final_state.get("fixed_code")
                    or final_state.get("generated_code")
                )
            stored_answer = answer
            if code:
                stored_answer = f"{answer}\n\n```\n{code}\n```"
            await graph.aupdate_state(
                config,
                {"messages": [AIMessage(content=stored_answer)]},
            )
            # Do not present the absence of testing as a failure
            # when the task did not require code testing.
            test_status = (
                final_state.get("test_status")
                if requires_testing
                else None
            )
            test_passed = (
                final_state.get("test_passed")
                if requires_testing
                else None
            )
            test_result = (
                final_state.get("test_result")
                if requires_testing
                else None
            )

            final_response = UserQueryResponse(
                thread_id=thread_id,
                task_type=task_type,
                answer=answer,
                code=code,
                requires_testing=requires_testing,
                test_status=test_status,
                test_passed=test_passed,
                test_result=test_result,
                error_message=(
                    final_state.get("error_message") or None
                ),
            )
            # Send the final response as a distinct SSE event.
            yield format_sse(
                "done",
                final_response.model_dump(mode="json"),
            )
        except Exception:
            # Full details stay in server logs, not in the public response.
            logger.exception("Streaming workflow execution failed.")

            yield format_sse(
                "error",
                {
                    "thread_id": thread_id,
                    "message": (
                        "The workflow could not complete the request."
                    ),
                },
            )
    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )