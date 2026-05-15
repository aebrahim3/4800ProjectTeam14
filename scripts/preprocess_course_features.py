import argparse
import json
import math
import os
import re
from dataclasses import dataclass, replace
from functools import lru_cache

try:
    import psycopg2
    from psycopg2.extras import Json, RealDictCursor
except ImportError:
    psycopg2 = None
    Json = None
    RealDictCursor = None


DEFAULT_DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/careerMatchingEngine"
DEFAULT_MODEL_NAME = "BAAI/bge-large-en-v1.5"
DEFAULT_EMBEDDING_DIMENSION = 1024
DEFAULT_BATCH_SIZE = 16
KEYWORD_CONFIDENCE = 0.65
COURSE_TEXT_FIELDS = (
    "title",
    "description",
    "prerequisites",
    "learning_outcomes",
    "program_credential_association",
    "certification",
)


@dataclass(frozen=True)
class TaxonomySkill:
    id: int
    name: str
    feature_key: str
    aliases: tuple[str, ...]


def normalize_feature_key(value: str) -> str:
    key = re.sub(r"[^A-Za-z0-9]+", "_", (value or "").strip().lower())
    return key.strip("_")


def unique_preserving_order(values):
    seen = set()
    result = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result


def coerce_synonyms(raw):
    if raw is None:
        return []
    if isinstance(raw, list):
        return raw
    if isinstance(raw, tuple):
        return list(raw)
    if isinstance(raw, str):
        stripped = raw.strip()
        if not stripped:
            return []
        try:
            parsed = json.loads(stripped)
        except json.JSONDecodeError:
            return [stripped]
        if isinstance(parsed, list):
            return parsed
        return [stripped]
    return []


def build_taxonomy_skill(row) -> TaxonomySkill:
    skill_id = int(row["id"])
    skill_name = str(row["skill_name"]).strip()
    feature_key = normalize_feature_key(skill_name) or f"skill_{skill_id}"
    aliases = [skill_name]
    aliases.extend(str(alias).strip() for alias in coerce_synonyms(row.get("skill_synonyms")))
    aliases = [alias for alias in aliases if alias]
    return TaxonomySkill(
        id=skill_id,
        name=skill_name,
        feature_key=feature_key,
        aliases=tuple(unique_preserving_order(aliases)),
    )


def ensure_unique_feature_keys(skills):
    seen = {}
    result = []
    for skill in skills:
        if skill.feature_key in seen:
            result.append(replace(skill, feature_key=f"{skill.feature_key}_{skill.id}"))
        else:
            result.append(skill)
            seen[skill.feature_key] = skill.id
    return result


