import io
import json
import urllib.error

import pytest

import fetch_coauthor_details as fcd


def fake_server(monkeypatch, responses):
    """Answer requests from the list responses: an HTTP status code with its
    headers, or a JSON body. Returns the waits asked of time.sleep."""
    waits = []
    monkeypatch.setattr(fcd.time, "sleep", waits.append)

    def urlopen(request, timeout):
        answer = responses.pop(0)
        if isinstance(answer, tuple):
            code, headers = answer
            raise urllib.error.HTTPError(request.full_url, code, "", headers, None)
        return io.BytesIO(json.dumps(answer).encode())

    monkeypatch.setattr(fcd.urllib.request, "urlopen", urlopen)
    return waits


def test_retries_when_asked_to_slow_down(monkeypatch):
    waits = fake_server(
        monkeypatch, [(429, {"Retry-After": "2"}), (503, {}), {"ok": 1}]
    )
    assert fcd.get("https://example.org") == {"ok": 1}
    assert waits == [2, 10]


def test_stops_when_the_daily_quota_is_used_up(monkeypatch):
    # A long wait means the quota is used up: stop instead of waiting hours
    fake_server(monkeypatch, [(429, {"X-RateLimit-Reset": "8538"})])
    with pytest.raises(fcd.QuotaExceeded):
        fcd.get("https://example.org")


def test_other_errors_are_not_retried(monkeypatch):
    waits = fake_server(monkeypatch, [(404, {})])
    with pytest.raises(urllib.error.HTTPError):
        fcd.get("https://example.org")
    assert waits == []
