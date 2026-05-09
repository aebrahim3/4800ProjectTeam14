from sqlalchemy import String, Integer, Boolean, Numeric, ForeignKey, JSON, DateTime, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin
from datetime import datetime
from typing import Optional, List

class User(Base, TimestampMixin):
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    first_name: Mapped[Optional[str]] = mapped_column(String(100))
    last_name: Mapped[Optional[str]] = mapped_column(String(100))
    current_city_id: Mapped[Optional[int]] = mapped_column(ForeignKey("cities.id"))
    profile_completion: Mapped[float] = mapped_column(Numeric, default=0)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    current_city = relationship("City", back_populates="users")
    sessions = relationship("UserSession", back_populates="user")
    preferences = relationship("UserPreference", back_populates="user", uselist=False)
    profiles = relationship("UserProfile", back_populates="user")
    resumes = relationship("ResumeFile", back_populates="user")
    assessments = relationship("VisiAssessment", back_populates="user")
    recommendations = relationship("CareerRecommendation", back_populates="user")
    saved_careers = relationship("SavedCareer", back_populates="user")
    feedback = relationship("UserFeedback", back_populates="user")

class UserSession(Base):
    __tablename__ = "user_sessions"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    session_token: Mapped[str] = mapped_column(Text, nullable=False)
    refresh_token: Mapped[Optional[str]] = mapped_column(Text)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    
    user = relationship("User", back_populates="sessions")

class UserPreference(Base):
    __tablename__ = "user_preferences"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    target_job_title: Mapped[Optional[str]] = mapped_column(String(255))
    experience_level: Mapped[Optional[str]] = mapped_column(String(50))
    salary_min: Mapped[Optional[float]] = mapped_column(Numeric)
    salary_max: Mapped[Optional[float]] = mapped_column(Numeric)
    preferred_industries: Mapped[Optional[dict]] = mapped_column(JSON)
    preferred_work_style: Mapped[Optional[str]] = mapped_column(String(100))
    location_flexibility: Mapped[Optional[str]] = mapped_column(String(100))
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())
    
    user = relationship("User", back_populates="preferences")

class UserProfile(Base, TimestampMixin):
    __tablename__ = "user_profiles"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    linkedin_url: Mapped[Optional[str]] = mapped_column(String(255))
    current_job_title: Mapped[Optional[str]] = mapped_column(String(255))
    current_company: Mapped[Optional[str]] = mapped_column(String(255))
    is_current: Mapped[bool] = mapped_column(Boolean, default=True)
    
    user = relationship("User", back_populates="profiles")
    skills = relationship("ExtractedSkill", back_populates="user_profile")
    work_experiences = relationship("WorkExperience", back_populates="user_profile")
    education_histories = relationship("EducationHistory", back_populates="user_profile")
    recommendations = relationship("CareerRecommendation", back_populates="user_profile")

class ResumeFile(Base):
    __tablename__ = "resume_files"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    file_name: Mapped[str] = mapped_column(String(255))
    file_type: Mapped[str] = mapped_column(String(50))
    file_size: Mapped[int] = mapped_column(Integer)
    raw_text: Mapped[Optional[str]] = mapped_column(Text)
    parsed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    
    user = relationship("User", back_populates="resumes")
