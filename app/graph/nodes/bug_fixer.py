import asyncio

from langchain_core.messages import HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq

from app.core.config import get_settings
from app.graph.state import CodingState

settings = get_settings()
api_key = settings.GROQ_API_KEY
if hasattr(api_key, "get_secret_value"):
    api_key = api_key.get_secret_value()
if not api_key:
    raise ValueError("GROQ_API_KEY is missing from your configuration.")

llm = ChatGroq(
    model=settings.GROQ_MODEL,
    api_key=api_key,
    temperature=0,
)

BUG_FIXER_PROMPT = """You are the Bug Fixer for Rexcoder.
Repair the code based on the reported failure and the user's request.
Return only the corrected code and a brief explanation.
If you cannot fully determine the fix, explain the missing information instead of inventing it.
"""

bug_fixer_prompt = ChatPromptTemplate.from_messages([
    ("system", BUG_FIXER_PROMPT),
    ("human", """USER REQUEST:
{user_query}
TASK TYPE:
{task_type}
CURRENT CODE:
{current_code}
ERROR / TEST FEEDBACK:
{error_message}
PLANNER PLAN:
{planner_output}
CONVERSATION CONTEXT:
{conversation_context}
"""),
])

bug_fixer_chain = bug_fixer_prompt | llm


def _extract_code_block(text: str) -> str:
    if "```" not in text:
        return text.strip()

    parts = text.split("```")
    if len(parts) >= 3:
        for i in range(1, len(parts), 2):
            candidate = parts[i].strip()
            if candidate and not candidate.lower().startswith("python"):
                return candidate
        return parts[1].strip()
    return text.strip()


async def bug_fixer_node(state: CodingState) -> dict:
    messages = state.get("messages", [])
    user_query = next(
        (
            message.content.strip()
            for message in reversed(messages)
            if (
                isinstance(message, HumanMessage)
                and isinstance(message.content, str)
                and message.content.strip()
            )
        ),
        "",
    ) or state.get("user_query", "").strip()

    if not user_query:
        raise ValueError("No user request was provided to the Bug Fixer.")

    task_type = state.get("task_type") or "debug"
    current_code = (state.get("current_code") or state.get("generated_code") or state.get("fixed_code") or "").strip()
    error_message = (state.get("error_message") or state.get("test_result") or "No detailed error message was supplied.").strip()
    planner_output = (state.get("planner_output") or "No planner plan was supplied.").strip()

    conversation_summary = (state.get("conversation_summary") or "No older conversation summary is available.").strip()
    recent_messages = messages[-8:]
    context_lines = []
    for message in recent_messages:
        if isinstance(message, HumanMessage) and isinstance(message.content, str):
            text = message.content.strip()
            if text and text != user_query:
                context_lines.append(f"{message.type}: {text}")
    recent_context = "\n".join(context_lines) or "No additional recent messages."
    conversation_context = (
        f"IMPORTANT OLDER CONTEXT:\n{conversation_summary}\n\n"
        f"RECENT CONVERSATION:\n{recent_context}"
    )

    response = await bug_fixer_chain.ainvoke(
        {
            "user_query": user_query,
            "task_type": task_type,
            "current_code": current_code,
            "error_message": error_message,
            "planner_output": planner_output,
            "conversation_context": conversation_context,
        }
    )

    fixed_text = response.content if isinstance(response.content, str) else str(response.content)
    fixed_code = _extract_code_block(fixed_text)
    retry_count = int(state.get("retry_count") or 0) + 1

    return {
        "bug_fixer_output": fixed_text,
        "current_code": fixed_code,
        "fixed_code": fixed_code,
        "retry_count": retry_count,
        "error_message": error_message,
    }


async def test_bug_fixer():
    state = {
        "messages": [HumanMessage(content="Fix the function to return the sum of two numbers.")],
        "user_query": "Fix the function to return the sum of two numbers.",
        "task_type": "debug",
        "current_code": "def add(a, b):\n    return a - b",
        "planner_output": "Repair the arithmetic bug and re-test the code.",
        "error_message": "The function returns subtraction instead of addition.",
        "conversation_summary": "",
    }
    result = await bug_fixer_node(state)
    print(result["fixed_code"])


if __name__ == "__main__":
    asyncio.run(test_bug_fixer())
