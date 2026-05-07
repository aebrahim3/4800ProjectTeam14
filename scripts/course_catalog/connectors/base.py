import hashlib
import re
import time
from abc import ABC, abstractmethod

import requests
from bs4 import BeautifulSoup

from course_catalog.fields import COURSE_CATALOG_FIELDS, JSON_DEFAULTS


HEADERS = {"User-Agent": "CareerMatchingCourseCatalogBot/1.0"}
REQUEST_DELAY_SECONDS = 1.5


def normalize_space(value):
    return re.sub(r"\s+", " ", value or "").strip()


def infer_course_level(course_number):
    match = re.search(r"\d+", course_number or "")
    if not match:
        return ""
    number = int(match.group())
    return f"{number // 100 * 100}-level"


def strip_prerequisite_text(text):
    cleaned = normalize_space(text)
    cleaned = re.sub(r"^Prerequisite(?:\(s\))?:\s*", "", cleaned, flags=re.IGNORECASE)
    return cleaned.strip(" .")


def extract_prerequisites(text):
    normalized = normalize_space(text)
    match = re.search(
        r"Prerequisite(?:\(s\))?:\s*(.*?)(?=(?:Corequisite(?:\(s\))?:|Equivalent Course|Students with credit|Quantitative/|Breadth-|Section Instructor|$))",
        normalized,
        flags=re.IGNORECASE,
    )
    if not match:
        return ""
    return strip_prerequisite_text(match.group(1))


def extract_unique_locations(text):
    locations = []
    for location in ["Burnaby", "Surrey", "Vancouver", "Downtown Vancouver"]:
        if re.search(rf"\b{re.escape(location)}\b", text or "", flags=re.IGNORECASE):
            locations.append(location)
    if "Downtown Vancouver" in locations and "Vancouver" in locations:
        locations.remove("Vancouver")
    return ", ".join(locations)


def build_source_hash(row):
    hash_fields = [
        "course_code",
        "title",
        "description",
        "credits",
        "prerequisites",
        "program_credential_association",
        "credential_type",
        "delivery_mode",
        "campus",
        "term_availability",
    ]
    raw = "|".join(normalize_space(row.get(field, "")) for field in hash_fields)
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


class BaseCourseCatalogConnector(ABC):
    institution_slug = ""

    def __init__(self, delay_seconds=REQUEST_DELAY_SECONDS):
        self.delay_seconds = delay_seconds

    def fetch(self, url):
        response = requests.get(url, headers=HEADERS, timeout=20)
        response.raise_for_status()
        time.sleep(self.delay_seconds)
        return BeautifulSoup(response.text, "html.parser")

    def record(self, **values):
        row = {field: "" for field in COURSE_CATALOG_FIELDS}
        row.update(JSON_DEFAULTS)
        row["institution_slug"] = self.institution_slug
        row.update(values)
        row["source_hash"] = build_source_hash(row)
        return row

    @abstractmethod
    def parse(self):
        raise NotImplementedError
