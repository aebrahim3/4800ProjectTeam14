import re

from course_catalog.connectors.base import (
    BaseCourseCatalogConnector,
    build_source_hash,
    merge_text,
    merge_row_values,
    normalize_space,
)


UBC_PROGRAM_URLS = [
    "https://vancouver.calendar.ubc.ca/faculties-colleges-and-schools/faculty-science/bachelor-science/computer-science",
]

SFU_PROGRAM_URLS = [
    "https://www.sfu.ca/students/calendar/2025/fall/programs/computing-studies/certificate",
]


class BCITCourseDetailEnricher(BaseCourseCatalogConnector):
    institution_slug = "bcit"

    def parse(self):
        return []

    def enrich(self, rows):
        for row in rows:
            if row.get("institution_slug") != self.institution_slug:
                continue
            course_url = row.get("course_url", "")
            if "/courses/" not in course_url:
                continue
            soup = self.fetch(course_url)
            merge_row_values(row, self._parse_detail_page(soup))
        return rows

    def _parse_detail_page(self, soup):
        learning_outcomes = self._section_text(soup, "Learning Outcomes")
        related_programs = self._related_programs(soup)
        updates = {
            "learning_outcomes": learning_outcomes,
            "source_hash": "",
        }
        if related_programs:
            updates.update(related_programs)
        return updates

    def _section_text(self, soup, heading_text):
        for heading in soup.find_all(["h2", "h3"]):
            if normalize_space(heading.get_text(" ")) != heading_text:
                continue
            section = heading.find_next_sibling()
            if not section:
                return ""
            return self._compact_learning_outcomes(section)
        return ""

    def _compact_learning_outcomes(self, section):
        items = [normalize_space(item.get_text(" ")) for item in section.find_all("li")]
        if not items:
            text = normalize_space(section.get_text(" "))
            text = re.sub(r"^Upon successful completion of this course, the student will be able to:\s*", "", text, flags=re.IGNORECASE)
            return text
        return "; ".join(item for item in items if item)

    def _related_programs(self, soup):
        text = self._section_text(soup, "Related Programs")
        if not text:
            return {}

        program_names = []
        credential_types = []
        pattern = re.compile(
            r"([A-Z][A-Za-z0-9&'()/, .+-]+?)\s+(Associate Certificate|Certificate|Diploma|Degree)\s+(?:Full-time|Part-time)",
        )
        for name, credential_type in pattern.findall(text):
            name = normalize_space(name)
            if name.startswith("School of "):
                name = re.sub(r"^School of [A-Za-z &]+?\s+", "", name)
            full_name = f"{name} {credential_type}"
            if full_name not in program_names:
                program_names.append(full_name)
            if credential_type not in credential_types:
                credential_types.append(credential_type)

        if not program_names:
            return {}
        return {
            "program_credential_association": "; ".join(program_names),
            "certification": "; ".join(program_names),
            "credential_type": "; ".join(credential_types),
        }


