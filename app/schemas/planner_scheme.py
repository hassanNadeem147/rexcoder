from typing import Literal
from pydantic import BaseModel, Field
# These are the only task categories the planner may return.
TaskType = Literal["question", "generate", "debug", "modify"]
class PlannerDecision(BaseModel):
    """
    Structured output expected from the planner LLM.
    Pydantic validates the returned data against these fields.
    """
    # Identifies the user's primary intent.
    # This value will later be used by LangGraph conditional edges.
    task_type: TaskType = Field(
        description=(
            "Classify the user's request as question, generate, "
            "debug, or modify."
        )
    )
    # Gives the next node a short, actionable plan.
    # This is a plan, not the actual code implementation.
    plan: str = Field(
        description=(
            "Provide a concise plan describing how to handle the "
            "request. Do not implement the code."
        )
    )
    # Indicates whether this task requires code testing.
    # This does not mean that testing has already happened.
    requires_testing: bool = Field(
        description=(
            "Return false for ordinary informational questions, including "
            "questions with educational code examples. Return true when "
            "code generated, debugged, or modified should be tested."
        )
    )