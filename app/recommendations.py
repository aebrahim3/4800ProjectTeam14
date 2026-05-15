from __future__ import annotations

import json
import logging
import math
import os
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

try:
    from fastapi import APIRouter, HTTPException, Request
except ImportError:
    APIRouter = None
    Request = Any

    class HTTPException(Exception):
        def __init__(self, status_code=None, detail=None):
            super().__init__(detail)
            self.status_code = status_code
            self.detail = detail

try:
    from pydantic import BaseModel, Field
except ImportError:
    class BaseModel:
        pass

    def Field(default=None, **_kwargs):
        return default

try:
    from sqlalchemy import text
    from sqlalchemy.exc import SQLAlchemyError
except ImportError:
    SQLAlchemyError = Exception

    def text(query):
        return query


logger = logging.getLogger(__name__)

DEFAULT_MODEL_NAME = "BAAI/bge-large-en-v1.5"
DEFAULT_MODEL_PATH = "models/course_ranker.json"
DEFAULT_RECALL_LIMIT = 50
DEFAULT_LIMIT = 3
MAX_LIMIT = 10
EMBEDDING_DIMENSION = 1024
ZERO_HIT_PENALTY = 0.35
FEATURE_NAMES = ("dense_similarity", "skill_hit_count", "credits", "is_local")
SPARSE_SHAP_PREFIX = "feature_sparse_"
SHAP_EXPLANATION_SOURCE = "shap"
HEURISTIC_EXPLANATION_SOURCE = "heuristic"


class _NoopRouter:
    def post(self, *_args, **_kwargs):
        def decorator(func):
            return func

        return decorator


router = APIRouter() if APIRouter is not None else _NoopRouter()


class RecommendationServiceError(RuntimeError):
    pass


class CourseRecommendationRequest(BaseModel):
    user_id: int
    skill_gaps: list[str]
    preferred_location: Optional[str] = None
    limit: int = Field(default=DEFAULT_LIMIT, ge=1, le=MAX_LIMIT)


@dataclass(frozen=True)
class TaxonomySkill:
    id: int
    skill_name: str
    feature_key: str
    aliases: tuple[str, ...]


@dataclass(frozen=True)
class RequestedSkill:
    raw_label: str
    skill_name: str
    feature_key: str


@dataclass(frozen=True)
class CourseCandidate:
    course_id: int
    institution: str
    course_code: str
    title: str
    url: str | None
    credits: float
    sparse_features: dict[str, Any]
    dense_similarity: float
    city: str | None = None
    province: str | None = None
    country: str | None = None


def normalize_feature_key(value: str) -> str:
    key = re.sub(r"[^A-Za-z0-9]+", "_", (value or "").strip().lower())
    return key.strip("_")


def normalize_alias(value: str | None) -> str:
    return re.sub(r"\s+", " ", (value or "").strip().lower())


def unique_preserving_order(values):
    seen = set()
    result = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def coerce_json_array(raw):
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


def coerce_json_object(raw):
    if raw is None:
        return {}
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        stripped = raw.strip()
        if not stripped:
            return {}
        try:
            parsed = json.loads(stripped)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def build_taxonomy_skill(row) -> TaxonomySkill:
    skill_id = int(row["id"])
    skill_name = str(row["skill_name"]).strip()
    feature_key = normalize_feature_key(skill_name) or f"skill_{skill_id}"
    aliases = [skill_name]
    aliases.extend(str(alias).strip() for alias in coerce_json_array(row.get("skill_synonyms")))
    aliases = tuple(unique_preserving_order(alias for alias in aliases if alias))
    return TaxonomySkill(skill_id, skill_name, feature_key, aliases)


def build_alias_lookup(taxonomy: list[TaxonomySkill]) -> dict[str, TaxonomySkill]:
    lookup = {}
    for skill in taxonomy:
        for alias in skill.aliases:
            normalized = normalize_alias(alias)
            if normalized and normalized not in lookup:
                lookup[normalized] = skill
    return lookup


def validate_skill_gap_input(skill_gaps: list[str]) -> list[str]:
    normalized = [str(skill).strip() for skill in skill_gaps if str(skill).strip()]
    if not normalized:
        raise ValueError("skill_gaps must contain at least one non-empty value")
    return normalized


