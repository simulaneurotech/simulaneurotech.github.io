import fetch_simula_projects as fsp

BODY = """
<p>Intro text.</p>
<h2>Funding source:</h2>
<p>Research Council of Norway, FRINATEK</p>
<p>kari@example.org</p>
<h2>aCleanBrain project partners</h2>
<ul><li>University of Oslo (Norway)</li><li>Oslo University Hospital (Norway)</li></ul>
<p>Contact</p>
<p>per-arne@example.org</p>
<h3>Media</h3>
<p>Not a section we read.</p>
"""


def test_sections_read_funding_and_partners():
    found = fsp.sections(BODY)
    # Email addresses are dropped; partners stop at the "Contact" line
    assert found["funding"] == ["Research Council of Norway, FRINATEK"]
    assert found["partners"] == [
        "University of Oslo (Norway)",
        "Oslo University Hospital (Norway)",
    ]


def test_investigators_found_by_email_or_name():
    emails = {
        "Kari T. Lunde": "kari@example.org",
        "Per-Arne Lund": "per-arne@example.org",
    }
    names = [
        "Kari T. Lunde",
        "Per-Arne Lund",
        "Odd Vik",
        "Siri Holm Sæther",
    ]
    text = "Contact: kari@example.org. Led by Odd Vik with Siri Saether."
    assert fsp.investigators_in(text, emails, names) == [
        "Kari T. Lunde",
        "Odd Vik",
        "Siri Holm Sæther",
    ]
