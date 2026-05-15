import os
import importlib.util
import unittest
from unittest.mock import patch

from app.recommendations import (
    CourseCandidate,
    RecommendationServiceError,
    RequestedSkill,
    TaxonomySkill,
    apply_zero_hit_penalty,
    build_feature_row,
    build_ranking_signals,
    build_shap_contributions,
    build_shap_explanation,
    compute_skill_matches,
    generate_recommendations,
    get_ranker_model,
    hybrid_nn_score,
    load_embedding_model,
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

    def test_shap_sparse_contribution_maps_to_skill_feature_and_template(self):
        requested = [
            RequestedSkill("AWS", "Cloud Architecture", "cloud_architecture"),
            RequestedSkill("Python", "Python", "python"),
        ]

        contributions = build_shap_contributions(
            [0.10, 0.90, -0.02, 0.01],
            requested,
            {"cloud_architecture": 1, "python": 0},
        )

        self.assertEqual(contributions[0]["feature"], "feature_sparse_aws")
        self.assertEqual(contributions[0]["source_feature"], "skill_hit_count")
        self.assertEqual(contributions[0]["skill"], "AWS")
        self.assertEqual(contributions[0]["value"], 0.9)
        self.assertEqual(
            build_shap_explanation(contributions),
            "This course precisely covers your urgent AWS skill.",
        )

    def test_shap_dense_similarity_template_when_dense_is_top_driver(self):
        requested = [RequestedSkill("AWS", "Cloud Architecture", "cloud_architecture")]

        contributions = build_shap_contributions(
            [0.80, 0.10, 0.00, 0.00],
            requested,
            {"cloud_architecture": 1},
        )

        self.assertEqual(contributions[0]["feature"], "dense_similarity")
        self.assertEqual(
            build_shap_explanation(contributions),
            "This course's overall content strongly aligns with your target career.",
        )

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

    def test_hybrid_nn_score_uses_stable_weights(self):
        feature_row = [0.8, 2.0, 3.0, 1.0]

        signals = build_ranking_signals(feature_row, requested_skill_count=4)

        self.assertEqual(signals["dense_similarity_weight"], 0.6)
        self.assertEqual(signals["skill_coverage_weight"], 0.3)
        self.assertEqual(signals["is_local_weight"], 0.07)
        self.assertEqual(signals["credit_score_weight"], 0.03)
        self.assertEqual(signals["skill_coverage"], 0.5)
        self.assertEqual(signals["credit_score"], 0.5)
        self.assertFalse(signals["zero_hit_penalty_applied"])
        self.assertAlmostEqual(hybrid_nn_score(feature_row, 4), 0.715)

    def test_hybrid_nn_zero_hit_penalty_reduces_high_dense_score(self):
        zero_hit_score = hybrid_nn_score([0.95, 0.0, 6.0, 1.0], 2)
        one_hit_score = hybrid_nn_score([0.60, 1.0, 3.0, 1.0], 2)

        self.assertLess(zero_hit_score, one_hit_score)

    def test_generate_recommendations_ranks_by_hybrid_nn_score(self):
        candidates = [
            CourseCandidate(1, "BCIT", "COMP 1000", "Intro", None, 3, {"cloud_architecture": 1}, 0.80),
            CourseCandidate(
                2,
                "BCIT",
                "COMP 2800",
                "Projects",
                None,
                4,
                {"cloud_architecture": 1, "project_management": 1},
                0.60,
                province="British Columbia",
            ),
            CourseCandidate(3, "UBC", "CPSC 330", "Applied ML", None, 4, {"python": 1}, 0.85),
            CourseCandidate(4, "BCIT", "COMP 1630", "General", None, 4, {}, 0.95),
        ]

        result = generate_recommendations(
            ["AWS", "Python", "Agile"],
            "British Columbia",
            3,
            self.taxonomy,
            candidates,
        )

        self.assertEqual(result["model_version"], "hybrid_nn_v1")
        self.assertFalse(result["used_rule_fallback"])
        self.assertEqual([item["course_id"] for item in result["recommendations"]], [2, 3, 1])
        self.assertTrue(result["recommendations"][0]["ranking_signals"]["is_local"])
        self.assertTrue(result["recommendations"][2]["ranking_signals"]["zero_hit_penalty_applied"] is False)

    def test_generate_recommendations_keeps_compatible_explanation_fields_without_shap(self):
        candidates = [
            CourseCandidate(1, "BCIT", "COMP 2800", "Projects 2", None, 4, {"cloud_architecture": 1}, 0.84),
        ]

        result = generate_recommendations(
            ["AWS", "Python"],
            "British Columbia",
            3,
            self.taxonomy,
            candidates,
        )

        recommendation = result["recommendations"][0]
        self.assertEqual(recommendation["explanation_source"], "heuristic")
        self.assertIsNone(recommendation["top_shap_feature"])
        self.assertEqual(recommendation["shap_values"], [])
        self.assertIn("ranking_signals", recommendation)

    def test_unknown_skill_does_not_change_known_skill_denominator(self):
        candidates = [
            CourseCandidate(1, "BCIT", "COMP 2800", "Projects 2", None, 4, {"cloud_architecture": 1}, 0.84),
        ]

        result = generate_recommendations(
            ["TotallyMadeUpSkillXYZ", "AWS"],
            "British Columbia",
            3,
            self.taxonomy,
            candidates,
        )

        recommendation = result["recommendations"][0]
        self.assertEqual(result["unknown_skill_gaps"], ["TotallyMadeUpSkillXYZ"])
        self.assertEqual(recommendation["matched_skills"], ["AWS"])
        self.assertEqual(recommendation["ranking_signals"]["skill_coverage"], 1.0)

    def test_missing_xgboost_model_path_uses_rule_fallback_loader(self):
        load_xgboost_model.cache_clear()
        with patch.dict(os.environ, {"COURSE_RANKER_MODEL_PATH": "/tmp/does-not-exist-course-ranker.json"}):
            self.assertIsNone(get_ranker_model())

    def test_embedding_model_load_failure_has_actionable_error(self):
        if importlib.util.find_spec("sentence_transformers") is None:
            self.skipTest("sentence-transformers is not installed in this local test environment")
        load_embedding_model.cache_clear()
        with patch("sentence_transformers.SentenceTransformer", side_effect=OSError("offline")):
            with self.assertRaisesRegex(RecommendationServiceError, "Failed to load embedding model"):
                load_embedding_model("BAAI/bge-large-en-v1.5")
        load_embedding_model.cache_clear()


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
            "model_version": "hybrid_nn_v1",
            "used_rule_fallback": False,
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
