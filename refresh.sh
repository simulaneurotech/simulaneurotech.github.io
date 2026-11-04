#!/usr/bin/env bash
# Refresh the publication data and rebuild the pages in site/.
#
# Usage: ./refresh.sh [--no-fetch]
#
# Fetches the investigators' publications from NVA, their co-authors'
# institutions from OpenAlex, and details about the co-authors at universities
# from OpenAlex and ORCID, rebuilds the pages, runs the tests and
# prints the key figures before and after. With --no-fetch, the pages are
# rebuilt from the data already in the repository.
#
# Nothing is committed: check the changes (git diff, in particular the review
# files written by nva/publication_data.py and any new institutions to merge
# or exclude in partners/), then commit and push to publish.

set -euo pipefail

fetch=yes
for arg in "$@"; do
    case "$arg" in
        --no-fetch) fetch=no ;;
        *) echo "Usage: $0 [--no-fetch]" >&2; exit 2 ;;
    esac
done

cd "$(dirname "$0")"
python=${PYTHON:-python3}

# Key figures from the built pages, one line per period
figures() {
    "$python" - <<'EOF'
import json
import re
from pathlib import Path


def data(page):
    path = Path("site") / page
    if not path.exists():
        return None
    m = re.search(r"^const DATA = (.*);$", path.read_text(encoding="utf-8"), re.M)
    return json.loads(m.group(1))


centre = data("index.html")
coauthorship = data("coauthorship.html")
for start, f in (centre or {}).get("figures", {}).items():
    print(
        f"  since {start}: {f['publications']} publications, "
        f"{f['coauthors']} co-authors, {f['institutions']} institutions, "
        f"{f['countries']} countries"
    )
if coauthorship:
    print(
        f"  {len(coauthorship['papers'])} publications with 2+ investigators, "
        f"{len(coauthorship['pairs'])} pairs"
    )
EOF
}

before=$(figures)

echo "== Publications (nva/)"
cd nva
if [ "$fetch" = yes ]; then
    "$python" fetch_nva.py
fi
"$python" publication_data.py
"$python" coauthorship.py
"$python" external_collaborators.py
"$python" collaboration_map.py
cd ..

echo "== Co-authors' institutions (partners/)"
cd partners
if [ "$fetch" = yes ]; then
    "$python" fetch_openalex.py
    "$python" fetch_coauthor_details.py
fi
"$python" build_partners_page.py
"$python" build_projects_page.py
cd ..

echo "== Overview page (centre/)"
cd centre
"$python" build_centre_page.py
cd ..

# Pages whose only change is the date they were generated are put back, so
# that a refresh without new data changes nothing
if git rev-parse --git-dir >/dev/null 2>&1; then
    undate() { sed -E 's/"generated": "[0-9]{4}-[0-9]{2}-[0-9]{2}"/"generated": ""/'; }
    for f in $(git diff --name-only -- site); do
        if cmp -s <(git show "HEAD:$f" | undate) <(undate <"$f"); then
            git checkout -q -- "$f"
        fi
    done
fi

echo "== Tests"
for d in nva partners centre; do
    (cd "$d" && "$python" -m pytest -q -p no:cacheprovider)
done

echo "== Key figures"
echo "Before:"
echo "${before:-  (no pages yet)}"
echo "After:"
figures
