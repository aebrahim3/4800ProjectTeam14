from pydantic import BaseModel
from typing import Optional, Dict, Any

class RecommendationRequest(BaseModel):
    user_id: int
    question: str

class RecommendationResponse(BaseModel):
    status: str = "success"
    user_id: int
    question: str
    recommendation: str
    metadata: Dict[str, Any]
