import pytest
from app.models.database import init_db


@pytest.fixture(autouse=True, scope="session")
def setup_test_database():
    """Initializes the SQLite schema before running test sessions."""
    init_db()
