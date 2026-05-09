from fastapi import FastAPI, HTTPException
from sqlalchemy import create_engine, text
from pydantic import BaseModel
from typing import List
import os
from app.services.matching_service import find_closest_jobs

app = FastAPI()

# Database connection
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@db:5432/myapp")
engine = create_engine(DATABASE_URL)

class MatchRequest(BaseModel):
    vector: List[float]
    limit: int = 5

@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.get("/health")
async def health():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}

@app.post("/api/match-jobs")
async def match_jobs(request: MatchRequest):
    """
    Find closest O*NET jobs based on provided feature vector.
    Vector should have 74 dimensions (33 Knowledge + 41 Work Activities).
    """
    if len(request.vector) != 74:
        raise HTTPException(status_code=400, detail="Vector must have 74 dimensions.")
    
    try:
        results = find_closest_jobs(engine, request.vector, request.limit)
        return {"matches": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/llm")
async def call_llm(prompt: str):
    """
    Call OpenRouter LLM API
    Example endpoint, needs to implement specific logic
    """
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        return {"error": "OPENROUTER_API_KEY not set"}
    
    return {"prompt": prompt, "response": "TODO: Implement LLM integration"}