from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models.user import User, UserProfile
from app.models.assessment import VisiAssessment
from app.models.market import JobProfile, NocCode, SkillTaxonomy
from typing import List, Dict, Any

class ContextAssemblyService:
    async def get_user_context(self, db: AsyncSession, user_id: int) -> Dict[str, Any]:
        """
        Fetch all relevant user information for context.
        """
        # Fetch user with profiles and preferences
        query = select(User).where(User.id == user_id).options(
            selectinload(User.profiles),
            selectinload(User.preferences),
            selectinload(User.assessments)
        )
        result = await db.execute(query)
        user = result.scalar_one_or_none()
        
        if not user:
            return {}

        # Get latest assessment
        latest_assessment = next((a for a in user.assessments if a.is_current), None)
        
        # Get latest profile
        latest_profile = next((p for p in user.profiles if p.is_current), None)
        if latest_profile:
            # Load relationships for profile
            profile_query = select(UserProfile).where(UserProfile.id == latest_profile.id).options(
                selectinload(UserProfile.skills),
                selectinload(UserProfile.work_experiences),
                selectinload(UserProfile.education_histories)
            )
            profile_result = await db.execute(profile_query)
            latest_profile = profile_result.scalar_one()

        return {
            "user": {
                "first_name": user.first_name,
                "last_name": user.last_name,
                "email": user.email,
            },
            "preferences": {
                "target_job_title": user.preferences.target_job_title if user.preferences else None,
                "salary_min": float(user.preferences.salary_min) if user.preferences and user.preferences.salary_min else None,
                "salary_max": float(user.preferences.salary_max) if user.preferences and user.preferences.salary_max else None,
                "location_flexibility": user.preferences.location_flexibility if user.preferences else None,
            } if user.preferences else {},
            "assessment": {
                "personality_type": latest_assessment.personality_type,
                "key_strengths": latest_assessment.key_strengths,
                "interests_scores": latest_assessment.interests_scores,
            } if latest_assessment else {},
            "profile": {
                "current_job_title": latest_profile.current_job_title,
                "current_company": latest_profile.current_company,
                "skills": [s.raw_skill_text for s in latest_profile.skills],
                "experience": [
                    {
                        "title": exp.job_title,
                        "company": exp.company_name,
                        "description": exp.description
                    } for exp in latest_profile.work_experiences
                ],
                "education": [
                    {
                        "institution": edu.institution_name,
                        "degree": edu.degree_type,
                        "field": edu.field_of_study
                    } for edu in latest_profile.education_histories
                ]
            } if latest_profile else {}
        }

    def format_search_results(self, jobs: List[JobProfile], nocs: List[NocCode], skills: List[SkillTaxonomy]) -> str:
        """
        Format the search results into a readable Markdown string for the LLM.
        """
        context_str = "## Relevant Job Market Data\n\n"
        
        context_str += "### Top Job Matches\n"
        for i, job in enumerate(jobs):
            context_str += f"{i+1}. **{job.job_title}** at {job.company_name}\n"
            context_str += f"   - Description: {job.job_description[:200]}...\n"
            context_str += f"   - Salary: {job.salary_min} - {job.salary_max} {job.salary_currency}\n"
            context_str += f"   - Required Skills: {job.required_skills}\n\n"
            
        context_str += "### Related Occupations (NOC)\n"
        for i, noc in enumerate(nocs):
            context_str += f"{i+1}. **{noc.noc_title}** ({noc.noc_code})\n"
            context_str += f"   - Outlook: {noc.job_outlook}\n"
            context_str += f"   - Median Salary: {noc.median_salary_cad} CAD\n"
            context_str += f"   - Main Duties: {noc.main_duties[:200]}...\n\n"
            
        context_str += "### Key Skills to Consider\n"
        for i, skill in enumerate(skills):
            context_str += f"{i+1}. **{skill.skill_name}**\n"
            context_str += f"   - Description: {skill.skill_description}\n"
            context_str += f"   - Salary Impact: {skill.salary_impact}\n"
            context_str += f"   - Estimated Learning Time: {skill.learning_time_weeks} weeks\n\n"
            
        return context_str

context_service = ContextAssemblyService()
