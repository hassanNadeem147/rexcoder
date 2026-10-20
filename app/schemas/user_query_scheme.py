from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator
from app.schemas.planner_scheme import TaskType
TesterStatus = Literal[
    "passed",
    "failed",
    "not_run",
    "timeout",
    "error",
]
class UserQueryRequest(BaseModel):
    """Request sent by the frontend to Rexcoder."""
    model_config = ConfigDict(extra="forbid")

    message: str = Field(
        min_length=1,
        max_length=20_000,
        description="The user's current request.",
    )
    # Omit this field to start a new conversation.
    # Send the returned ID to continue an existing conversation.
    thread_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=128,
        description=(
            "Omit to create a new conversation. Reuse the returned ID "
            "to continue an existing conversation."
        ),
    )

    @field_validator("message")
    @classmethod
    def validate_message(cls, value: str) -> str:
        if not (value := value.strip()):
            raise ValueError("Message cannot be empty.")
        return value

    @field_validator("thread_id")
    @classmethod
    def validate_thread_id(cls, value: str | None) -> str | None:
        if value is not None and not (value := value.strip()):
            raise ValueError("Thread ID cannot be empty.")
        return value


class UserQueryResponse(BaseModel):
    """Final result returned to the frontend."""
    thread_id: str
    task_type: TaskType | None = None
    answer: str
    # Final active source code for coding tasks.
    code: str | None = None
    requires_testing: bool | None = None
    test_status: TesterStatus | None = None
    test_passed: bool | None = None
    test_result: str | None = None
    # Empty internal errors are returned as None.
    error_message: str | None = None