def normalize_skill_gaps(skill_gaps: list[str], taxonomy: list[TaxonomySkill]):
    lookup = build_alias_lookup(taxonomy)
    requested = []
    unknown = []
    seen_feature_keys = set()

    for raw_label in validate_skill_gap_input(skill_gaps):
        skill = lookup.get(normalize_alias(raw_label))
        if skill is None:
            unknown.append(raw_label)
            continue
        if skill.feature_key in seen_feature_keys:
            continue
        requested.append(RequestedSkill(raw_label, skill.skill_name, skill.feature_key))
        seen_feature_keys.add(skill.feature_key)

    return requested, unknown


def truthy_feature_value(value) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value > 0
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes"}
    return False


def compute_skill_matches(sparse_features, requested_skills: list[RequestedSkill]):
    matched_skills, missing_skills = compute_requested_skill_matches(sparse_features, requested_skills)
    return [skill.raw_label for skill in matched_skills], [skill.raw_label for skill in missing_skills]


def compute_requested_skill_matches(sparse_features, requested_skills: list[RequestedSkill]):
    features = coerce_json_object(sparse_features)
    matched = []
    missing = []

    for skill in requested_skills:
        if truthy_feature_value(features.get(skill.feature_key)):
            matched.append(skill)
        else:
            missing.append(skill)

    return matched, missing


def is_local_match(preferred_location: str | None, candidate: CourseCandidate) -> int:
    wanted = normalize_alias(preferred_location)
    if not wanted:
        return 0

    for location in (candidate.city, candidate.province, candidate.country):
        normalized = normalize_alias(location)
        if normalized and (wanted == normalized or wanted in normalized or normalized in wanted):
            return 1
    return 0


def clamp_score(value) -> float:
    if value is None:
        return 0.0
    value = float(value)
    if not math.isfinite(value):
        return 0.0
    return max(0.0, min(1.0, value))


def apply_zero_hit_penalty(score: float, skill_hit_count: int, requested_skill_count: int) -> float:
    if requested_skill_count > 0 and skill_hit_count == 0:
        return clamp_score(score * ZERO_HIT_PENALTY)
    return clamp_score(score)


def build_feature_row(
    candidate: CourseCandidate,
    requested_skills: list[RequestedSkill],
    preferred_location: str | None,
) -> list[float]:
    matched_skills, _ = compute_skill_matches(candidate.sparse_features, requested_skills)
    return [
        float(candidate.dense_similarity),
        float(len(matched_skills)),
        float(candidate.credits or 0),
        float(is_local_match(preferred_location, candidate)),
    ]


def rule_fallback_score(feature_row: list[float], requested_skill_count: int) -> float:
    dense_similarity, skill_hit_count, credits, is_local = feature_row
    coverage = skill_hit_count / requested_skill_count if requested_skill_count else 0.0
    credit_score = max(0.0, min(float(credits) / 6.0, 1.0))
    score = (0.55 * dense_similarity) + (0.30 * coverage) + (0.10 * is_local) + (0.05 * credit_score)
    return clamp_score(score)


def predict_xgboost_scores(model, feature_rows: list[list[float]]) -> list[float]:
    import numpy as np
    import xgboost as xgb

    matrix = xgb.DMatrix(np.asarray(feature_rows, dtype=float), feature_names=list(FEATURE_NAMES))
    return [float(value) for value in model.predict(matrix)]


def score_feature_rows(model, feature_rows: list[list[float]], requested_skill_count: int):
    if not feature_rows:
        return [], model is None

    used_rule_fallback = model is None

    if used_rule_fallback:
        raw_scores = [rule_fallback_score(row, requested_skill_count) for row in feature_rows]
    else:
        try:
            raw_scores = predict_xgboost_scores(model, feature_rows)
            if len(raw_scores) != len(feature_rows):
                raise ValueError("XGBoost prediction count did not match feature row count")
        except Exception:
            used_rule_fallback = True
            raw_scores = [rule_fallback_score(row, requested_skill_count) for row in feature_rows]

    scored = []
    for score, row in zip(raw_scores, feature_rows):
        scored.append(apply_zero_hit_penalty(score, int(row[1]), requested_skill_count))
    return scored, used_rule_fallback


