from pydantic import BaseModel, Field


class StopSegment(BaseModel):
    distance_km: float = Field(ge=0)
    slow_min: float = Field(ge=0)


class MultiStopRequest(BaseModel):
    segments: list[StopSegment] = Field(min_length=2)
    night: bool = False
    persist: bool = True
