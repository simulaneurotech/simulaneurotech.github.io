import fetch_simula_projects as fsp

BODY = """
<p>Intro text.</p>
<h2>Funding source:</h2>
<p>Research Council of Norway, FRINATEK</p>
<p>meg@simula.no</p>
<h2>aCleanBrain project partners</h2>
<ul><li>University of Oslo (Norway)</li><li>Oslo University Hospital (Norway)</li></ul>
<p>Contact</p>
<p>kent-and@simula.no</p>
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
        "Marie E. Rognes": "meg@simula.no",
        "Kent-Andre Mardal": "kent-and@simula.no",
    }
    names = [
        "Marie E. Rognes",
        "Kent-Andre Mardal",
        "Aslak Tveito",
        "Karoline Horgmo Jæger",
    ]
    text = "Contact: meg@simula.no. Led by Aslak Tveito with Karoline Jaeger."
    assert fsp.investigators_in(text, emails, names) == [
        "Marie E. Rognes",
        "Aslak Tveito",
        "Karoline Horgmo Jæger",
    ]
