from sqlalchemy import String, Integer, Boolean, Numeric, ForeignKey, JSON, DateTime, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base
from datetime import datetime
from typing import Optional, List

class VisiAssessment(Base):
    __tablename__ = "visi_assessments"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    assessment_version: Mapped[Optional[str]] = mapped_column(String(50))
    questions_answers: Mapped[Optional[dict]] = mapped_column(JSON)
    values_scores: Mapped[Optional[dict]] = mapped_column(JSON)
    interests_scores: Mapped[Optional[dict]] = mapped_column(JSON)
    skills_scores: Mapped[Optional[dict]] = mapped_column(JSON)
    income_preferences: Mapped[Optional[dict]] = mapped_column(JSON)
    personality_type: Mapped[Optional[str]] = mapped_column(String(100))
    key_strengths: Mapped[Optional[dict]] = mapped_column(JSON)
    completion_time_minutes: Mapped[Optional[int]] = mapped_column(Integer)
    is_current: Mapped[bool] = mapped_column(Boolean, default=True)
    completed_at: Mapped[datetime] = mapped_column(server_default=func.now())
    
    user = relationship("User", back_populates="assessments")
    recommendations = relationship("CareerRecommendation", back_populates="visi_assessment")
    history_entries = relationship("AssessmentHistory", back_populates="current_assessment")

class AssessmentHistory(Base):
    __tablename__ = "assessment_history"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    assessment_type: Mapped[Optional[str]] = mapped_column(String(100))
    previous_assessment_id: Mapped[Optional[int]] = mapped_column(Integer)
    current_assessment_id: Mapped[int] = mapped_column(ForeignKey("visi_assessments.id"))
    changes_summary: Mapped[Optional[str]] = mapped_column(Text)
    significant_changes: Mapped[Optional[dict]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    
    current_assessment = relationship("VisiAssessment", back_populates="history_entries")

class CareerRecommendation(Base):
    __tablename__ = "career_recommendations"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    visi_assessment_id: Mapped[Optional[int]] = mapped_column(ForeignKey("visi_assessments.id"))
    user_profile_id: Mapped[Optional[int]] = mapped_column(ForeignKey("user_profiles.id"))
    recommendation_type: Mapped[Optional[str]] = mapped_column(String(100))
    recommended_careers: Mapped[Optional[dict]] = mapped_column(JSON)
    match_scores: Mapped[Optional[dict]] = mapped_column(JSON)
    skills_gap_analysis: Mapped[Optional[dict]] = mapped_column(JSON)
    learning_pathways: Mapped[Optional[dict]] = mapped_column(JSON)
    market_insights: Mapped[Optional[dict]] = mapped_column(JSON)
    salary_projections: Mapped[Optional[dict]] = mapped_column(JSON)
    confidence_score: Mapped[Optional[float]] = mapped_column(Numeric)
    processing_time_seconds: Mapped[Optional[float]] = mapped_column(Numeric)
    llm_model_used: Mapped[Optional[str]] = mapped_column(String(100))
    data_sources: Mapped[Optional[dict]] = mapped_column(JSON)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    generated_at: Mapped[datetime] = mapped_column(server_default=func.now())
    
    user = relationship("User", back_populates="recommendations")
    visi_assessment = relationship("VisiAssessment", back_populates="recommendations")
    user_profile = relationship("UserProfile", back_populates="recommendations")
    saved_careers = relationship("SavedCareer", back_populates="recommendation")
    feedback = relationship("UserFeedback", back_populates="recommendation")

class SavedCareer(Base):
    __tablename__ = "saved_careers"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    recommendation_id: Mapped[Optional[int]] = mapped_column(ForeignKey("career_recommendations.id"))
    career_title: Mapped[str] = mapped_column(String(255))
    noc_code: Mapped[Optional[str]] = mapped_column(String(20))
    match_score: Mapped[Optional[float]] = mapped_column(Numeric)
    salary_range: Mapped[Optional[str]] = mapped_column(String(100))
    market_demand: Mapped[Optional[str]] = mapped_column(String(100))
    progress_status: Mapped[Optional[str]] = mapped_column(String(50))
    target_date: Mapped[Optional[datetime]] = mapped_column(DateTime)
    is_primary_goal: Mapped[Optional[bool]] = mapped_column(Boolean)
    saved_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())
    
    user = relationship("User", back_populates="saved_careers")
    recommendation = relationship("CareerRecommendation", back_populates="saved_careers")

class UserFeedback(Base):
    __tablename__ = "user_feedback"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    recommendation_id: Mapped[Optional[int]] = mapped_column(ForeignKey("career_recommendations.id"))
    career_title: Mapped[Optional[str]] = mapped_column(String(255))
    match_score: Mapped[Optional[int]] = mapped_column(Integer)
    salary_range: Mapped[Optional[str]] = mapped_column(String(100))
    market_demand: Mapped[Optional[str]] = mapped_column(String(100))
    saved_at: Mapped[datetime] = mapped_column(server_default=func.now())
    
    user = relationship("User", back_populates="feedback")
    recommendation = relationship("CareerRecommendation", back_populates="feedback")
