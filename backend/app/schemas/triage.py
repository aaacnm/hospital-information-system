from pydantic import BaseModel, Field


class TriageRequest(BaseModel):
    symptoms: str = Field(default="", max_length=2000)


class TriageResponse(BaseModel):
    dept: str
    urgency: str
    notes: str
    disclaimer: str
    source: str
