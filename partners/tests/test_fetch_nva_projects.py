import fetch_nva_projects as fnp

PROJECT = {
    "id": "https://api.nva.unit.no/cristin/project/123",
    "title": "SURE-AI",
    "startDate": "2025-01-01T00:00:00Z",
    "endDate": "2030-12-31T00:00:00Z",
    "funding": [
        {
            "source": "https://api.nva.unit.no/cristin/funding-sources/NFR",
            "identifier": "357482",
            "labels": {"en": "Research Council of Norway (RCN)"},
        }
    ],
    "coordinatingInstitution": {"labels": {"en": "Simula"}},
    "contributors": [
        {
            "identity": {
                "id": "https://api.nva.unit.no/cristin/person/588528",
                "firstName": "Baltasar",
                "lastName": "Beferull-Lozano",
            },
            "roles": [
                {
                    "type": "ProjectManager",
                    "affiliation": {
                        "id": "https://api.nva.unit.no/cristin/organization/7498.10.0.0",
                        "labels": {"en": "SimulaMet"},
                    },
                }
            ],
        }
    ],
}


def test_project_row_and_participants():
    row = fnp.to_row(PROJECT, ["Baltasar Beferull-Lozano"])
    assert row == {
        "nva_project_id": "123",
        "title": "SURE-AI",
        "start": "2025",
        "end": "2030",
        "funding": "Research Council of Norway (RCN) 357482",
        "coordinator": "Simula",
        "n_participants": 1,
        "investigators": "Baltasar Beferull-Lozano",
    }
    assert fnp.participants(PROJECT) == [
        {
            "nva_project_id": "123",
            "cristin_person_id": "588528",
            "name": "Baltasar Beferull-Lozano",
            "role": "ProjectManager",
            "institution_id": "7498",
            "institution": "SimulaMet",
            "unit": "SimulaMet",
        }
    ]
    # With institution names, the unit is replaced by its institution
    assert fnp.participants(PROJECT, {"7498": "Simula"})[0]["institution"] == "Simula"
