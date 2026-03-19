from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime

class SourceModel(BaseModel):
    file_name: str
    file_id: int
    relevance_score: float
    text_snippet: str

class LlmResponse(BaseModel):
    question: str
    answer: str
    sources: list[SourceModel]
