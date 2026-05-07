import sys
import unittest
from pathlib import Path

from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from course_catalog.connectors.bcit import BCITCourseCatalogConnector
from course_catalog.connectors.sfu import SFUCourseCatalogConnector
from course_catalog.connectors.ubc import UBCCourseCatalogConnector


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "course_catalog"


def connector_with_fixture(connector, fixture_name):
    html = (FIXTURE_DIR / fixture_name).read_text(encoding="utf-8")
    connector.fetch = lambda _url: BeautifulSoup(html, "html.parser")
    return connector


class CourseCatalogConnectorTests(unittest.TestCase):
    def test_bcit_extracts_program_and_course_fields(self):
        connector = connector_with_fixture(BCITCourseCatalogConnector(urls=["fixture://bcit"]), "bcit_cst.html")
        rows = connector.parse()
        row = rows[0]
        self.assertEqual(row["course_code"], "COMP 1510")
        self.assertEqual(row["prerequisites"], "No prerequisites are required for this course")
        self.assertEqual(row["program_credential_association"], "Computer Systems Technology")
        self.assertEqual(row["credential_type"], "Diploma")
        self.assertEqual(row["delivery_mode"], "In-person")
        self.assertEqual(row["campus"], "Burnaby and Downtown Vancouver campuses")
        self.assertEqual(row["term_availability"], "September & January")
        self.assertEqual(row["course_level"], "First Year - Level 1")

    def test_ubc_extracts_prerequisite_and_inferred_fields(self):
        connector = connector_with_fixture(UBCCourseCatalogConnector(urls=["https://vancouver.calendar.ubc.ca/test"]), "ubc_cpscv.html")
        row = connector.parse()[0]
        self.assertEqual(row["course_code"], "CPSC_V 330")
        self.assertEqual(row["course_level"], "300-level")
        self.assertEqual(row["campus"], "Vancouver")
        self.assertEqual(row["program_credential_association"], "Computer Science")
        self.assertEqual(row["prerequisites"], "Either CPSC_V 203 or CPSC_V 210")

    def test_sfu_extracts_prerequisite_term_campus_and_level(self):
        connector = connector_with_fixture(SFUCourseCatalogConnector(urls=["fixture://sfu"]), "sfu_cmpt120.html")
        row = connector.parse()[0]
        self.assertEqual(row["course_code"], "CMPT 120")
        self.assertEqual(row["course_level"], "100-level")
        self.assertEqual(row["program_credential_association"], "Computing Science")
        self.assertEqual(row["term_availability"], "Summer 2026")
        self.assertEqual(row["campus"], "Burnaby, Surrey")
        self.assertEqual(row["prerequisites"], "BC Math 12 or equivalent is recommended")

    def test_source_hash_changes_when_structured_content_changes(self):
        connector = connector_with_fixture(UBCCourseCatalogConnector(urls=["https://vancouver.calendar.ubc.ca/test"]), "ubc_cpscv.html")
        row = connector.parse()[0]
        changed = {**row, "prerequisites": "Different prerequisite"}
        self.assertNotEqual(row["source_hash"], connector.record(**changed)["source_hash"])


if __name__ == "__main__":
    unittest.main()
