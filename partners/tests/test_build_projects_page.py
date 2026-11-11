"""The projects page needs no co-author data, so this check also runs on
GitHub."""

import json
import re

import build_projects_page as bpp


def test_projects_page_is_up_to_date():
    # Project statuses follow the date, so this fails on the day a project
    # starts or ends, until the pages are rebuilt (../refresh.sh --no-fetch)
    page = bpp.OUTPUT.read_text(encoding="utf-8")
    committed = json.loads(
        re.search(r"^const DATA = (.*);$", page, re.MULTILINE).group(1)
    )
    data = json.loads(json.dumps(bpp.collect(), ensure_ascii=False))
    committed.pop("generated")
    data.pop("generated")
    assert data == committed
