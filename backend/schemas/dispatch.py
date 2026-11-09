from pydantic import BaseModel, Field


class RescueCompleteRequest(BaseModel):
    token_id: str = Field(
        ...,
        description="Unique token ID of the rescued victim"
    )

    team_id: str = Field(
        ...,
        description="ID of the rescue team completing the operation"
    )