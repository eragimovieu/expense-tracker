"""The only place where the budgets service talks to the expenses service.

In A1 this was a function call, expenses.service.totals_by_category(conn,
month). Now it's GET {EXPENSES_URL}/api/expenses/totals?month=YYYY-MM, which
answers {"month": "2026-11", "totals": {"groceries": 4250}} (ADR-6).

Every call has a time limit, so a slow or stopped expenses service can't make
a budgets request hang. requests' own timeout doesn't cover looking up the
host name, and when the expenses container is stopped that lookup alone can
take many seconds. So the call runs in a worker thread and we wait for it at
most EXPENSES_TIMEOUT_S in total. Any failure becomes ExpensesUnavailable, and
the route decides what the user gets instead.
"""
import logging
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as CallTimedOut

import requests

log = logging.getLogger("expenses_client")

# A few threads for the calls. A call that is stuck on a name lookup finishes
# in the background; the request that started it has already moved on.
_calls = ThreadPoolExecutor(max_workers=4, thread_name_prefix="expenses-call")


class ExpensesUnavailable(Exception):
    """The expenses service didn't answer in time, or answered with an error."""


def _get_totals(url, month, timeout_s):
    response = requests.get(url, params={"month": month}, timeout=timeout_s)
    response.raise_for_status()
    return response.json()["totals"]


def fetch_totals(base_url, month, timeout_s):
    url = f"{base_url.rstrip('/')}/api/expenses/totals"
    call = _calls.submit(_get_totals, url, month, timeout_s)
    try:
        totals = call.result(timeout=timeout_s)
    except CallTimedOut:
        log.warning("Expenses service unavailable (%s): no answer within %ss", url, timeout_s)
        raise ExpensesUnavailable(f"no answer within {timeout_s}s") from None
    except (requests.RequestException, ValueError, KeyError, TypeError) as err:
        log.warning("Expenses service unavailable (%s): %s", url, err)
        raise ExpensesUnavailable(str(err)) from err

    if not isinstance(totals, dict):
        raise ExpensesUnavailable("totals is not an object")
    return {category: int(cents) for category, cents in totals.items()}
