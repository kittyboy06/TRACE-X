import pytest
import json
import hashlib
from pathlib import Path
from app.models.database import init_db

BENCHMARK_DIR = Path(__file__).parent.parent / "app" / "data"
CASE_1_EXPECTED_HASH = "c6f630533dea5cc30a0414b380556875d87fc80178037a062ec727493993e8ec"
CASE_2_EXPECTED_HASH = "df1a5f8e52a5bed6aeac9559476acbfb0d69a41a9b22fc5a75ebcd1b8a7880df"


@pytest.fixture(autouse=True, scope="session")
def setup_test_database():
    """Initializes the SQLite schema before running test sessions."""
    init_db()


@pytest.fixture(scope="session")
def frozen_benchmark_case_1() -> dict:
    """Loads and verifies frozen ground truth for Case 1 (Multi-Modal Convergence)."""
    file_path = BENCHMARK_DIR / "benchmark_case_1.json"
    content = file_path.read_bytes()
    computed_hash = hashlib.sha256(content).hexdigest()
    assert computed_hash == CASE_1_EXPECTED_HASH, (
        f"Benchmark Case 1 integrity check failed! Expected {CASE_1_EXPECTED_HASH}, got {computed_hash}"
    )
    return json.loads(content.decode("utf-8"))


@pytest.fixture(scope="session")
def frozen_benchmark_case_2() -> dict:
    """Loads and verifies frozen ground truth for Case 2 (Anti-False-Positive Contradiction)."""
    file_path = BENCHMARK_DIR / "benchmark_case_2.json"
    content = file_path.read_bytes()
    computed_hash = hashlib.sha256(content).hexdigest()
    assert computed_hash == CASE_2_EXPECTED_HASH, (
        f"Benchmark Case 2 integrity check failed! Expected {CASE_2_EXPECTED_HASH}, got {computed_hash}"
    )
    return json.loads(content.decode("utf-8"))


@pytest.fixture(scope="session")
def canonical_weights() -> dict:
    """Returns canonical frozen attribution weights summing to 1.0."""
    return {
        "CRYPTOGRAPHIC": 0.30,
        "FINANCIAL": 0.25,
        "STYLOMETRIC": 0.20,
        "INFRASTRUCTURE": 0.15,
        "BEHAVIORAL_TEMPORAL": 0.10,
    }
