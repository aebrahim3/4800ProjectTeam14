from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.schemas.career import RecommendationRequest, RecommendationResponse
from app.services.llm import recommendation_service
import time

router = APIRouter()

@router.post("/career-recommendation", response_model=RecommendationResponse)
async def get_career_recommendation(
    request: RecommendationRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Get personalized career and educational recommendations.
    """
    start_time = time.time()
    try:
        result = await recommendation_service.get_recommendation(
            db, 
            request.user_id, 
            request.question
        )
        
        processing_time = time.time() - start_time
        result["metadata"]["processing_time_seconds"] = processing_time
        
        return RecommendationResponse(
            user_id=request.user_id,
            question=request.question,
            recommendation=result["recommendation"],
            metadata=result["metadata"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
