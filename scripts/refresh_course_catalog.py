import argparse
import csv
import hashlib
import re
import time
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


HEADERS = {"User-Agent": "CareerMatchingCourseCatalogBot/1.0"}
REQUEST_DELAY_SECONDS = 1.5
UBC_CPSC_URL = "https://vancouver.calendar.ubc.ca/course-descriptions/subject/cpscv"
BCIT_COMP_URLS = [
    "https://www.bcit.ca/cst",
    "https://www.bcit.ca/course_subjects/computer-systems-comp/",
]
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
COURSE_CATALOG_FIELDS = [
    "institution_slug",
    "course_code",
    "subject_code",
    "course_number",
    "title",
    "description",
    "credits",
    "prerequisites",
    "learning_outcomes",
    "program_credential_association",
    "credential_type",
    "certification",
    "course_level",
    "delivery_mode",
    "campus",
    "term_availability",
    "onet_soc_codes",
    "onet_skill_elements",
    "onet_technology_skills",
    "onet_knowledge_elements",
    "onet_work_activities",
    "onet_task_statements",
    "onet_job_zone",
    "onet_alignment_notes",
    "sparse_features",
    "course_url",
    "source_url",
    "source_hash",
]


def normalize_space(value):
    return re.sub(r"\s+", " ", value or "").strip()


def hash_course(row):
    raw = f"{row['course_code']}|{row['title']}|{row['description']}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


def fetch(url):
    response = requests.get(url, headers=HEADERS, timeout=20)
    response.raise_for_status()
    time.sleep(REQUEST_DELAY_SECONDS)
    return BeautifulSoup(response.text, "html.parser")


def parse_bcit():
    rows = {}
    for source_url in BCIT_COMP_URLS:
        soup = fetch(source_url)
        for course_number_cell in soup.find_all("td", class_="course_number"):
            code_text = normalize_space(course_number_cell.get_text(" "))
            match = re.match(r"^(COMP)\s+(\d{4})$", code_text)
            if not match:
                continue
            subject, number = match.groups()
            row = course_number_cell.find_parent("tr")
            detail_cell = row.find("td", class_="peekaboo") if row else None
            title_node = detail_cell.find("strong", class_="course_name") if detail_cell else None
            summary_node = detail_cell.find("div", class_="course_summary") if detail_cell else None
            credits_node = row.find("td", class_="credits") if row else None
            title = normalize_space(title_node.get_text(" ")) if title_node else ""
            description = normalize_space(summary_node.get_text(" ")) if summary_node else title
            course_code = f"{subject} {number}"
            if title:
                rows[course_code] = {
                    "institution_slug": "bcit",
                    "course_code": course_code,
                    "subject_code": subject,
                    "course_number": number,
                    "title": title[:255],
                    "description": description,
                    "credits": normalize_space(credits_node.get_text(" ")) if credits_node else "",
                    "course_url": source_url,
                    "source_url": source_url,
                }
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
            rows[course_code] = {
                "institution_slug": "bcit",
                "course_code": course_code,
                "subject_code": subject,
                "course_number": number,
                "title": title[:255],
                "description": title,
                "credits": "",
                "course_url": course_url,
                "source_url": source_url,
            }
    return list(rows.values())


def parse_ubc():
    soup = fetch(UBC_CPSC_URL)
    rows = []
    headings = soup.find_all(["h3", "h4"])
    for heading in headings:
        heading_text = normalize_space(heading.get_text(" "))
        match = re.match(r"^(CPSC_V)\s+(\d{3}[A-Z]?)\s+\(([\d.]+)\)\s+(.+)$", heading_text)
        if not match:
            continue
        subject, number, credits, title = match.groups()
        description_parts = []
        for sibling in heading.find_next_siblings():
            if sibling.name in {"h3", "h4"}:
                break
            text = normalize_space(sibling.get_text(" "))
            if text:
                description_parts.append(text)
        row = {
            "institution_slug": "ubc",
            "course_code": f"{subject} {number}",
            "subject_code": subject,
            "course_number": number,
            "title": title,
            "description": normalize_space(" ".join(description_parts)) or title,
            "credits": credits,
            "course_url": UBC_CPSC_URL,
            "source_url": UBC_CPSC_URL,
        }
        rows.append(row)
    return rows


def parse_sfu():
    rows = []
    for number in SFU_CMPT_NUMBERS:
        source_url = SFU_CMPT_URL_TEMPLATE.format(number=number)
        soup = fetch(source_url)
        h1 = None
        match = None
        for candidate in soup.find_all("h1"):
            h1_text = normalize_space(candidate.get_text(" "))
            match = re.match(r"^(.*?)\s+CMPT\s+(\d{3})\s+\(([\d.]+)\)$", h1_text)
            if match:
                h1 = candidate
                break
        if not match:
            page_text = normalize_space(soup.get_text(" "))
            match = re.search(r"#?\s*(.*?)\s+CMPT\s+(\d{3})\s+\(([\d.]+)\)", page_text)
        if not match:
            continue
        title, parsed_number, credits = match.groups()
        description = ""
        if h1:
            for sibling in h1.find_next_siblings():
                text = normalize_space(sibling.get_text(" "))
                if text and not text.startswith("Section "):
                    description = text
                    break
        rows.append(
            {
                "institution_slug": "sfu",
                "course_code": f"CMPT {parsed_number}",
                "subject_code": "CMPT",
                "course_number": parsed_number,
                "title": normalize_space(title),
                "description": description or normalize_space(title),
                "credits": credits,
                "course_url": source_url,
                "source_url": source_url,
            }
        )
    return rows


def write_courses(rows, output_path):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=COURSE_CATALOG_FIELDS)
        writer.writeheader()
        for row in sorted(rows, key=lambda item: (item["institution_slug"], item["course_code"])):
            row = {
                **{field: "" for field in COURSE_CATALOG_FIELDS},
                "onet_soc_codes": "[]",
                "onet_skill_elements": "[]",
                "onet_technology_skills": "[]",
                "onet_knowledge_elements": "[]",
                "onet_work_activities": "[]",
                "onet_task_statements": "[]",
                "sparse_features": "{}",
                **row,
                "source_hash": hash_course(row),
            }
            writer.writerow(row)


def main():
    parser = argparse.ArgumentParser(description="Refresh allowlisted official course catalog pages.")
    parser.add_argument("--output", default="data/scraped_course_catalog.csv")
    parser.add_argument("--include-bcit", action="store_true")
    parser.add_argument("--include-ubc", action="store_true")
    parser.add_argument("--include-sfu", action="store_true")
    args = parser.parse_args()

    include_all = not (args.include_bcit or args.include_ubc or args.include_sfu)
    rows = []
    if include_all or args.include_bcit:
        rows.extend(parse_bcit())
    if include_all or args.include_ubc:
        rows.extend(parse_ubc())
    if include_all or args.include_sfu:
        rows.extend(parse_sfu())

    write_courses(rows, Path(args.output))
    print(f"Wrote {len(rows)} scraped course rows to {args.output}.")


if __name__ == "__main__":
    main()
