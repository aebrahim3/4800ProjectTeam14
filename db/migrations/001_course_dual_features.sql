-- Sub-task 3 migration: course dual-track dense/sparse features.
-- Existing 768-dim vectors are cleared because bge-large-en-v1.5 outputs 1024 dimensions.

CREATE EXTENSION IF NOT EXISTS vector;

DROP INDEX IF EXISTS noc_codes_embedding_idx;
DROP INDEX IF EXISTS skills_taxonomy_embedding_idx;
DROP INDEX IF EXISTS job_profiles_embedding_idx;
DROP INDEX IF EXISTS idx_courses_embedding;

DO $$
DECLARE
    target_table TEXT;
    current_type TEXT;
BEGIN
    FOR target_table IN
        SELECT unnest(ARRAY['noc_codes', 'skills_taxonomy', 'courses', 'job_profiles']::TEXT[])
    LOOP
        SELECT format_type(a.atttypid, a.atttypmod)
        INTO current_type
        FROM pg_attribute a
        JOIN pg_class c ON c.oid = a.attrelid
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'public'
          AND c.relname = target_table
          AND a.attname = 'embedding'
          AND NOT a.attisdropped;

        IF current_type IS NOT NULL AND current_type <> 'vector(1024)' THEN
            EXECUTE format(
                'ALTER TABLE %I ALTER COLUMN embedding TYPE vector(1024) USING NULL',
                target_table
            );
        END IF;
    END LOOP;
END $$;

ALTER TABLE courses
    ADD COLUMN IF NOT EXISTS embedding_model VARCHAR(100),
    ADD COLUMN IF NOT EXISTS embedding_updated_at TIMESTAMP,
    ADD COLUMN IF NOT EXISTS sparse_features_updated_at TIMESTAMP;

ALTER TABLE course_skill_mapping
    ADD COLUMN IF NOT EXISTS feature_key VARCHAR(100),
    ADD COLUMN IF NOT EXISTS source_fields JSONB DEFAULT '[]'::jsonb,
    ADD COLUMN IF NOT EXISTS evidence_text TEXT,
    ADD COLUMN IF NOT EXISTS matched_aliases JSONB DEFAULT '[]'::jsonb;

UPDATE course_skill_mapping csm
SET feature_key = trim(both '_' from lower(regexp_replace(st.skill_name, '[^A-Za-z0-9]+', '_', 'g')))
FROM skills_taxonomy st
WHERE csm.skill_taxonomy_id = st.id
  AND csm.feature_key IS NULL;

UPDATE course_skill_mapping csm
SET source_fields = '["course_skill_mapping"]'::jsonb
WHERE csm.source_fields IS NULL;

UPDATE course_skill_mapping csm
SET matched_aliases = jsonb_build_array(st.skill_name)
FROM skills_taxonomy st
WHERE csm.skill_taxonomy_id = st.id
  AND (csm.matched_aliases IS NULL OR csm.matched_aliases = '[]'::jsonb);

CREATE INDEX IF NOT EXISTS noc_codes_embedding_idx
    ON noc_codes USING hnsw (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS skills_taxonomy_embedding_idx
    ON skills_taxonomy USING hnsw (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS job_profiles_embedding_idx
    ON job_profiles USING hnsw (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS idx_courses_embedding
    ON courses USING hnsw (embedding vector_cosine_ops);
