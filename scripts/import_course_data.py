import argparse
import csv
import hashlib
import os
from pathlib import Path

import psycopg2
from psycopg2.extras import Json, RealDictCursor


DEFAULT_DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/myapp"
COURSE_JSON_FIELDS = [
    "onet_soc_codes",
    "onet_skill_elements",
    "onet_technology_skills",
    "onet_knowledge_elements",
    "onet_work_activities",
    "onet_task_statements",
]
COURSE_OPTIONAL_FIELDS = [
    "prerequisites",
    "learning_outcomes",
    "program_credential_association",
    "credential_type",
    "certification",
    "course_level",
    "delivery_mode",
    "campus",
    "term_availability",
    "onet_alignment_notes",
]
INSTITUTIONS = {
    "bcit": {
        "name": "British Columbia Institute of Technology",
        "website_url": "https://www.bcit.ca",
        "catalog_url": "https://www.bcit.ca/course_subjects/computer-systems-comp/",
        "city": "Burnaby",
        "province": "British Columbia",
        "country": "Canada",
    },
    "ubc": {
        "name": "University of British Columbia",
        "website_url": "https://www.ubc.ca",
        "catalog_url": "https://vancouver.calendar.ubc.ca/course-descriptions/subject/cpscv",
        "city": "Vancouver",
        "province": "British Columbia",
        "country": "Canada",
    },
    "sfu": {
        "name": "Simon Fraser University",
        "website_url": "https://www.sfu.ca",
        "catalog_url": "https://www.sfu.ca/students/calendar/2026/summer/courses/cmpt/",
        "city": "Burnaby",
        "province": "British Columbia",
        "country": "Canada",
    },
}


def source_hash(row):
    raw = f"{row['course_code']}|{row['title']}|{row.get('description') or ''}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


def read_csv(path):
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def json_value(row, field, default):
    raw = row.get(field)
    if not raw:
        return Json(default)
    import json

    return Json(json.loads(raw))


def normalize_course_row(row, institution_id):
    normalized = dict(row)
    normalized.update({field: row.get(field) or None for field in COURSE_OPTIONAL_FIELDS})
    for field in COURSE_JSON_FIELDS:
        normalized[field] = json_value(row, field, [])
    normalized["sparse_features"] = json_value(row, "sparse_features", {})
    normalized["onet_job_zone"] = row.get("onet_job_zone") or None
    normalized.update(
        {
            "institution_id": institution_id,
            "credits": row.get("credits") or None,
            "source_hash": row.get("source_hash") or source_hash(row),
        }
    )
    return normalized


def upsert_institutions(conn):
    with conn.cursor() as cur:
        for slug, data in INSTITUTIONS.items():
            cur.execute(
                """
                INSERT INTO institutions
                    (slug, name, website_url, catalog_url, city, province, country, created_at, updated_at)
                VALUES
                    (%(slug)s, %(name)s, %(website_url)s, %(catalog_url)s, %(city)s, %(province)s, %(country)s, NOW(), NOW())
                ON CONFLICT (slug) DO UPDATE SET
                    name = EXCLUDED.name,
                    website_url = EXCLUDED.website_url,
                    catalog_url = EXCLUDED.catalog_url,
                    city = EXCLUDED.city,
                    province = EXCLUDED.province,
                    country = EXCLUDED.country,
                    updated_at = NOW()
                """,
                {"slug": slug, **data},
            )


def load_lookup(conn, table, key_column):
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(f"SELECT id, {key_column} FROM {table}")
        return {row[key_column]: row["id"] for row in cur.fetchall()}


