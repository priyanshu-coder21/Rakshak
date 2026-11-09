from typing import Literal
from pydantic import BaseModel, Field


class RescueRequest(BaseModel):
    latitude: float = Field(
        ...,
        ge=-90.0,
        le=90.0
    )

    longitude: float = Field(
        ...,
        ge=-180.0,
        le=180.0
    )

    team_capacity: int = Field(
        ...,
        ge=5
    )


class RescueResponse(BaseModel):
    team_id: str

    status: Literal[
        "Available",
        "In_Transit",
        "Assigned"
    ]

    message: str