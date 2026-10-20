from pydantic import BaseModel, Field
class CoderResult(BaseModel):
    """Structured output returned by the Coder Agent."""
    # Contains the actual source code produced by the coder.
    # Do not include Markdown code fences or explanations in this field.
    code: str = Field(
        description=(
            "The complete source code for the requested implementation. "
            "Return source code only, without Markdown fences."
        )
    )
    # Contains a user-friendly explanation of the implementation.
    # This is separate from the actual source code.
    explanation: str = Field(
        description=(
            "Briefly explain what was implemented or changed, "
            "and mention important implementation choices. "
            "Do not claim that tests have passed."
        )
    )