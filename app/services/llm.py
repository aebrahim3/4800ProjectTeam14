from openai import AsyncOpenAI
from app.core.config import settings
from app.services.vectorizer import vectorizer
from app.services.search import search_service
from app.services.context import context_service
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any

class LLMRecommendationService:
    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=settings.OPENROUTER_API_KEY,
            base_url=settings.OPENROUTER_BASE_URL
        )
        self.model = settings.LLM_MODEL

    async def get_recommendation(self, db: AsyncSession, user_id: int, question: str) -> Dict[str, Any]:
        """
        Complete RAG pipeline: Vectorize -> Search -> Assemble Context -> Call LLM.
        """
        # 1. Vectorize the user's question
        question_vector = await vectorizer.get_embedding(question)
        
        # 2. Perform semantic search across tables
        jobs = await search_service.search_job_profiles(db, question_vector)
        nocs = await search_service.search_noc_codes(db, question_vector)
        skills = await search_service.search_skills(db, question_vector)
        
        # 3. Fetch user context
        user_context = await context_service.get_user_context(db, user_id)
        
        # 4. Assemble full context for the LLM
        market_context = context_service.format_search_results(jobs, nocs, skills)
        
        system_prompt = f"""
You are an expert career advisor specializing in technology careers in Canada.
Your goal is to provide personalized, data-driven career and educational recommendations.

Use the provided User Profile and Job Market Data to answer the user's question.
Be specific about job titles, salary ranges in CAD, and learning pathways.

USER PROFILE:
{user_context}

JOB MARKET DATA:
{market_context}
"""

        # 5. Call OpenRouter API
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": question}
            ],
            temperature=0.7,
            max_tokens=2000
        )
        
        return {
            "recommendation": response.choices[0].message.content,
            "metadata": {
                "model": self.model,
                "jobs_found": len(jobs),
                "nocs_found": len(nocs),
                "skills_found": len(skills)
            }
        }

recommendation_service = LLMRecommendationService()
