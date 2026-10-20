from pydantic import BaseModel, Field


class TesterResult(BaseModel):
    """Structured result from the Tester's static code review."""

    passed: bool = Field(
        description="Whether the implementation meets the request by inspection."
    )
    summary: str = Field(
        description="Concise review findings; do not claim code was executed."
    )
