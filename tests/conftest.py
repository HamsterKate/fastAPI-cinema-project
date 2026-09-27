from collections.abc import Generator
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from main import app


@pytest.fixture(scope="session")
def client() -> Generator[TestClient, None, None]:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def unique_email() -> str:
    return f"test-{uuid4().hex}@example.com"