def normalize_shap_output(raw_shap_values, expected_rows: int, expected_features: int):
    if raw_shap_values is None:
        return None

    try:
        import numpy as np
    except ImportError:
        return None

    values = getattr(raw_shap_values, "values", raw_shap_values)
    try:
        matrix = np.asarray(values, dtype=float)
    except (TypeError, ValueError):
        return None

    if matrix.ndim == 3:
        if matrix.shape[1] == expected_rows and matrix.shape[2] == expected_features:
            matrix = matrix[-1]
        elif matrix.shape[0] == expected_rows and matrix.shape[1] == expected_features:
            matrix = matrix[:, :, -1]
        else:
            return None

    if matrix.ndim == 1 and expected_rows == 1 and matrix.shape[0] == expected_features:
        matrix = matrix.reshape(1, expected_features)

    if matrix.ndim != 2 or matrix.shape != (expected_rows, expected_features):
        return None
    if not np.all(np.isfinite(matrix)):
        return None

    return matrix.tolist()


def compute_shap_values(model, feature_rows: list[list[float]]):
    if model is None or not feature_rows:
        return None

    try:
        import numpy as np
        import shap
    except ImportError:
        return None

    try:
        feature_matrix = np.asarray(feature_rows, dtype=float)
        explainer = shap.TreeExplainer(model)
        raw_shap_values = explainer.shap_values(feature_matrix)
        return normalize_shap_output(raw_shap_values, len(feature_rows), len(FEATURE_NAMES))
    except Exception:
        return None


def build_sparse_shap_feature_name(skill: RequestedSkill) -> str:
    raw_key = normalize_feature_key(skill.raw_label)
    return f"{SPARSE_SHAP_PREFIX}{raw_key or skill.feature_key}"


def build_shap_contributions(
    row_shap_values,
    requested_skills: list[RequestedSkill],
    sparse_features,
):
    if row_shap_values is None:
        return []
    if len(row_shap_values) != len(FEATURE_NAMES):
        return []

    matched_requested_skills, _ = compute_requested_skill_matches(sparse_features, requested_skills)
    contributions = []

    for feature_name, raw_value in zip(FEATURE_NAMES, row_shap_values):
        value = float(raw_value)
        if feature_name == "skill_hit_count" and matched_requested_skills:
            shared_value = value / len(matched_requested_skills)
            for skill in matched_requested_skills:
                contributions.append(
                    {
                        "feature": build_sparse_shap_feature_name(skill),
                        "source_feature": feature_name,
                        "skill": skill.raw_label,
                        "canonical_skill": skill.skill_name,
                        "value": round(shared_value, 6),
                    }
                )
            continue

        contributions.append(
            {
                "feature": feature_name,
                "source_feature": feature_name,
                "value": round(value, 6),
            }
        )

    return sorted(
        contributions,
        key=lambda item: (-abs(item["value"]), item["feature"]),
    )


def top_positive_shap_contribution(shap_contributions):
    best = None
    for item in shap_contributions:
        if item["value"] <= 0:
            continue
        if best is None or item["value"] > best["value"]:
            best = item
    return best


def build_shap_explanation(shap_contributions) -> str | None:
    top_contribution = top_positive_shap_contribution(shap_contributions)
    if top_contribution is None:
        return None

    feature_name = top_contribution["feature"]
    if feature_name.startswith(SPARSE_SHAP_PREFIX) and top_contribution.get("skill"):
        return f"This course precisely covers your urgent {top_contribution['skill']} skill."
    if feature_name == "dense_similarity":
        return "This course's overall content strongly aligns with your target career."
    return None


def build_query_text(skill_gaps: list[str]) -> str:
    return "Skill gaps: " + ", ".join(skill_gaps)


def validate_embedding_vector(vector) -> list[float]:
    values = [float(value) for value in vector]
    if len(values) != EMBEDDING_DIMENSION:
        raise RecommendationServiceError(
            f"Expected query embedding dimension {EMBEDDING_DIMENSION}, got {len(values)}"
        )
    if any(not math.isfinite(value) for value in values):
        raise RecommendationServiceError("Query embedding contains non-finite values")
    return values


def format_pgvector(vector) -> str:
    return "[" + ",".join(f"{value:.10g}" for value in vector) + "]"