def upsert_courses(conn, course_rows):
    institutions = load_lookup(conn, "institutions", "slug")
    with conn.cursor() as cur:
        for row in course_rows:
            institution_id = institutions[row["institution_slug"]]
            cur.execute(
                """
                INSERT INTO courses (
                    institution_id,
                    course_code,
                    subject_code,
                    course_number,
                    title,
                    description,
                    credits,
                    prerequisites,
                    learning_outcomes,
                    program_credential_association,
                    credential_type,
                    certification,
                    course_level,
                    delivery_mode,
                    campus,
                    term_availability,
                    onet_soc_codes,
                    onet_skill_elements,
                    onet_technology_skills,
                    onet_knowledge_elements,
                    onet_work_activities,
                    onet_task_statements,
                    onet_job_zone,
                    onet_alignment_notes,
                    sparse_features,
                    course_url,
                    source_url,
                    source_hash,
                    last_seen_at,
                    is_active,
                    created_at,
                    updated_at
                )
                VALUES (
                    %(institution_id)s,
                    %(course_code)s,
                    %(subject_code)s,
                    %(course_number)s,
                    %(title)s,
                    %(description)s,
                    %(credits)s,
                    %(prerequisites)s,
                    %(learning_outcomes)s,
                    %(program_credential_association)s,
                    %(credential_type)s,
                    %(certification)s,
                    %(course_level)s,
                    %(delivery_mode)s,
                    %(campus)s,
                    %(term_availability)s,
                    %(onet_soc_codes)s,
                    %(onet_skill_elements)s,
                    %(onet_technology_skills)s,
                    %(onet_knowledge_elements)s,
                    %(onet_work_activities)s,
                    %(onet_task_statements)s,
                    %(onet_job_zone)s,
                    %(onet_alignment_notes)s,
                    %(sparse_features)s,
                    %(course_url)s,
                    %(source_url)s,
                    %(source_hash)s,
                    NOW(),
                    TRUE,
                    NOW(),
                    NOW()
                )
                ON CONFLICT (institution_id, course_code) DO UPDATE SET
                    subject_code = EXCLUDED.subject_code,
                    course_number = EXCLUDED.course_number,
                    title = EXCLUDED.title,
                    description = EXCLUDED.description,
                    credits = EXCLUDED.credits,
                    prerequisites = EXCLUDED.prerequisites,
                    learning_outcomes = EXCLUDED.learning_outcomes,
                    program_credential_association = EXCLUDED.program_credential_association,
                    credential_type = EXCLUDED.credential_type,
                    certification = EXCLUDED.certification,
                    course_level = EXCLUDED.course_level,
                    delivery_mode = EXCLUDED.delivery_mode,
                    campus = EXCLUDED.campus,
                    term_availability = EXCLUDED.term_availability,
                    onet_soc_codes = EXCLUDED.onet_soc_codes,
                    onet_skill_elements = EXCLUDED.onet_skill_elements,
                    onet_technology_skills = EXCLUDED.onet_technology_skills,
                    onet_knowledge_elements = EXCLUDED.onet_knowledge_elements,
                    onet_work_activities = EXCLUDED.onet_work_activities,
                    onet_task_statements = EXCLUDED.onet_task_statements,
                    onet_job_zone = EXCLUDED.onet_job_zone,
                    onet_alignment_notes = EXCLUDED.onet_alignment_notes,
                    sparse_features = EXCLUDED.sparse_features,
                    course_url = EXCLUDED.course_url,
                    source_url = EXCLUDED.source_url,
                    source_hash = EXCLUDED.source_hash,
                    last_seen_at = NOW(),
                    is_active = TRUE,
                    updated_at = NOW()
                """,
                normalize_course_row(row, institution_id),
            )


def upsert_mappings(conn, mapping_rows):
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT c.id, i.slug, c.course_code
            FROM courses c
            JOIN institutions i ON i.id = c.institution_id
            """
        )
        courses = {(row["slug"], row["course_code"]): row["id"] for row in cur.fetchall()}
        cur.execute("SELECT id, skill_name FROM skills_taxonomy")
        skills = {row["skill_name"]: row["id"] for row in cur.fetchall()}

    with conn.cursor() as cur:
        for row in mapping_rows:
            course_id = courses[(row["institution_slug"], row["course_code"])]
            skill_id = skills[row["skill_name"]]
            cur.execute(
                """
                INSERT INTO course_skill_mapping (
                    course_id,
                    skill_taxonomy_id,
                    confidence_score,
                    mapping_source,
                    rationale,
                    created_at,
                    updated_at
                )
                VALUES (%s, %s, %s, %s, %s, NOW(), NOW())
                ON CONFLICT (course_id, skill_taxonomy_id) DO UPDATE SET
                    confidence_score = EXCLUDED.confidence_score,
                    mapping_source = EXCLUDED.mapping_source,
                    rationale = EXCLUDED.rationale,
                    updated_at = NOW()
                """,
                (
                    course_id,
                    skill_id,
                    row["confidence_score"],
                    row["mapping_source"],
                    row["rationale"],
                ),
            )


def main():
    parser = argparse.ArgumentParser(description="Import institution course catalog seed data.")
    parser.add_argument("--courses", default="data/course_catalog_mvp.csv")
    parser.add_argument("--mappings", default="data/course_skill_mapping_mvp.csv")
    parser.add_argument("--database-url", default=os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL))
    args = parser.parse_args()

    course_rows = read_csv(Path(args.courses))
    mapping_rows = read_csv(Path(args.mappings))

    with psycopg2.connect(args.database_url) as conn:
        upsert_institutions(conn)
        upsert_courses(conn, course_rows)
        upsert_mappings(conn, mapping_rows)

    print(f"Imported {len(course_rows)} courses and {len(mapping_rows)} course-skill mappings.")


if __name__ == "__main__":
    main()
