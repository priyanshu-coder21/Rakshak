from pydantic import BaseModel, Field


class DistressRequest(BaseModel):
    raw_message: str = Field(
        ...,
        min_length=5,
        description="Message of the victim"
    )

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


class DistressResponse(BaseModel):
    token_id: str
    status: str
    extracted_data: dict
    message: str