import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from preprocess_course_features import (
    DEFAULT_EMBEDDING_DIMENSION,
    TaxonomySkill,
    build_sparse_feature_payload,
    build_taxonomy_skill,
    find_text_skill_matches,
    normalize_feature_key,
    validate_embedding_vector,
)


class CourseFeaturePreprocessingTests(unittest.TestCase):
    def setUp(self):
        self.taxonomy = [
            TaxonomySkill(1, "Python", "python", ("Python", "Python3", "Py")),
            TaxonomySkill(2, "Project Management", "project_management", ("Project Management", "Agile", "Scrum")),
            TaxonomySkill(3, "Cloud Architecture", "cloud_architecture", ("Cloud Architecture", "AWS", "Azure", "GCP", "Cloud")),
            TaxonomySkill(4, "SQL", "sql", ("SQL", "PostgreSQL")),
        ]

    def test_bge_large_embedding_dimension_is_1024(self):
        self.assertEqual(DEFAULT_EMBEDDING_DIMENSION, 1024)

    def test_feature_key_normalization_is_stable(self):
        self.assertEqual(normalize_feature_key("Machine Learning"), "machine_learning")
        self.assertEqual(normalize_feature_key("Cloud / AWS"), "cloud_aws")
        self.assertEqual(normalize_feature_key("  SQL  "), "sql")

    def test_build_taxonomy_skill_reads_synonym_json(self):
        skill = build_taxonomy_skill(
            {
                "id": 9,
                "skill_name": "Cloud Architecture",
                "skill_synonyms": '["AWS", "Azure", "GCP"]',
            }
        )
        self.assertEqual(skill.feature_key, "cloud_architecture")
        self.assertEqual(skill.aliases, ("Cloud Architecture", "AWS", "Azure", "GCP"))

    def test_synonym_matching_recognizes_aws_python_and_agile(self):
        course = {
            "id": 100,
            "title": "Cloud Project Studio",
            "description": "Build Agile software using AWS services and Python automation.",
            "prerequisites": "",
            "learning_outcomes": "",
            "program_credential_association": "",
            "certification": "",
        }
        matches = find_text_skill_matches(course, self.taxonomy)

        self.assertIn(1, matches)
        self.assertIn(2, matches)
        self.assertIn(3, matches)
        self.assertIn("Python", matches[1]["matched_aliases"])
        self.assertIn("Agile", matches[2]["matched_aliases"])
        self.assertIn("AWS", matches[3]["matched_aliases"])

    def test_sparse_features_include_all_taxonomy_keys_as_zero_or_one(self):
        course = {
            "id": 101,
            "title": "Cloud Project Studio",
            "description": "Build Agile software using AWS services and Python automation.",
            "prerequisites": "",
            "learning_outcomes": "",
            "program_credential_association": "",
            "certification": "",
        }
        features, _ = build_sparse_feature_payload(course, self.taxonomy)

        self.assertEqual(
            features,
            {
                "cloud_architecture": 1,
                "project_management": 1,
                "python": 1,
                "sql": 0,
            },
        )

    def test_existing_manual_mapping_becomes_positive_sparse_feature(self):
        course = {
            "id": 102,
            "title": "Database Foundations",
            "description": "Relational design and normalization.",
            "prerequisites": "",
            "learning_outcomes": "",
            "program_credential_association": "",
            "certification": "",
        }
        existing_mappings = {
            4: {
                "confidence_score": 0.96,
                "mapping_source": "manual",
                "rationale": "Manual SQL mapping.",
            }
        }

        features, records = build_sparse_feature_payload(course, self.taxonomy, existing_mappings)
        sql_record = next(record for record in records if record["skill_taxonomy_id"] == 4)

        self.assertEqual(features["sql"], 1)
        self.assertEqual(sql_record["mapping_source"], "manual")
        self.assertEqual(sql_record["confidence_score"], 0.96)
        self.assertIn("course_skill_mapping", sql_record["source_fields"])

    def test_embedding_dimension_mismatch_raises(self):
        with self.assertRaisesRegex(ValueError, "Expected embedding dimension 1024"):
            validate_embedding_vector([0.1, 0.2])


if __name__ == "__main__":
    unittest.main()