class UBCProgramCredentialMapper(BaseCourseCatalogConnector):
    institution_slug = "ubc"

    def __init__(self, urls=None, delay_seconds=None):
        super().__init__(delay_seconds=1.5 if delay_seconds is None else delay_seconds)
        self.urls = urls or UBC_PROGRAM_URLS

    def parse(self):
        mappings = {}
        for url in self.urls:
            soup = self.fetch(url)
            mappings.update(self._parse_program_page(soup))
        return mappings

    def enrich(self, rows):
        mappings = self.parse()
        for row in rows:
            if row.get("institution_slug") != self.institution_slug:
                continue
            updates = mappings.get(row.get("course_code"))
            if updates:
                merge_row_values(row, updates)
        return rows

    def _parse_program_page(self, soup):
        program_name = normalize_space(soup.find("h1").get_text(" ")) if soup.find("h1") else "Computer Science"
        mappings = {}
        headings = soup.find_all(["h3", "h4"])
        for heading in headings:
            heading_text = normalize_space(heading.get_text(" "))
            if not self._is_credential_heading(heading_text):
                continue
            section_text = self._section_text(heading)
            credential = heading_text
            credential_type = self._credential_type(heading_text)
            for code in self._course_codes(section_text):
                incoming = {
                    "program_credential_association": program_name,
                    "certification": credential,
                    "credential_type": credential_type,
                }
                if code in mappings:
                    mappings[code]["certification"] = merge_text(mappings[code].get("certification", ""), credential)
                    mappings[code]["credential_type"] = merge_text(mappings[code].get("credential_type", ""), credential_type)
                    mappings[code]["program_credential_association"] = merge_text(
                        mappings[code].get("program_credential_association", ""), program_name
                    )
                else:
                    mappings[code] = incoming
        return mappings

    def _section_text(self, heading):
        parts = []
        for sibling in heading.find_next_siblings():
            if sibling.name in {"h3", "h4"}:
                break
            text = normalize_space(sibling.get_text(" "))
            if text:
                parts.append(text)
        return normalize_space(" ".join(parts))

    def _course_codes(self, text):
        codes = []
        for number in re.findall(r"\bCPSC_V\s+(\d{3}[A-Z]?)\b", text):
            code = f"CPSC_V {number}"
            if code not in codes:
                codes.append(code)
        return codes

    def _is_credential_heading(self, text):
        return any(keyword in text for keyword in ["Major", "Honours", "Option", "Degree", "Minor"])

    def _credential_type(self, text):
        for credential_type in ["Honours", "Major", "Minor", "Option", "Degree"]:
            if credential_type in text:
                return credential_type
        return ""


class SFUProgramCredentialMapper(BaseCourseCatalogConnector):
    institution_slug = "sfu"

    def __init__(self, urls=None, delay_seconds=None):
        super().__init__(delay_seconds=1.5 if delay_seconds is None else delay_seconds)
        self.urls = urls or SFU_PROGRAM_URLS

    def parse(self):
        mappings = {}
        for url in self.urls:
            soup = self.fetch(url)
            mappings.update(self._parse_program_page(soup, url))
        return mappings

    def enrich(self, rows):
        mappings = self.parse()
        for row in rows:
            if row.get("institution_slug") != self.institution_slug:
                continue
            updates = mappings.get(row.get("course_code"))
            if updates:
                merge_row_values(row, updates)
        return rows

    def _parse_program_page(self, soup, url):
        program_name = self._program_name(soup)
        credential_type = "Certificate" if "certificate" in url.lower() or "Certificate" in program_name else ""
        text = normalize_space(soup.get_text(" "))
        mappings = {}
        for code in self._course_codes(text):
            mappings[code] = {
                "program_credential_association": program_name,
                "certification": f"{program_name} {credential_type}".strip(),
                "credential_type": credential_type,
            }
        return mappings

    def _program_name(self, soup):
        headings = [normalize_space(h.get_text(" ")) for h in soup.find_all("h1")]
        for heading in headings:
            if heading and "Simon Fraser University" not in heading:
                return heading
        return headings[-1] if headings else ""

    def _course_codes(self, text):
        codes = []
        for number in re.findall(r"\bCMPT\s*[-_ ]?\s*(\d{3})\b", text):
            code = f"CMPT {number}"
            if code not in codes:
                codes.append(code)
        return codes


def enrich_courses(rows, include_bcit=True, include_ubc=True, include_sfu=True):
    enrichers = []
    if include_bcit:
        enrichers.append(BCITCourseDetailEnricher())
    if include_ubc:
        enrichers.append(UBCProgramCredentialMapper())
    if include_sfu:
        enrichers.append(SFUProgramCredentialMapper())
    for enricher in enrichers:
        rows = enricher.enrich(rows)
    for row in rows:
        row["source_hash"] = build_source_hash(row)
    return rows
