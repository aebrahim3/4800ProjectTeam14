from fastapi import FastAPI, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.core.database import get_db
from app.api.endpoints import recommendation
from app.core.config import settings

app = FastAPI(title=settings.PROJECT_NAME)

# Include Routers
app.include_router(recommendation.router, prefix="/api", tags=["recommendations"])

@app.get("/")
async def root():
    return {"message": f"Welcome to the {settings.PROJECT_NAME} API"}

@app.get("/health")
async def health(db: AsyncSession = Depends(get_db)):
    """
    Health check endpoint verifying database connectivity.
    """
    try:
        await db.execute(text("SELECT 1"))
        return {
            "status": "healthy",
            "database": "connected",
            "version": "1.0.0"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)