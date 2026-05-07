import re

from course_catalog.connectors.base import (
    BaseCourseCatalogConnector,
    extract_prerequisites,
    extract_unique_locations,
    infer_course_level,
    normalize_space,
)


SFU_CMPT_NUMBERS = [
    "120",
    "125",
    "130",
    "135",
    "225",
    "263",
    "276",
    "295",
    "300",
    "307",
    "310",
    "353",
    "354",
    "361",
    "363",
    "371",
    "404",
    "431",
    "756",
    "839",
]
SFU_CMPT_URL_TEMPLATE = "https://www.sfu.ca/students/calendar/2026/summer/courses/cmpt/{number}.html"


class SFUCourseCatalogConnector(BaseCourseCatalogConnector):
    institution_slug = "sfu"

    def __init__(self, urls=None, delay_seconds=None):
        super().__init__(delay_seconds=1.5 if delay_seconds is None else delay_seconds)
        self.urls = urls or [SFU_CMPT_URL_TEMPLATE.format(number=number) for number in SFU_CMPT_NUMBERS]

    def parse(self):
        rows = []
        for source_url in self.urls:
            soup = self.fetch(source_url)
            parsed = self._parse_course_page(soup)
            if not parsed:
                continue
            rows.append(
                self.record(
                    course_url=source_url,
                    source_url=source_url,
                    **parsed,
                )
            )
        return rows

    def _parse_course_page(self, soup):
        h1 = self._course_heading(soup)
        if not h1:
            return None
        heading_text = normalize_space(h1.get_text(" "))
        match = re.match(r"^(.*?)\s+CMPT\s+(\d{3})\s+\(([\d.]+)\)$", heading_text)
        if not match:
            return None

        title, number, credits = match.groups()
        description = self._course_description(h1)
        page_text = normalize_space(soup.get_text(" "))
        section_text = normalize_space(soup.find("div", class_="course-sections").get_text(" ")) if soup.find("div", class_="course-sections") else ""
        term = self._term_availability(soup, page_text)
        return {
            "course_code": f"CMPT {number}",
            "subject_code": "CMPT",
            "course_number": number,
            "title": normalize_space(title),
            "description": description or normalize_space(title),
            "credits": credits,
            "prerequisites": extract_prerequisites(description),
            "program_credential_association": "Computing Science",
            "course_level": infer_course_level(number),
            "campus": extract_unique_locations(section_text),
            "term_availability": term,
        }

    def _course_heading(self, soup):
        for candidate in soup.find_all("h1"):
            text = normalize_space(candidate.get_text(" "))
            if re.match(r"^.*?\s+CMPT\s+\d{3}\s+\([\d.]+\)$", text):
                return candidate
        return None

    def _course_description(self, h1):
        parts = []
        for sibling in h1.find_next_siblings():
            text = normalize_space(sibling.get_text(" "))
            if not text or text.startswith("Section Instructor Day/Time Location"):
                break
            parts.append(text)
        return normalize_space(" ".join(parts))

    def _term_availability(self, soup, page_text):
        title = normalize_space(soup.title.get_text(" ")) if soup.title else ""
        match = re.search(r"\b(Spring|Summer|Fall)\s+(20\d{2})\b", page_text)
        if match:
            return f"{match.group(1)} {match.group(2)}"
        match = re.search(r"\b(Spring|Summer|Fall)\s+Calendar\b", title)
        if match:
            year_match = re.search(r"/(20\d{2})/", page_text)
            return f"{match.group(1)} {year_match.group(1)}" if year_match else match.group(1)
        return ""
