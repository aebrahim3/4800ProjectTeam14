import os
import unittest
from unittest.mock import patch

from app.recommendations import (
    CourseCandidate,
    RequestedSkill,
    TaxonomySkill,
    apply_zero_hit_penalty,
    build_feature_row,
    compute_skill_matches,
    generate_recommendations,
    get_ranker_model,
    load_xgboost_model,
    normalize_skill_gaps,
    rule_fallback_score,
)

try:
    from fastapi.testclient import TestClient
    from app.main import app

    FASTAPI_AVAILABLE = True
except ImportError:
    TestClient = None
    app = None
    FASTAPI_AVAILABLE = False


class CourseRecommendationLogicTests(unittest.TestCase):
    def setUp(self):
        self.taxonomy = [
            TaxonomySkill(1, "Python", "python", ("Python", "Python3", "Py")),
            TaxonomySkill(2, "Project Management", "project_management", ("Project Management", "Agile", "Scrum")),
            TaxonomySkill(3, "Cloud Architecture", "cloud_architecture", ("Cloud Architecture", "AWS", "Azure", "GCP")),
        ]

    def test_skill_gap_normalization_maps_aliases_to_feature_keys(self):
        requested, unknown = normalize_skill_gaps(["AWS", "Python", "Agile"], self.taxonomy)

        self.assertEqual(unknown, [])
        self.assertEqual(
            [(skill.raw_label, skill.skill_name, skill.feature_key) for skill in requested],
            [
                ("AWS", "Cloud Architecture", "cloud_architecture"),
                ("Python", "Python", "python"),
                ("Agile", "Project Management", "project_management"),
            ],
        )

    def test_feature_row_order_is_stable(self):
        candidate = CourseCandidate(
            course_id=10,
            institution="BCIT",
            course_code="COMP 2800",
            title="Projects 2",
            url="https://example.com",
            credits=4,
            sparse_features={"cloud_architecture": 1, "python": 0},
            dense_similarity=0.82,
            province="British Columbia",
        )
        requested = [
            RequestedSkill("AWS", "Cloud Architecture", "cloud_architecture"),
            RequestedSkill("Python", "Python", "python"),
        ]

        self.assertEqual(build_feature_row(candidate, requested, "British Columbia"), [0.82, 1.0, 4.0, 1.0])

    def test_sparse_hit_count_handles_partial_and_missing_skills(self):
        requested = [
            RequestedSkill("AWS", "Cloud Architecture", "cloud_architecture"),
            RequestedSkill("Python", "Python", "python"),
            RequestedSkill("Agile", "Project Management", "project_management"),
        ]

        matched, missing = compute_skill_matches({"cloud_architecture": 1, "python": 0}, requested)

        self.assertEqual(matched, ["AWS"])
        self.assertEqual(missing, ["Python", "Agile"])

    def test_zero_sparse_hit_penalty_reduces_high_scores(self):
        self.assertAlmostEqual(apply_zero_hit_penalty(0.9, 0, 3), 0.315)
        self.assertEqual(apply_zero_hit_penalty(0.9, 1, 3), 0.9)

    def test_rule_fallback_score_is_deterministic_and_bounded(self):
        feature_row = [0.9, 2.0, 4.0, 1.0]

        first = rule_fallback_score(feature_row, 3)
        second = rule_fallback_score(feature_row, 3)

        self.assertEqual(first, second)
        self.assertGreaterEqual(first, 0)
        self.assertLessEqual(first, 1)

    def test_generate_recommendations_ranks_deterministically_with_model_scores(self):
        candidates = [
            CourseCandidate(1, "BCIT", "COMP 1000", "Intro", None, 3, {"cloud_architecture": 1}, 0.70),
            CourseCandidate(2, "UBC", "CPSC 330", "Applied ML", None, 4, {"python": 1}, 0.90),
            CourseCandidate(3, "SFU", "CMPT 276", "Software", None, 3, {"project_management": 1}, 0.80),
            CourseCandidate(4, "BCIT", "COMP 1630", "SQL", None, 4, {}, 0.95),
        ]

        with patch("app.recommendations.predict_xgboost_scores", return_value=[0.40, 0.90, 0.70, 0.99]):
            result = generate_recommendations(
                ["AWS", "Python", "Agile"],
                "British Columbia",
                3,
                self.taxonomy,
                candidates,
                model=object(),
            )

        self.assertEqual(result["model_version"], "xgboost")
        self.assertFalse(result["used_rule_fallback"])
        self.assertEqual([item["course_id"] for item in result["recommendations"]], [2, 3, 1])

    def test_missing_xgboost_model_path_uses_rule_fallback_loader(self):
        load_xgboost_model.cache_clear()
        with patch.dict(os.environ, {"COURSE_RANKER_MODEL_PATH": "/tmp/does-not-exist-course-ranker.json"}):
            self.assertIsNone(get_ranker_model())


class CourseRecommendationApiTests(unittest.TestCase):
    @unittest.skipUnless(FASTAPI_AVAILABLE, "FastAPI is not installed in this local test environment")
    def test_api_rejects_empty_skill_gaps(self):
        client = TestClient(app)

        response = client.post(
            "/career/course-recommendations",
            json={"user_id": 1, "skill_gaps": [], "preferred_location": "British Columbia"},
        )

        self.assertEqual(response.status_code, 422)

    @unittest.skipUnless(FASTAPI_AVAILABLE, "FastAPI is not installed in this local test environment")
    def test_api_returns_mocked_recommendations(self):
        mocked_response = {
            "model_version": "rule_fallback",
            "used_rule_fallback": True,
            "unknown_skill_gaps": [],
            "recommendations": [
                {"course_id": 1, "title": "A"},
                {"course_id": 2, "title": "B"},
                {"course_id": 3, "title": "C"},
            ],
        }

        with patch("app.recommendations.build_course_recommendations", return_value=mocked_response) as mocked:
            client = TestClient(app)
            response = client.post(
                "/career/course-recommendations",
                json={"user_id": 1, "skill_gaps": ["AWS", "Python"], "limit": 3},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), mocked_response)
        mocked.assert_called_once()


if __name__ == "__main__":
    unittest.main()
