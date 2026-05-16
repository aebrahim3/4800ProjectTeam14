-- ==========================================
-- Phase 7: OaSIS Data for Job Matching
-- ==========================================

-- 1. Enable pgvector extension if not already enabled
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. Create base occupations table
CREATE TABLE IF NOT EXISTS oasis_occupations (
    oasis_code VARCHAR(20) PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    core_competencies JSONB,
    interests JSONB
);

-- 3. Create vectors table for different domains
-- The combined vector is sized to hold all the numerical dimensions:
-- Abilities (52) + Skills (33) + Work Context (66)
-- + Knowledge (44) + Personal Attributes (13) + Work Activities (39) = 247
CREATE TABLE IF NOT EXISTS oasis_occupation_vectors (
    oasis_code VARCHAR(20) PRIMARY KEY REFERENCES oasis_occupations(oasis_code),
    abilities_vector VECTOR(52),
    skills_vector VECTOR(33),
    work_context_vector VECTOR(66),
    knowledge_vector VECTOR(44),
    personal_attributes_vector VECTOR(13),
    work_activities_vector VECTOR(39),
    combined_vector VECTOR(247),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. Create an HNSW index on the combined_vector for efficient similarity searches
-- Using cosine distance (vector_cosine_ops) which is standard for embedding comparison
CREATE INDEX IF NOT EXISTS oasis_combined_vector_idx ON oasis_occupation_vectors USING hnsw (combined_vector vector_cosine_ops);