@lru_cache(maxsize=2)
def load_embedding_model(model_name: str = DEFAULT_MODEL_NAME):
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        raise RecommendationServiceError(
            "Install sentence-transformers and torch to encode recommendation queries."
        ) from exc
    try:
        return SentenceTransformer(model_name)
    except Exception as exc:
        raise RecommendationServiceError(
            f"Failed to load embedding model {model_name}. "
            "Check network/model cache availability inside the recommender container."
        ) from exc


def encode_query_embedding(skill_gaps: list[str], model_name: str = DEFAULT_MODEL_NAME) -> list[float]:
    model = load_embedding_model(model_name)
    encoded = model.encode([build_query_text(skill_gaps)], normalize_embeddings=True)
    if hasattr(encoded, "tolist"):
        encoded = encoded.tolist()
    if encoded and isinstance(encoded[0], list):
        encoded = encoded[0]
    return validate_embedding_vector(encoded)


@lru_cache(maxsize=4)
def load_xgboost_model(model_path: str):
    path = Path(model_path).expanduser()
    if not path.exists():
        return None

    try:
        import xgboost as xgb
    except ImportError:
        return None

    try:
        model = xgb.Booster()
        model.load_model(str(path))
        return model
    except Exception:
        return None


def get_ranker_model():
    return load_xgboost_model(os.getenv("COURSE_RANKER_MODEL_PATH", DEFAULT_MODEL_PATH))


def fetch_taxonomy(engine) -> list[TaxonomySkill]:
    query = text(
        """
        SELECT id, skill_name, skill_synonyms
        FROM skills_taxonomy
        ORDER BY skill_name, id
        """
    )
    try:
        with engine.connect() as conn:
            rows = conn.execute(query).mappings().all()
    except SQLAlchemyError as exc:
        raise RecommendationServiceError(
            "Failed to load skills_taxonomy from the database. "
            "Check DATABASE_URL and run the latest migrations."
        ) from exc
    return [build_taxonomy_skill(row) for row in rows]


def row_to_candidate(row) -> CourseCandidate:
    institution = row.get("institution_slug") or row.get("institution_name") or ""
    if row.get("institution_slug"):
        institution = str(row["institution_slug"]).upper()

    return CourseCandidate(
        course_id=int(row["course_id"]),
        institution=institution,
        course_code=str(row.get("course_code") or ""),
        title=str(row.get("title") or ""),
        url=row.get("url"),
        credits=float(row.get("credits") or 0),
        sparse_features=coerce_json_object(row.get("sparse_features")),
        dense_similarity=float(row.get("dense_similarity") or 0),
        city=row.get("city"),
        province=row.get("province"),
        country=row.get("country"),
    )


def fetch_course_candidates(engine, query_embedding: list[float], recall_limit: int = DEFAULT_RECALL_LIMIT):
    query = text(
        """
        SELECT
            c.id AS course_id,
            i.name AS institution_name,
            i.slug AS institution_slug,
            i.city,
            i.province,
            i.country,
            c.course_code,
            c.title,
            c.course_url AS url,
            COALESCE(c.credits, 0) AS credits,
            COALESCE(c.sparse_features, '{}'::jsonb) AS sparse_features,
            (1 - (c.embedding <=> CAST(:query_embedding AS vector))) AS dense_similarity
        FROM courses c
        JOIN institutions i ON i.id = c.institution_id
        WHERE c.is_active = TRUE
          AND c.embedding IS NOT NULL
        ORDER BY c.embedding <=> CAST(:query_embedding AS vector)
        LIMIT :recall_limit
        """
    )
    try:
        with engine.connect() as conn:
            rows = conn.execute(
                query,
                {
                    "query_embedding": format_pgvector(query_embedding),
                    "recall_limit": int(recall_limit),
                },
            ).mappings().all()
    except SQLAlchemyError as exc:
        raise RecommendationServiceError(
            "Failed to recall course candidates. "
            "Check that courses.embedding is vector(1024), pgvector is enabled, "
            "and course feature preprocessing has been run."
        ) from exc
    return [row_to_candidate(row) for row in rows]


def format_skill_list(values: list[str]) -> str:
    if not values:
        return ""
    if len(values) == 1:
        return values[0]
    if len(values) == 2:
        return f"{values[0]} and {values[1]}"
    return ", ".join(values[:-1]) + f", and {values[-1]}"


