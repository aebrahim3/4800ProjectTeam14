from fastapi import FastAPI
from sqlalchemy import create_engine, text
import os

from app.recommendations import router as recommendations_router

app = FastAPI()

# Database connection
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/careerMatchingEngine")
engine = create_engine(DATABASE_URL)
app.state.engine = engine
app.include_router(recommendations_router)

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
