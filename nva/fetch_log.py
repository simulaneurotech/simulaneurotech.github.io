"""When each source of data was last fetched.

The fetch scripts call record() when they have written their data; the page
builders read the dates with read() and show them on the pages. A folder's
fetched.csv has one row per source: its name and the date (YYYY-MM-DD).
"""

import csv
import datetime
from pathlib import Path

FIELDS = ["source", "fetched"]


def read(path):
    """{source: date} from path, or {} if there is no such file."""
    path = Path(path)
    if not path.exists():
        return {}
    with path.open(encoding="utf-8", newline="") as f:
        return {r["source"]: r["fetched"] for r in csv.DictReader(f)}


def record(path, source, day=None):
    """Set the date source was fetched (today unless day is given) in path,
    keeping the other sources' dates."""
    dates = read(path)
    dates[source] = day or datetime.date.today().isoformat()
    with Path(path).open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(FIELDS)
        writer.writerows(sorted(dates.items()))
