"""Shared test setup. The suite runs as the laptop demo does (KINCARE_DEMO=1, an admin token); test_security.py checks
that without them login codes, unsigned webhooks and admin stay closed."""
import os

import pytest

os.environ.setdefault("KINCARE_DEMO", "1")
os.environ.setdefault("ADMIN_TOKEN", "test-admin-token")
ADMIN = {"X-Admin-Token": os.environ["ADMIN_TOKEN"]}


@pytest.fixture(autouse=True)
def _fresh_rate_limits():
    """Every test comes from the same "IP" (testclient); limits must not carry over from earlier tests."""
    import core

    core._hits.clear()
    yield
