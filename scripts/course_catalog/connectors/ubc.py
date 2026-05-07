import re

from course_catalog.connectors.base import (
    BaseCourseCatalogConnector,
    extract_prerequisites,
    infer_course_level,
    normalize_space,
)


UBC_CPSC_URL = "https://vancouver.calendar.ubc.ca/course-descriptions/subject/cpscv"


class UBCCourseCatalogConnector(BaseCourseCatalogConnector):
    institution_slug = "ubc"

    def __init__(self, urls=None, delay_seconds=None):
        super().__init__(delay_seconds=1.5 if delay_seconds is None else delay_seconds)
        self.urls = urls or [UBC_CPSC_URL]

    def parse(self):
        rows = []
        for source_url in self.urls:
            soup = self.fetch(source_url)
            program_association = self._program_association(soup)
            campus = "Vancouver" if "vancouver.calendar.ubc.ca" in source_url else ""
            headings = soup.find_all(["h3", "h4"])
            for heading in headings:
                heading_text = normalize_space(heading.get_text(" "))
                match = re.match(r"^(CPSC_V)\s+(\d{3}[A-Z]?)\s+\(([\d.]+)\)\s+(.+)$", heading_text)
                if not match:
                    continue
                subject, number, credits, title = match.groups()
                description = self._description_after_heading(heading)
                rows.append(
                    self.record(
                        course_code=f"{subject} {number}",
                        subject_code=subject,
                        course_number=number,
                        title=title,
                        description=description or title,
                        credits=credits,
                        prerequisites=extract_prerequisites(description),
                        program_credential_association=program_association,
                        course_level=infer_course_level(number),
                        campus=campus,
                        course_url=source_url,
                        source_url=source_url,
                    )
                )
        return rows

    def _description_after_heading(self, heading):
        description_parts = []
        for sibling in heading.find_next_siblings():
            if sibling.name in {"h3", "h4"}:
                break
            text = normalize_space(sibling.get_text(" "))
            if text:
                description_parts.append(text)
        return normalize_space(" ".join(description_parts))

    def _program_association(self, soup):
        h1 = soup.find("h1")
        if not h1:
            return "Computer Science"
        return normalize_space(h1.get_text(" ")).split(",")[0]
