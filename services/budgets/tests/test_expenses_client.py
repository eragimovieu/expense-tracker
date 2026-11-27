"""The call across the seam, with the expenses service replaced by a fake
requests.get. Checks that every kind of failure becomes ExpensesUnavailable."""
import time

import pytest
import requests

import expenses_client


class FakeResponse:
    def __init__(self, status=200, body=None):
        self.status_code = status
        self.body = body

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code} error")

    def json(self):
        if self.body is None:
            raise ValueError("not JSON")
        return self.body


def fake_get(response=None, error=None, delay=0):
    def get(url, params, timeout):
        get.calls.append((url, params, timeout))
        if delay:
            time.sleep(delay)
        if error:
            raise error
        return response

    get.calls = []
    return get


def test_returns_totals_as_ints(monkeypatch):
    get = fake_get(FakeResponse(body={"month": "2026-11", "totals": {"groceries": "4250"}}))
    monkeypatch.setattr(expenses_client.requests, "get", get)

    totals = expenses_client.fetch_totals("http://expenses:8001/", "2026-11", 3)

    assert totals == {"groceries": 4250}
    url, params, timeout = get.calls[0]
    assert url == "http://expenses:8001/api/expenses/totals"
    assert params == {"month": "2026-11"}
    assert timeout == 3


@pytest.mark.parametrize(
    "get",
    [
        fake_get(error=requests.ConnectionError("refused")),
        fake_get(error=requests.Timeout("too slow")),
        fake_get(FakeResponse(status=503)),
        fake_get(FakeResponse(body=None)),  # not JSON
        fake_get(FakeResponse(body={"month": "2026-11"})),  # no totals
        fake_get(FakeResponse(body={"totals": [1, 2]})),  # wrong shape
    ],
)
def test_failures_become_expenses_unavailable(monkeypatch, get):
    monkeypatch.setattr(expenses_client.requests, "get", get)
    with pytest.raises(expenses_client.ExpensesUnavailable):
        expenses_client.fetch_totals("http://expenses:8001", "2026-11", 3)


def test_gives_up_after_the_timeout_even_if_the_call_hangs(monkeypatch):
    # e.g. the DNS lookup of a stopped container, which requests' timeout doesn't cover
    monkeypatch.setattr(expenses_client.requests, "get", fake_get(delay=2))
    started = time.perf_counter()
    with pytest.raises(expenses_client.ExpensesUnavailable):
        expenses_client.fetch_totals("http://expenses:8001", "2026-11", 0.3)
    assert time.perf_counter() - started < 1
