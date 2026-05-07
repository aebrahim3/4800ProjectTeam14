import argparse
import csv
from pathlib import Path

from course_catalog.connectors.bcit import BCITCourseCatalogConnector
from course_catalog.connectors.enrichment import enrich_courses
from course_catalog.connectors.sfu import SFUCourseCatalogConnector
from course_catalog.connectors.ubc import UBCCourseCatalogConnector
from course_catalog.fields import COURSE_CATALOG_FIELDS


def selected_connectors(args):
    include_all = not (args.include_bcit or args.include_ubc or args.include_sfu)
    connectors = []
    if include_all or args.include_bcit:
        connectors.append(BCITCourseCatalogConnector())
    if include_all or args.include_ubc:
        connectors.append(UBCCourseCatalogConnector())
    if include_all or args.include_sfu:
        connectors.append(SFUCourseCatalogConnector())
    return connectors


def write_courses(rows, output_path):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    deduped = {}
    for row in rows:
        deduped[(row["institution_slug"], row["course_code"])] = row

    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=COURSE_CATALOG_FIELDS)
        writer.writeheader()
        for row in sorted(deduped.values(), key=lambda item: (item["institution_slug"], item["course_code"])):
            writer.writerow({field: row.get(field, "") for field in COURSE_CATALOG_FIELDS})


def main():
    parser = argparse.ArgumentParser(description="Refresh allowlisted official course catalog pages.")
    parser.add_argument("--output", default="data/scraped_course_catalog.csv")
    parser.add_argument("--include-bcit", action="store_true")
    parser.add_argument("--include-ubc", action="store_true")
    parser.add_argument("--include-sfu", action="store_true")
    parser.add_argument("--enrich", action="store_true", help="Fetch compact detail/program pages for outcomes and credentials.")
    args = parser.parse_args()

    rows = []
    for connector in selected_connectors(args):
        rows.extend(connector.parse())
    if args.enrich:
        include_all = not (args.include_bcit or args.include_ubc or args.include_sfu)
        rows = enrich_courses(
            rows,
            include_bcit=include_all or args.include_bcit,
            include_ubc=include_all or args.include_ubc,
            include_sfu=include_all or args.include_sfu,
        )

    write_courses(rows, Path(args.output))
    print(f"Wrote {len(rows)} scraped course rows to {args.output}.")


if __name__ == "__main__":
    main()
