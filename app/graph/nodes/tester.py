from langchain_core.messages import HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
from app.core.config import get_settings
from app.graph.state import CodingState
from app.schemas.tester_scheme import TesterResult
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
TESTER_PROMPT = """You are the Tester for Rexcoder.
Review the supplied code against the user's request and the planner plan.
This is a static review: do not claim that the code was executed or tested.
Mark passed only if the implementation appears to meet the request by inspection.
Mark failed when the code is incorrect, incomplete, or cannot be assessed.
Return concise findings in the structured result.
"""
tester_prompt = ChatPromptTemplate.from_messages([
    ("system", TESTER_PROMPT),
    ("human", """USER REQUEST:
{user_query}
TASK TYPE:
{task_type}
PLANNER PLAN:
{planner_output}
CURRENT CODE:
{current_code}
CONVERSATION CONTEXT:
{conversation_context}
"""),
])
tester_chain = tester_prompt | llm.with_structured_output(TesterResult)
async def tester_node(state: CodingState) -> dict:
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
        raise ValueError("No user request was provided to the Tester.")
    task_type = state.get("task_type") or "generate"
    planner_output = (state.get("planner_output") or "No planner plan was supplied.").strip()
    current_code = (state.get("current_code") or state.get("generated_code") or state.get("fixed_code") or "").strip()
    if not current_code:
        current_code = "No code was provided for testing."
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
    response = await tester_chain.ainvoke(
        {
            "user_query": user_query,
            "task_type": task_type,
            "planner_output": planner_output,
            "current_code": current_code,
            "conversation_context": conversation_context,
        }
    )
    if not isinstance(response, TesterResult):
        raise TypeError("Tester did not return a valid structured result.")
    status = "passed" if response.passed else "failed"
    content = f"Static review {status}: {response.summary}"
    return {
        "tester_output": content,
        "test_result": content,
        "test_passed": response.passed,
        "test_status": status,
        "test_command": "Static code review; code was not executed.",
        "error_message": "" if response.passed else response.summary,
        "retry_count": state.get("retry_count", 0),
    }