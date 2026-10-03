import pytest

import db


@pytest.fixture
def conn():
    """A brand-new in-memory database with the real schema, for each test.

    ':memory:' means nothing is written to disk and every test starts empty,
    so tests can't affect each other or my real data/expenses.db.
    """
    connection = db.connect(":memory:")
    db.init_db(connection)
    yield connection
    connection.close()