def load_taxonomy(conn):
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT id, skill_name, skill_synonyms
            FROM skills_taxonomy
            ORDER BY skill_name, id
            """
        )
        skills = [build_taxonomy_skill(row) for row in cur.fetchall()]
    return ensure_unique_feature_keys(skills)


def build_course_text(course):
    parts = []
    for field in COURSE_TEXT_FIELDS:
        value = course.get(field)
        if value:
            label = field.replace("_", " ").title()
            parts.append(f"{label}: {value}")
    return "\n".join(parts)


@lru_cache(maxsize=4096)
def compile_alias_pattern(alias):
    tokens = re.split(r"\s+", alias.strip())
    escaped = r"\s+".join(re.escape(token) for token in tokens if token)
    return re.compile(rf"(?<![A-Za-z0-9]){escaped}(?![A-Za-z0-9])", re.IGNORECASE)


def extract_evidence(text, match, window=80):
    start = max(0, match.start() - window)
    end = min(len(text), match.end() + window)
    prefix = "..." if start > 0 else ""
    suffix = "..." if end < len(text) else ""
    excerpt = re.sub(r"\s+", " ", text[start:end]).strip()
    return f"{prefix}{excerpt}{suffix}"


def find_text_skill_matches(course, taxonomy):
    matches = {}
    for field in COURSE_TEXT_FIELDS:
        text = str(course.get(field) or "")
        if not text:
            continue
        for skill in taxonomy:
            for alias in skill.aliases:
                match = compile_alias_pattern(alias).search(text)
                if not match:
                    continue
                info = matches.setdefault(
                    skill.id,
                    {
                        "source_fields": set(),
                        "matched_aliases": set(),
                        "evidence_text": None,
                    },
                )
                info["source_fields"].add(field)
                info["matched_aliases"].add(alias)
                if info["evidence_text"] is None:
                    info["evidence_text"] = extract_evidence(text, match)
                break

    normalized = {}
    for skill_id, info in matches.items():
        normalized[skill_id] = {
            "source_fields": sorted(info["source_fields"]),
            "matched_aliases": sorted(info["matched_aliases"]),
            "evidence_text": info["evidence_text"],
        }
    return normalized


def build_sparse_feature_payload(course, taxonomy, existing_mappings=None):
    existing_mappings = existing_mappings or {}
    text_matches = find_text_skill_matches(course, taxonomy)
    features = {}
    mapping_records = []

    for skill in sorted(taxonomy, key=lambda item: item.feature_key):
        text_match = text_matches.get(skill.id)
        existing_mapping = existing_mappings.get(skill.id)
        is_hit = bool(text_match or existing_mapping)
        features[skill.feature_key] = 1 if is_hit else 0

        if not is_hit:
            continue

        source_fields = []
        matched_aliases = []
        evidence_text = None
        confidence_score = KEYWORD_CONFIDENCE
        mapping_source = "keyword"
        rationale = "Keyword match in course text."

        if existing_mapping:
            source_fields.append("course_skill_mapping")
            matched_aliases.append(skill.name)
            evidence_text = existing_mapping.get("rationale")
            confidence_score = existing_mapping.get("confidence_score") or confidence_score
            mapping_source = existing_mapping.get("mapping_source") or mapping_source
            rationale = existing_mapping.get("rationale") or rationale

        if text_match:
            source_fields.extend(text_match["source_fields"])
            matched_aliases.extend(text_match["matched_aliases"])
            evidence_text = text_match.get("evidence_text") or evidence_text

        mapping_records.append(
            {
                "course_id": int(course["id"]),
                "skill_taxonomy_id": skill.id,
                "confidence_score": float(confidence_score),
                "mapping_source": mapping_source,
                "feature_key": skill.feature_key,
                "source_fields": unique_preserving_order(source_fields),
                "evidence_text": evidence_text,
                "matched_aliases": unique_preserving_order(matched_aliases),
                "rationale": rationale,
            }
        )

    return features, mapping_records


def validate_embedding_vector(vector, expected_dimension=DEFAULT_EMBEDDING_DIMENSION):
    values = [float(value) for value in vector]
    if len(values) != expected_dimension:
        raise ValueError(f"Expected embedding dimension {expected_dimension}, got {len(values)}")
    if any(not math.isfinite(value) for value in values):
        raise ValueError("Embedding contains non-finite values")
    return values


def format_pgvector(vector):
    return "[" + ",".join(f"{value:.10g}" for value in vector) + "]"


def fetch_courses(conn, course_id=None, limit=None):
    query = """
        SELECT
            id,
            title,
            description,
            prerequisites,
            learning_outcomes,
            program_credential_association,
            certification
        FROM courses
        WHERE is_active = TRUE
    """
    params = []

    if course_id is not None:
        query += " AND id = %s"
        params.append(course_id)

    query += " ORDER BY id"

    if limit is not None:
        query += " LIMIT %s"
        params.append(limit)

    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(query, params)
        return list(cur.fetchall())


def load_existing_mappings(conn, course_ids):
    if not course_ids:
        return {}

    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT
                csm.course_id,
                csm.skill_taxonomy_id,
                csm.confidence_score,
                csm.mapping_source,
                csm.rationale
            FROM course_skill_mapping csm
            WHERE csm.course_id = ANY(%s)
            """,
            (list(course_ids),),
        )
        rows = cur.fetchall()

    mappings = {}
    for row in rows:
        course_mappings = mappings.setdefault(row["course_id"], {})
        course_mappings[row["skill_taxonomy_id"]] = row
    return mappings


