from sqlalchemy import String, Integer, Boolean, Numeric, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base

class Country(Base):
    __tablename__ = "countries"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    country_code: Mapped[str] = mapped_column(String(10), unique=True)
    country_name: Mapped[str] = mapped_column(String(100))
    currency_code: Mapped[str] = mapped_column(String(10))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    provinces = relationship("Province", back_populates="country")

class Province(Base):
    __tablename__ = "provinces"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    country_id: Mapped[int] = mapped_column(ForeignKey("countries.id"))
    province_code: Mapped[str] = mapped_column(String(10))
    province_name: Mapped[str] = mapped_column(String(100))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    country = relationship("Country", back_populates="provinces")
    cities = relationship("City", back_populates="province")

class City(Base):
    __tablename__ = "cities"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    province_id: Mapped[int] = mapped_column(ForeignKey("provinces.id"))
    city_name: Mapped[str] = mapped_column(String(100))
    population: Mapped[int] = mapped_column(Integer, nullable=True)
    cost_of_living_index: Mapped[float] = mapped_column(Numeric, nullable=True)
    job_market_score: Mapped[float] = mapped_column(Numeric, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    province = relationship("Province", back_populates="cities")
    users = relationship("User", back_populates="current_city")
    job_profiles = relationship("JobProfile", back_populates="city")
    education_histories = relationship("EducationHistory", back_populates="city")
