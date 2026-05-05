-- 1. Enable pgvector extension (required for AI vector similarity search)
CREATE EXTENSION IF NOT EXISTS vector;

-- ==========================================
-- Phase 1: Geographic Reference Data
-- ==========================================
CREATE TABLE countries (
    id SERIAL PRIMARY KEY,
    country_code VARCHAR(10) UNIQUE,
    country_name VARCHAR(100),
    currency_code VARCHAR(10),
    is_active BOOLEAN DEFAULT TRUE
);

CREATE TABLE provinces (
    id SERIAL PRIMARY KEY,
    country_id INTEGER REFERENCES countries(id),
    province_code VARCHAR(10),
    province_name VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE
);

CREATE TABLE cities (
    id SERIAL PRIMARY KEY,
    province_id INTEGER REFERENCES provinces(id),
    city_name VARCHAR(100),
    population INTEGER,
    cost_of_living_index NUMERIC,
    job_market_score NUMERIC,
    is_active BOOLEAN DEFAULT TRUE
);

-- ==========================================
-- Phase 2: Core User Data
-- ==========================================
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    current_city_id INTEGER REFERENCES cities(id),
    profile_completion NUMERIC DEFAULT 0,
    email_verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);

CREATE TABLE user_sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    session_token TEXT NOT NULL,
    refresh_token TEXT,
    expires_at TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE user_preferences (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    target_job_title VARCHAR(255),
    experience_level VARCHAR(50),
    salary_min NUMERIC,
    salary_max NUMERIC,
    preferred_industries JSONB,
    preferred_work_style VARCHAR(100),
    location_flexibility VARCHAR(100),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ==========================================
-- Phase 3: Job Market Reference Data
-- ==========================================
CREATE TABLE noc_codes (
    id SERIAL PRIMARY KEY,
    noc_code VARCHAR(20) UNIQUE,
    noc_title VARCHAR(255),
    noc_description TEXT,
    skill_level VARCHAR(50),
    skill_type VARCHAR(50),
    main_duties TEXT,
    employment_requirements TEXT,
    related_job_titles JSONB,
    median_salary_cad NUMERIC,
    job_outlook VARCHAR(100),
    embedding VECTOR(768),
    last_updated TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE skills_taxonomy (
    id SERIAL PRIMARY KEY,
    skill_name VARCHAR(100),
    skill_category VARCHAR(100),
    skill_subcategory VARCHAR(100),
    skill_description TEXT,
    skill_synonyms JSONB,
    is_technical BOOLEAN,
    proficiency_levels JSONB,
    learning_time_weeks INTEGER,
    demand_score NUMERIC,
    salary_impact NUMERIC,
    embedding VECTOR(768),
    last_updated TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE job_profiles (
    id SERIAL PRIMARY KEY,
    job_title VARCHAR(255),
    company_name VARCHAR(255),
    job_description TEXT,
    required_skills JSONB,
    preferred_skills JSONB,
    experience_level VARCHAR(50),
    salary_min NUMERIC,
    salary_max NUMERIC,
    salary_currency VARCHAR(10),
    city_id INTEGER REFERENCES cities(id),
    remote_work_option BOOLEAN,
    employment_type VARCHAR(50),
    industry VARCHAR(100),
    noc_code VARCHAR(20) REFERENCES noc_codes(noc_code),
    job_source VARCHAR(100),
    market_demand VARCHAR(100),
    embedding VECTOR(768),
    last_updated TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ==========================================
-- Phase 4: Resume, Profile & VISI Assessment
-- ==========================================
CREATE TABLE user_profiles (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    linkedin_url VARCHAR(255),
    current_job_title VARCHAR(255),
    current_company VARCHAR(255),
    is_current BOOLEAN,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE resume_files (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    file_name VARCHAR(255),
    file_type VARCHAR(50),
    file_size INTEGER,
    raw_text TEXT,
    parsed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE extracted_skills (
    id SERIAL PRIMARY KEY,
    user_profile_id INTEGER REFERENCES user_profiles(id),
    skill_taxonomy_id INTEGER REFERENCES skills_taxonomy(id),
    raw_skill_text VARCHAR(100),
    proficiency_level VARCHAR(50),
    years_experience NUMERIC,
    confidence_score NUMERIC,
    source VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE work_experience (
    id SERIAL PRIMARY KEY,
    user_profile_id INTEGER REFERENCES user_profiles(id),
    company_name VARCHAR(255),
    job_title VARCHAR(255),
    start_date DATE,
    end_date DATE,
    is_current BOOLEAN,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE activity_scores (
    id SERIAL PRIMARY KEY,
    user_profile_id INTEGER REFERENCES user_profiles(id),
    getting_information_score NUMERIC,
    identifying_objects_actions_and_events_score NUMERIC,
    monitoring_processes_materials_or_surroundings_score NUMERIC,
    inspecting_equipment_structures_or_materials_score NUMERIC,
    estimating_quantifiable_characteristics_score NUMERIC,
    judging_qualities_of_objects_services_or_people_score NUMERIC,
    evaluating_information_compliance_with_standards_score NUMERIC,
    processing_information_score NUMERIC,
    analyzing_data_or_information_score NUMERIC,
    making_decisions_and_solving_problems_score NUMERIC,
    thinking_creatively_score NUMERIC,
    updating_and_using_relevant_knowledge_score NUMERIC,
    developing_objectives_and_strategies_score NUMERIC,
    scheduling_work_and_activities_score NUMERIC,
    organizing_planning_and_prioritizing_work_score NUMERIC,
    performing_general_physical_activities_score NUMERIC,
    handling_and_moving_objects_score NUMERIC,
    controlling_machines_and_processes_score NUMERIC,
    working_with_computers_score NUMERIC,
    operating_vehicles_mechanized_devices_or_equipment_score NUMERIC,
    drafting_laying_out_and_specifying_technical_devices_score NUMERIC,
    repairing_and_maintaining_mechanical_equipment_score NUMERIC,
    repairing_and_maintaining_electronic_equipment_score NUMERIC,
    documenting_recording_information_score NUMERIC,
    interpreting_meaning_of_information_for_others_score NUMERIC,
    communicating_with_supervisors_peers_or_subordinates_score NUMERIC,
    communicating_with_people_outside_organization_score NUMERIC,
    establishing_and_maintaining_interpersonal_relationships_score NUMERIC,
    assisting_and_caring_for_others_score NUMERIC,
    selling_or_influencing_others_score NUMERIC,
    resolving_conflicts_and_negotiating_with_others_score NUMERIC,
    performing_for_or_working_directly_with_public_score NUMERIC,
    coordinating_work_and_activities_of_others_score NUMERIC,
    developing_and_building_teams_score NUMERIC,
    training_and_teaching_others_score NUMERIC,
    guiding_directing_and_motivating_subordinates_score NUMERIC,
    coaching_and_developing_others_score NUMERIC,
    providing_consultation_and_advice_to_others_score NUMERIC,
    performing_administrative_activities_score NUMERIC,
    staffing_organizational_units_score NUMERIC,
    monitoring_and_controlling_resources_score NUMERIC,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE education_history (
    id SERIAL PRIMARY KEY,
    user_profile_id INTEGER REFERENCES user_profiles(id),
    institution_name VARCHAR(255),
    degree_type VARCHAR(100),
    field_of_study VARCHAR(100),
    specialization VARCHAR(100),
    start_date DATE,
    end_date DATE,
    gpa NUMERIC,
    math_mark NUMERIC,

    is_current BOOLEAN,
    description TEXT,
    city_id INTEGER REFERENCES cities(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE marks (
    id SERIAL PRIMARY KEY,
    user_profile_id INTEGER REFERENCES user_profiles(id),
    administration_and_management_mark NUMERIC,
    administrative_mark NUMERIC,
    economics_and_accounting_mark NUMERIC,
    sales_and_marketing_mark NUMERIC,
    customer_and_personal_service_mark NUMERIC,
    personnel_and_human_resources_mark NUMERIC,
    production_and_processing_mark NUMERIC,
    food_production_mark NUMERIC,
    computers_and_electronics_mark NUMERIC,
    engineering_and_technology_mark NUMERIC,
    design_mark NUMERIC,
    building_and_construction_mark NUMERIC,
    mechanical_mark NUMERIC,
    mathematics_mark NUMERIC,
    physics_mark NUMERIC,
    chemistry_mark NUMERIC,
    biology_mark NUMERIC,
    psychology_mark NUMERIC,
    sociology_and_anthropology_mark NUMERIC,
    geography_mark NUMERIC,
    medicine_and_dentistry_mark NUMERIC,
    therapy_and_counseling_mark NUMERIC,
    education_and_training_mark NUMERIC,
    english_language_mark NUMERIC,
    foreign_language_mark NUMERIC,
    fine_arts_mark NUMERIC,
    history_and_archaeology_mark NUMERIC,
    philosophy_and_theology_mark NUMERIC,
    public_safety_and_security_mark NUMERIC,
    law_and_government_mark NUMERIC,
    telecommunications_mark NUMERIC,
    communications_and_media_mark NUMERIC,
    transportation_mark NUMERIC,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE visi_assessments (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    assessment_version VARCHAR(50),
    questions_answers JSONB,
    values_scores JSONB,
    interests_scores JSONB,
    skills_scores JSONB,
    income_preferences JSONB,
    personality_type VARCHAR(100),
    key_strengths JSONB,
    completion_time_minutes INTEGER,
    is_current BOOLEAN DEFAULT TRUE,
    completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE assessment_history (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    assessment_type VARCHAR(100),
    previous_assessment_id INTEGER,
    current_assessment_id INTEGER REFERENCES visi_assessments(id),
    changes_summary TEXT,
    significant_changes JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ==========================================
-- Phase 5: Career Recommendations & Feedback
-- ==========================================
CREATE TABLE career_recommendations (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    visi_assessment_id INTEGER REFERENCES visi_assessments(id),
    user_profile_id INTEGER REFERENCES user_profiles(id),
    recommendation_type VARCHAR(100),
    recommended_careers JSONB,
    match_scores JSONB,
    skills_gap_analysis JSONB,
    learning_pathways JSONB,
    market_insights JSONB,
    salary_projections JSONB,
    confidence_score NUMERIC,
    processing_time_seconds NUMERIC,
    llm_model_used VARCHAR(100),
    data_sources JSONB,
    expires_at TIMESTAMP,
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE saved_careers (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    recommendation_id INTEGER REFERENCES career_recommendations(id),
    career_title VARCHAR(255),
    noc_code VARCHAR(20),
    match_score NUMERIC,
    salary_range VARCHAR(100),
    market_demand VARCHAR(100),
    progress_status VARCHAR(50),
    target_date DATE,
    is_primary_goal BOOLEAN,
    saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE user_feedback (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    recommendation_id INTEGER REFERENCES career_recommendations(id),
    career_title VARCHAR(255),
    match_score INTEGER,
    salary_range VARCHAR(100),
    market_demand VARCHAR(100),
    saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ==========================================
-- Vector Search Indexes (HNSW for performance)
-- ==========================================
CREATE INDEX ON noc_codes USING hnsw (embedding vector_cosine_ops);
CREATE INDEX ON skills_taxonomy USING hnsw (embedding vector_cosine_ops);
CREATE INDEX ON job_profiles USING hnsw (embedding vector_cosine_ops);
