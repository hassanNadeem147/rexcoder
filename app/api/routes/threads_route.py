from fastapi import APIRouter, HTTPException, Request
from langchain_core.messages import AIMessage, HumanMessage

router = APIRouter()


def _message_text(message) -> dict[str, str] | None:
    if not isinstance(message.content, str) or not message.content.strip():
        return None
    if isinstance(message, HumanMessage):
        role = "user"
    elif isinstance(message, AIMessage):
        role = "assistant"
    else:
        return None
    return {"role": role, "content": message.content}


@router.get("")
async def list_threads(request: Request) -> dict:
    graph = getattr(request.app.state, "graph", None)
    if graph is None:
        raise HTTPException(status_code=503, detail="Workflow graph is not initialized.")
    checkpointer = graph.checkpointer
    thread_ids = []
    seen = set()
    async for checkpoint in checkpointer.alist(None, limit=1000):
        thread_id = checkpoint.config.get("configurable", {}).get("thread_id")
        if not thread_id or thread_id in seen:
            continue
        seen.add(thread_id)
        if len(thread_ids) < 100:
            thread_ids.append(thread_id)
    threads = []
    for thread_id in thread_ids:
        snapshot = await graph.aget_state(
            {"configurable": {"thread_id": thread_id}}
        )
        state_messages = snapshot.values.get("messages", [])
        title = next(
            (
                message.content.strip()
                for message in state_messages
                if isinstance(message, HumanMessage)
                and isinstance(message.content, str)
                and message.content.strip()
            ),
            "New conversation",
        )
        threads.append({"thread_id": thread_id, "title": title[:80]})
    return {"threads": threads}


@router.get("/{thread_id}")
async def get_thread(thread_id: str, request: Request) -> dict:
    graph = getattr(request.app.state, "graph", None)
    if graph is None:
        raise HTTPException(status_code=503, detail="Workflow graph is not initialized.")
    snapshot = await graph.aget_state(
        {"configurable": {"thread_id": thread_id}}
    )
    if not snapshot.values:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    messages = [
        item
        for message in snapshot.values.get("messages", [])
        if (item := _message_text(message)) is not None
    ]
    return {"thread_id": thread_id, "messages": messages}
