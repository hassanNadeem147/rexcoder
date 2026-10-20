from typing import Annotated, Literal
from typing_extensions import NotRequired, TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph import add_messages
from app.schemas.planner_scheme import TaskType
class CodingState(TypedDict):
    """
    Shared state for the AI coding workflow.
    Nodes read the information they need and return updates
    to the fields they are responsible for.
    """
    # --------------------------------------------------
    # 1. Conversation and User Request
    # --------------------------------------------------
    # Stores conversation messages.
    # add_messages merges new messages with the existing history.
    messages: Annotated[list[BaseMessage], add_messages]
    # The user's current request, for direct access by workflow nodes.
    user_query: NotRequired[str]
    # A concise summary of important older conversation details.
    # This field must be populated by your application or a summary node.
    conversation_summary: NotRequired[str]
    # --------------------------------------------------
    # 2. Planning and Routing
    # --------------------------------------------------
    # The task category selected by the planner.
    # Conditional edges will use this field to select the next node.
    task_type: NotRequired[TaskType]
    # The planner's actionable plan for the selected task.
    planner_output: NotRequired[str]
    # Indicates whether this task requires testing.
    requires_testing: NotRequired[bool]
    # --------------------------------------------------
    # 3. Code Versions
    # --------------------------------------------------
    # Original code supplied by the user.
    existing_code: NotRequired[str]
    # New code produced by the coder.
    generated_code: NotRequired[str]
    # Repaired code produced by the bug fixer.
    fixed_code: NotRequired[str]
    # The current code version that should be tested or returned.
    current_code: NotRequired[str]
    # --------------------------------------------------
    # 4. Agent Outputs
    # --------------------------------------------------
    # Coder's implementation notes or summary.
    coder_output: NotRequired[str]
    # Bug fixer's diagnosis and repair summary.
    bug_fixer_output: NotRequired[str]
    # Tester's findings and interpretation of test results.
    tester_output: NotRequired[str]
    # --------------------------------------------------
    # 5. Testing and Error Handling
    # --------------------------------------------------
    # Approved command or procedure used to test the code.
    test_command: NotRequired[str]
    # Actual output returned by the test runner.
    test_result: NotRequired[str]
    # Whether the required tests passed.
    # Missing means the result has not yet been determined.
    test_passed: NotRequired[bool | None]
    test_status: NotRequired[Literal["passed", "failed", "not_run", "timeout", "error"]]
    # Relevant error details for diagnosing failures.
    error_message: NotRequired[str]
    # Counts repair attempts to help prevent an endless repair loop.
    retry_count: NotRequired[int]
    # --------------------------------------------------
    # 6. Final Response
    # --------------------------------------------------
    # Final user-facing response, including code, explanation,
    # test status, and any remaining issues.
    final_output: NotRequired[str]