import re
from urllib.parse import urljoin

from course_catalog.connectors.base import BaseCourseCatalogConnector, extract_prerequisites, normalize_space


BCIT_COMP_URLS = [
    "https://www.bcit.ca/cst",
    "https://www.bcit.ca/course_subjects/computer-systems-comp/",
]


class BCITCourseCatalogConnector(BaseCourseCatalogConnector):
    institution_slug = "bcit"

    def __init__(self, urls=None, delay_seconds=None):
        super().__init__(delay_seconds=1.5 if delay_seconds is None else delay_seconds)
        self.urls = urls or BCIT_COMP_URLS

    def parse(self):
        rows = {}
        for source_url in self.urls:
            soup = self.fetch(source_url)
            program_metadata = self._program_metadata(soup)
            self._merge_rows(rows, self._parse_program_matrix(soup, source_url, program_metadata))
            self._merge_rows(rows, self._parse_subject_listing(soup, source_url, program_metadata))
        return list(rows.values())

    def _merge_rows(self, target, incoming):
        for course_code, row in incoming.items():
            if course_code not in target:
                target[course_code] = row
                continue
            existing = target[course_code]
            for field, value in row.items():
                if not existing.get(field) and value:
                    existing[field] = value

    def _program_metadata(self, soup):
        page_text = normalize_space(soup.get_text(" "))
        program_title = normalize_space(soup.find("h1").get_text(" ")) if soup.find("h1") else ""
        credential = self._extract_label(page_text, "Credential", stop_labels=["Format", "Intakes"])
        delivery = self._extract_label(page_text, "Program delivery", stop_labels=["Campus", "Domestic tuition"])
        campus = self._extract_label(page_text, "Campus", stop_labels=["Domestic tuition", "International tuition"])
        intakes = self._extract_label(page_text, "Intakes", stop_labels=["Program delivery", "Campus"])
        return {
            "program_credential_association": program_title,
            "credential_type": credential,
            "delivery_mode": delivery,
            "campus": campus,
            "term_availability": intakes,
        }

    def _parse_program_matrix(self, soup, source_url, metadata):
        table = soup.find("table", id="programmatrix")
        if not table:
            return {}

        rows = {}
        current_level = ""
        for table_row in table.find_all("tr"):
            row_text = normalize_space(table_row.get_text(" "))
            level_match = re.search(r"((?:First|Second) Year - Level \d[A-Z]?|Level \d[A-Z]?)", row_text)
            if level_match and not table_row.find("td", class_="course_number"):
                current_level = level_match.group(1)
                continue

            course_number_cell = table_row.find("td", class_="course_number")
            if not course_number_cell:
                continue
            code_text = normalize_space(course_number_cell.get_text(" "))
            match = re.match(r"^(COMP)\s+(\d{4})$", code_text)
            if not match:
                continue

            subject, number = match.groups()
            detail_cell = table_row.find("td", class_="peekaboo")
            title_node = detail_cell.find("strong", class_="course_name") if detail_cell else None
            summary_node = detail_cell.find("div", class_="course_summary") if detail_cell else None
            credits_node = table_row.find("td", class_="credits")
            title = normalize_space(title_node.get_text(" ")) if title_node else ""
            description = normalize_space(summary_node.get_text(" ")) if summary_node else title
            course_code = f"{subject} {number}"
            if not title:
                continue

            rows[course_code] = self.record(
                course_code=course_code,
                subject_code=subject,
                course_number=number,
                title=title[:255],
                description=description,
                credits=normalize_space(credits_node.get_text(" ")) if credits_node else "",
                prerequisites=extract_prerequisites(description),
                course_level=current_level,
                course_url=source_url,
                source_url=source_url,
                **metadata,
            )
        return rows

    def _parse_subject_listing(self, soup, source_url, metadata):
        rows = {}
        for heading in soup.find_all("h3"):
            heading_text = normalize_space(heading.get_text(" "))
            match = re.search(r"\((COMP)\s+(\d{4})\)", heading_text)
            if not match:
                continue
            subject, number = match.groups()
            course_code = f"{subject} {number}"
            title = re.sub(r"\s*\(COMP\s+\d{4}\)\s*$", "", heading_text).strip()
            link = heading.find("a")
            course_url = urljoin(source_url, link["href"]) if link and link.get("href") else source_url
            if not title:
                continue
            rows[course_code] = self.record(
                course_code=course_code,
                subject_code=subject,
                course_number=number,
                title=title[:255],
                description=title,
                course_level=f"{number[0]}000-level",
                course_url=course_url,
                source_url=source_url,
                **metadata,
            )
        return rows

    def _extract_label(self, page_text, label, stop_labels):
        stop_pattern = "|".join(re.escape(stop) for stop in stop_labels)
        match = re.search(rf"{re.escape(label)}\s*:\s*(.*?)(?=\s+(?:{stop_pattern})\s*:|$)", page_text)
        return normalize_space(match.group(1)) if match else ""
