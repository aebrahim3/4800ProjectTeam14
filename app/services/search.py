from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.market import JobProfile, NocCode, SkillTaxonomy
from typing import List, Any

class VectorSearchService:
    async def search_job_profiles(self, db: AsyncSession, vector: List[float], limit: int = 5) -> List[JobProfile]:
        """
        Search for job profiles similar to the given vector.
        """
        # Using cosine distance (<=>)
        query = select(JobProfile).order_by(JobProfile.embedding.cosine_distance(vector)).limit(limit)
        result = await db.execute(query)
        return result.scalars().all()

    async def search_noc_codes(self, db: AsyncSession, vector: List[float], limit: int = 3) -> List[NocCode]:
        """
        Search for NOC codes similar to the given vector.
        """
        query = select(NocCode).order_by(NocCode.embedding.cosine_distance(vector)).limit(limit)
        result = await db.execute(query)
        return result.scalars().all()

    async def search_skills(self, db: AsyncSession, vector: List[float], limit: int = 5) -> List[SkillTaxonomy]:
        """
        Search for skills similar to the given vector.
        """
        query = select(SkillTaxonomy).order_by(SkillTaxonomy.embedding.cosine_distance(vector)).limit(limit)
        result = await db.execute(query)
        return result.scalars().all()

search_service = VectorSearchService()