def build_explanation(matched_skills: list[str], dense_similarity: float) -> str:
    if matched_skills and dense_similarity >= 0.75:
        return (
            f"This course covers {format_skill_list(matched_skills)}, "
            "with strong semantic alignment to your skill gaps."
        )
    if matched_skills:
        return f"This course covers {format_skill_list(matched_skills)}."
    if dense_similarity >= 0.75:
        return "This course has strong semantic alignment to your skill gaps."
    return "This course is the best available catalog match for the requested skill gaps."


def generate_recommendations(
    skill_gaps: list[str],
    preferred_location: str | None,
    limit: int,
    taxonomy: list[TaxonomySkill],
    candidates: list[CourseCandidate],
    model=None,
):
    requested_skills, unknown_skill_gaps = normalize_skill_gaps(skill_gaps, taxonomy)
    feature_rows = [build_feature_row(candidate, requested_skills, preferred_location) for candidate in candidates]
    scores, used_rule_fallback = score_feature_rows(model, feature_rows, len(requested_skills))
    shap_value_rows = None if used_rule_fallback else compute_shap_values(model, feature_rows)

    recommendations = []
    for index, (candidate, feature_row, score) in enumerate(zip(candidates, feature_rows, scores)):
        matched_skills, missing_skills = compute_skill_matches(candidate.sparse_features, requested_skills)
        row_shap_values = shap_value_rows[index] if shap_value_rows else None
        shap_contributions = build_shap_contributions(
            row_shap_values,
            requested_skills,
            candidate.sparse_features,
        )
        shap_explanation = build_shap_explanation(shap_contributions)
        top_shap_contribution = top_positive_shap_contribution(shap_contributions)
        recommendations.append(
            {
                "course_id": candidate.course_id,
                "institution": candidate.institution,
                "course_code": candidate.course_code,
                "title": candidate.title,
                "url": candidate.url,
                "score": round(clamp_score(score), 4),
                "dense_similarity": round(clamp_score(candidate.dense_similarity), 4),
                "skill_hit_count": int(feature_row[1]),
                "matched_skills": matched_skills,
                "missing_skills": missing_skills,
                "explanation": shap_explanation or build_explanation(matched_skills, candidate.dense_similarity),
                "explanation_source": (
                    SHAP_EXPLANATION_SOURCE if shap_explanation else HEURISTIC_EXPLANATION_SOURCE
                ),
                "top_shap_feature": top_shap_contribution["feature"] if top_shap_contribution else None,
                "shap_values": shap_contributions,
            }
        )

    recommendations.sort(
        key=lambda item: (
            -item["score"],
            -item["skill_hit_count"],
            -item["dense_similarity"],
            item["course_id"],
        )
    )

    return {
        "model_version": "rule_fallback" if used_rule_fallback else "xgboost",
        "used_rule_fallback": used_rule_fallback,
        "unknown_skill_gaps": unknown_skill_gaps,
        "recommendations": recommendations[:limit],
    }


def build_course_recommendations(
    engine,
    skill_gaps: list[str],
    preferred_location: str | None = None,
    limit: int = DEFAULT_LIMIT,
):
    skill_gaps = validate_skill_gap_input(skill_gaps)
    taxonomy = fetch_taxonomy(engine)
    query_embedding = encode_query_embedding(skill_gaps)
    candidates = fetch_course_candidates(engine, query_embedding, DEFAULT_RECALL_LIMIT)
    model = get_ranker_model()
    return generate_recommendations(skill_gaps, preferred_location, limit, taxonomy, candidates, model)


@router.post("/career/course-recommendations")
async def recommend_courses(payload: CourseRecommendationRequest, request: Request):
    try:
        skill_gaps = validate_skill_gap_input(payload.skill_gaps)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    try:
        return build_course_recommendations(
            request.app.state.engine,
            skill_gaps=skill_gaps,
            preferred_location=payload.preferred_location,
            limit=payload.limit,
        )
    except RecommendationServiceError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Unexpected course recommendation failure")
        raise HTTPException(
            status_code=503,
            detail="Unexpected course recommendation failure. Check recommender container logs.",
        ) from exc