def write_sparse_features(conn, course_id, features, mapping_records):
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE courses
            SET sparse_features = %s,
                sparse_features_updated_at = NOW(),
                updated_at = NOW()
            WHERE id = %s
            """,
            (Json(features), course_id),
        )

        for record in mapping_records:
            cur.execute(
                """
                INSERT INTO course_skill_mapping (
                    course_id,
                    skill_taxonomy_id,
                    confidence_score,
                    mapping_source,
                    feature_key,
                    source_fields,
                    evidence_text,
                    matched_aliases,
                    rationale,
                    created_at,
                    updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                ON CONFLICT (course_id, skill_taxonomy_id) DO UPDATE SET
                    feature_key = EXCLUDED.feature_key,
                    source_fields = EXCLUDED.source_fields,
                    evidence_text = COALESCE(EXCLUDED.evidence_text, course_skill_mapping.evidence_text),
                    matched_aliases = EXCLUDED.matched_aliases,
                    updated_at = NOW()
                """,
                (
                    record["course_id"],
                    record["skill_taxonomy_id"],
                    record["confidence_score"],
                    record["mapping_source"],
                    record["feature_key"],
                    Json(record["source_fields"]),
                    record["evidence_text"],
                    Json(record["matched_aliases"]),
                    record["rationale"],
                ),
            )


def load_embedding_model(model_name):
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        raise RuntimeError(
            "Install sentence-transformers and torch to generate dense embeddings."
        ) from exc
    return SentenceTransformer(model_name)


def iter_batches(values, batch_size):
    for start in range(0, len(values), batch_size):
        yield values[start : start + batch_size]


def encode_course_batch(model, courses, batch_size):
    texts = [build_course_text(course) for course in courses]
    return model.encode(
        texts,
        batch_size=batch_size,
        normalize_embeddings=True,
        show_progress_bar=len(texts) > batch_size,
    )


def write_embedding(conn, course_id, vector, model_name):
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE courses
            SET embedding = %s::vector,
                embedding_model = %s,
                embedding_updated_at = NOW(),
                updated_at = NOW()
            WHERE id = %s
            """,
            (format_pgvector(vector), model_name, course_id),
        )


def preprocess_course_features(
    database_url,
    model_name=DEFAULT_MODEL_NAME,
    batch_size=DEFAULT_BATCH_SIZE,
    limit=None,
    course_id=None,
    skip_embeddings=False,
    skip_sparse=False,
    dry_run=False,
):
    if psycopg2 is None:
        raise RuntimeError("Install psycopg2-binary to preprocess database-backed course features.")

    with psycopg2.connect(database_url) as conn:
        courses = fetch_courses(conn, course_id=course_id, limit=limit)
        if not courses:
            print("No active courses found.")
            return {"courses": 0, "sparse_updates": 0, "embedding_updates": 0}

        sparse_updates = 0
        if not skip_sparse:
            taxonomy = load_taxonomy(conn)
            existing_mappings = load_existing_mappings(conn, [course["id"] for course in courses])
            for course in courses:
                features, mapping_records = build_sparse_feature_payload(
                    course,
                    taxonomy,
                    existing_mappings.get(course["id"], {}),
                )
                if dry_run:
                    active_keys = [key for key, value in features.items() if value == 1]
                    print(f"DRY RUN sparse course_id={course['id']} active_features={active_keys}")
                else:
                    write_sparse_features(conn, course["id"], features, mapping_records)
                sparse_updates += 1

        embedding_updates = 0
        if not skip_embeddings:
            model = load_embedding_model(model_name)
            for course_batch in iter_batches(courses, batch_size):
                vectors = encode_course_batch(model, course_batch, batch_size)
                for course, vector in zip(course_batch, vectors):
                    values = validate_embedding_vector(vector)
                    if dry_run:
                        print(f"DRY RUN embedding course_id={course['id']} dimension={len(values)}")
                    else:
                        write_embedding(conn, course["id"], values, model_name)
                    embedding_updates += 1

    print(
        "Processed "
        f"{len(courses)} courses, "
        f"{sparse_updates} sparse feature updates, "
        f"{embedding_updates} embedding updates."
    )
    return {
        "courses": len(courses),
        "sparse_updates": sparse_updates,
        "embedding_updates": embedding_updates,
    }


def positive_int(value):
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("Value must be positive.")
    return parsed


def parse_args():
    parser = argparse.ArgumentParser(description="Preprocess course dense and sparse features.")
    parser.add_argument("--database-url", default=os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL))
    parser.add_argument("--model-name", default=DEFAULT_MODEL_NAME)
    parser.add_argument("--batch-size", type=positive_int, default=DEFAULT_BATCH_SIZE)
    parser.add_argument("--limit", type=positive_int)
    parser.add_argument("--course-id", type=positive_int)
    parser.add_argument("--skip-embeddings", action="store_true")
    parser.add_argument("--skip-sparse", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main():
    args = parse_args()
    if args.skip_embeddings and args.skip_sparse:
        raise SystemExit("At least one preprocessing track must be enabled.")

    preprocess_course_features(
        database_url=args.database_url,
        model_name=args.model_name,
        batch_size=args.batch_size,
        limit=args.limit,
        course_id=args.course_id,
        skip_embeddings=args.skip_embeddings,
        skip_sparse=args.skip_sparse,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
