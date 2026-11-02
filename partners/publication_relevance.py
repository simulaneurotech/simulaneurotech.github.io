"""Suggest which publications are relevant to the centre, for review by hand.

Usage: python publication_relevance.py

Reads openalex_works.csv and openalex_affiliations.csv (from
fetch_openalex.py) and writes publication_relevance.csv, one row per
publication with a suggestion (keep, review or drop) and the reason. The
decision column is filled in by hand and overrides the suggestion; decisions
and notes already in the file are kept when it is written again.

Relevant publications are core mathematical, computational or technological
research (including general data mining), or methods work with a
physiological application. Rules, in order:

1. Wireless networks or the Internet of Things in the title: drop.
2. Methods terms (model, simulation, computational, ...) and a physiological
   subject (brain, cells, heart, ...) in the title or abstract: keep.
3. Wireless networks or IoT only in the abstract, or OpenAlex's subfield
   "Computer Networks and Communications" (which it sometimes gives to
   unrelated papers): review.
4. Main research field Mathematics, Computer Science, Engineering, Physics
   and Astronomy or Decision Sciences: keep.
5. Only methods terms, or only a physiological subject: review.
6. Neither: drop.

build_partners_page.py uses a publication when its decision is "keep", or
when it has no decision and the suggestion is "keep".
"""

import csv
import re
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIELDS = [
    "result_id",
    "year",
    "title",
    "investigators",
    "primary_field",
    "primary_subfield",
    "suggestion",
    "reason",
    "decision",
    "note",
]
METHOD_FIELDS = {
    "Mathematics",
    "Computer Science",
    "Engineering",
    "Physics and Astronomy",
    "Decision Sciences",
}
WIRELESS_SUBFIELDS = {"Computer Networks and Communications"}
WIRELESS = re.compile(
    r"\b(wireless|iot|internet of things|5g|6g|lte|mmwave|radars?|antennas?|mimo|"
    r"wake-up radio|radio (?:maps?|resources?|measurements?)|software defined radio|"
    r"sensor networks?|wsns?|access points?|d2d|device-to-device|vehicular|uavs?|"
    r"beamforming|spectrum (?:cartography|sensing|sharing)|channel gain|"
    r"power cartography|scma|noma|csma|mac protocol|medium access|multicast|"
    r"cellular networks?|uplink|downlink|routing|fog computing|energy harvesting|"
    r"self-powered)\b",
    re.IGNORECASE,
)
METHODS = re.compile(
    r"\b(model\w*|simulat\w*|comput\w*|numeric\w*|mathematic\w*|finite element\w*|"
    r"algorithm\w*|machine learning|deep learning|neural networks?|optimi[sz]\w*|"
    r"estimat\w*|inverse|segmentation|image analysis|data-driven|tensors?|"
    r"decomposition\w*|statistic\w*|solvers?|discreti[sz]\w*|uncertainty quantification|"
    r"digital twins?|bayesian|inference|signal processing|software|cfd|"
    r"fluid dynamics|formalism|filter\w*|spectr\w*|quantif\w*|automated|framework)\b",
    re.IGNORECASE,
)
PHYSIOLOGY = re.compile(
    r"\b(brains?|neur\w*|cerebr\w*|spinal|csf|glymph\w*|perivascular|astrocyt\w*|"
    r"glia\w*|cardiac|cardio\w*|heart|atri\w*|ventric\w*|myocard\w*|cells?|cellular|tissues?|"
    r"blood|vascular|aneurysms?|arter\w*|electrophysiolog\w*|ions?|ionic|membranes?|"
    r"physiolog\w*|patients?|mri|imaging|eeg|ecg|cort\w*|hippocamp\w*|synap\w*|"
    r"dendrit\w*|axon\w*|sleep|stroke|epilep\w*|alzheimer\w*|dementia)\b",
    re.IGNORECASE,
)


def text_flags(title, abstract):
    """Which kinds of terms a publication's title and abstract contain, as
    "yes"/"no". fetch_openalex.py stores these flags instead of the abstract,
    which is usually copyrighted."""
    text = f"{title} {abstract}"

    def yes(found):
        return "yes" if found else "no"

    return {
        "methods_terms": yes(METHODS.search(text)),
        "physiology_terms": yes(PHYSIOLOGY.search(text)),
        "wireless_in_abstract": yes(WIRELESS.search(abstract)),
    }


def suggest(work):
    """Return (suggestion, reason) for an openalex_works.csv row."""
    methods = work["methods_terms"] == "yes"
    physiology = work["physiology_terms"] == "yes"
    if WIRELESS.search(work["title"]):
        return "drop", "wireless networks or Internet of Things"
    if methods and physiology:
        return "keep", "methods with a physiological application"
    if (
        work["wireless_in_abstract"] == "yes"
        or work["primary_subfield"] in WIRELESS_SUBFIELDS
    ):
        return "review", "mentions wireless networks or Internet of Things"
    if work["primary_field"] in METHOD_FIELDS:
        return "keep", f"core methods ({work['primary_field']})"
    if methods:
        return "review", "methods, but no physiological application found"
    if physiology:
        return "review", "physiological, but no methods found"
    return (
        "drop",
        f"outside the scope of this page ({work['primary_field'] or 'no field'})",
    )


def relevant(row):
    """True if a publication_relevance.csv row is to be used."""
    decision = row.get("decision", "").strip().lower()
    return decision == "keep" or (not decision and row["suggestion"] == "keep")


def read_csv(path):
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main():
    works = read_csv(HERE / "openalex_works.csv")
    investigators = defaultdict(str)
    for r in read_csv(HERE / "openalex_affiliations.csv"):
        investigators[r["result_id"]] = r["investigators"]
    previous = {r["result_id"]: r for r in read_csv(HERE / "publication_relevance.csv")}

    rows = []
    for w in works:
        suggestion, reason = suggest(w)
        old = previous.get(w["result_id"], {})
        rows.append(
            {
                "result_id": w["result_id"],
                "year": w["year"],
                "title": w["title"],
                "investigators": investigators[w["result_id"]],
                "primary_field": w["primary_field"],
                "primary_subfield": w["primary_subfield"],
                "suggestion": suggestion,
                "reason": reason,
                "decision": old.get("decision", ""),
                "note": old.get("note", ""),
            }
        )
    order = {"review": 0, "drop": 1, "keep": 2}
    rows.sort(
        key=lambda r: (order[r["suggestion"]], r["reason"], r["year"], r["title"])
    )
    with (HERE / "publication_relevance.csv").open(
        "w", encoding="utf-8", newline=""
    ) as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    print(Counter(r["suggestion"] for r in rows))
    print(Counter(r["reason"] for r in rows).most_common())
    print(
        f"{sum(relevant(r) for r in rows)} of {len(rows)} publications used on the page"
    )


if __name__ == "__main__":
    main()
