from sqlalchemy import String, Integer, Boolean, Numeric, ForeignKey, JSON, DateTime, Text, func, Date
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector
from app.models.base import Base
from datetime import datetime, date
from typing import Optional, List

class NocCode(Base):
    __tablename__ = "noc_codes"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    noc_code: Mapped[str] = mapped_column(String(20), unique=True)
    noc_title: Mapped[str] = mapped_column(String(255))
    noc_description: Mapped[Optional[str]] = mapped_column(Text)
    skill_level: Mapped[Optional[str]] = mapped_column(String(50))
    skill_type: Mapped[Optional[str]] = mapped_column(String(50))
    main_duties: Mapped[Optional[str]] = mapped_column(Text)
    employment_requirements: Mapped[Optional[str]] = mapped_column(Text)
    related_job_titles: Mapped[Optional[dict]] = mapped_column(JSON)
    median_salary_cad: Mapped[Optional[float]] = mapped_column(Numeric)
    job_outlook: Mapped[Optional[str]] = mapped_column(String(100))
    embedding: Mapped[Optional[List[float]]] = mapped_column(Vector(768))
    last_updated: Mapped[Optional[datetime]] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    
    job_profiles = relationship("JobProfile", back_populates="noc")

class SkillTaxonomy(Base):
    __tablename__ = "skills_taxonomy"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    skill_name: Mapped[str] = mapped_column(String(100))
    skill_category: Mapped[Optional[str]] = mapped_column(String(100))
    skill_subcategory: Mapped[Optional[str]] = mapped_column(String(100))
    skill_description: Mapped[Optional[str]] = mapped_column(Text)
    skill_synonyms: Mapped[Optional[dict]] = mapped_column(JSON)
    is_technical: Mapped[Optional[bool]] = mapped_column(Boolean)
    proficiency_levels: Mapped[Optional[dict]] = mapped_column(JSON)
    learning_time_weeks: Mapped[Optional[int]] = mapped_column(Integer)
    demand_score: Mapped[Optional[float]] = mapped_column(Numeric)
    salary_impact: Mapped[Optional[float]] = mapped_column(Numeric)
    embedding: Mapped[Optional[List[float]]] = mapped_column(Vector(768))
    last_updated: Mapped[Optional[datetime]] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    
    extracted_skills = relationship("ExtractedSkill", back_populates="skill_taxonomy")

class JobProfile(Base):
    __tablename__ = "job_profiles"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    job_title: Mapped[str] = mapped_column(String(255))
    company_name: Mapped[str] = mapped_column(String(255))
    job_description: Mapped[Optional[str]] = mapped_column(Text)
    required_skills: Mapped[Optional[dict]] = mapped_column(JSON)
    preferred_skills: Mapped[Optional[dict]] = mapped_column(JSON)
    experience_level: Mapped[Optional[str]] = mapped_column(String(50))
    salary_min: Mapped[Optional[float]] = mapped_column(Numeric)
    salary_max: Mapped[Optional[float]] = mapped_column(Numeric)
    salary_currency: Mapped[str] = mapped_column(String(10), default="CAD")
    city_id: Mapped[Optional[int]] = mapped_column(ForeignKey("cities.id"))
    remote_work_option: Mapped[Optional[bool]] = mapped_column(Boolean)
    employment_type: Mapped[Optional[str]] = mapped_column(String(50))
    industry: Mapped[Optional[str]] = mapped_column(String(100))
    noc_code: Mapped[Optional[str]] = mapped_column(ForeignKey("noc_codes.noc_code"))
    job_source: Mapped[Optional[str]] = mapped_column(String(100))
    market_demand: Mapped[Optional[str]] = mapped_column(String(100))
    embedding: Mapped[Optional[List[float]]] = mapped_column(Vector(768))
    last_updated: Mapped[Optional[datetime]] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    
    city = relationship("City", back_populates="job_profiles")
    noc = relationship("NocCode", back_populates="job_profiles")

class ExtractedSkill(Base):
    __tablename__ = "extracted_skills"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    user_profile_id: Mapped[int] = mapped_column(ForeignKey("user_profiles.id"))
    skill_taxonomy_id: Mapped[Optional[int]] = mapped_column(ForeignKey("skills_taxonomy.id"))
    raw_skill_text: Mapped[str] = mapped_column(String(100))
    proficiency_level: Mapped[Optional[str]] = mapped_column(String(50))
    years_experience: Mapped[Optional[float]] = mapped_column(Numeric)
    confidence_score: Mapped[Optional[float]] = mapped_column(Numeric)
    source: Mapped[Optional[str]] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    
    user_profile = relationship("UserProfile", back_populates="skills")
    skill_taxonomy = relationship("SkillTaxonomy", back_populates="extracted_skills")

class WorkExperience(Base):
    __tablename__ = "work_experience"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    user_profile_id: Mapped[int] = mapped_column(ForeignKey("user_profiles.id"))
    company_name: Mapped[str] = mapped_column(String(255))
    job_title: Mapped[str] = mapped_column(String(255))
    start_date: Mapped[Optional[date]] = mapped_column(Date)
    end_date: Mapped[Optional[date]] = mapped_column(Date)
    is_current: Mapped[Optional[bool]] = mapped_column(Boolean)
    description: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    
    user_profile = relationship("UserProfile", back_populates="work_experiences")

class EducationHistory(Base):
    __tablename__ = "education_history"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    user_profile_id: Mapped[int] = mapped_column(ForeignKey("user_profiles.id"))
    institution_name: Mapped[str] = mapped_column(String(255))
    degree_type: Mapped[Optional[str]] = mapped_column(String(100))
    field_of_study: Mapped[Optional[str]] = mapped_column(String(100))
    specialization: Mapped[Optional[str]] = mapped_column(String(100))
    start_date: Mapped[Optional[date]] = mapped_column(Date)
    end_date: Mapped[Optional[date]] = mapped_column(Date)
    gpa: Mapped[Optional[float]] = mapped_column(Numeric)
    is_current: Mapped[Optional[bool]] = mapped_column(Boolean)
    description: Mapped[Optional[str]] = mapped_column(Text)
    city_id: Mapped[Optional[int]] = mapped_column(ForeignKey("cities.id"))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    
    user_profile = relationship("UserProfile", back_populates="education_histories")
    city = relationship("City", back_populates="education_histories")
