"""Build the projects page from the curated projects.

Usage: python build_projects_page.py [output.html]

Writes ../site/projects.html by default, a page on the website next to the
overview page, which loads its fonts and scripts from ../site/assets.

Reads centre_projects.csv (curated by hand; rows with include = "no" and
projects that started before FIRST_PROJECT_YEAR are left out; the column
short gives a short name where the title's own is not suitable) and fills
projects_page_template.html. Funding amounts and project partners are left
out (LEFT_OUT).
"""

import datetime
import json
import sys
from pathlib import Path

from build_partners_page import FIRST_PROJECT_YEAR, fetch_dates, projects, read_csv

HERE = Path(__file__).resolve().parent
TEMPLATE = HERE / "projects_page_template.html"
OUTPUT = HERE.parent / "site" / "projects.html"


# Left out of the page: funding amounts, and the project partners, which are
# still to be verified
LEFT_OUT = ("partners", "rcn")


def collect(here=HERE):
    return {
        "generated": datetime.date.today().isoformat(),
        "fetched": fetch_dates(here),
        "firstYear": FIRST_PROJECT_YEAR,
        "projects": [
            {k: v for k, v in p.items() if k not in LEFT_OUT}
            for p in projects(read_csv(here / "centre_projects.csv"))
        ],
    }


def main():
    output = Path(sys.argv[1]) if len(sys.argv) > 1 else OUTPUT
    data = collect()
    html = TEMPLATE.read_text(encoding="utf-8").replace(
        "__DATA__", json.dumps(data, ensure_ascii=False)
    )
    output.write_text(html, encoding="utf-8")
    status = [p["status"] for p in data["projects"]]
    print(
        f"{output.name}: {status.count('active')} active, "
        f"{status.count('upcoming')} upcoming and {status.count('ended')} ended "
        "projects"
    )


if __name__ == "__main__":
    main()
