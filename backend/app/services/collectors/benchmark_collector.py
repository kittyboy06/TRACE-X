import json
import hashlib
from pathlib import Path
from typing import Dict, Any

from app.services.collectors.base_collector import BaseCollector

CASE_1_EXPECTED_HASH = "c6f630533dea5cc30a0414b380556875d87fc80178037a062ec727493993e8ec"
CASE_2_EXPECTED_HASH = "df1a5f8e52a5bed6aeac9559476acbfb0d69a41a9b22fc5a75ebcd1b8a7880df"

BENCHMARK_REGISTRY = {
    "1": ("benchmark_case_1.json", CASE_1_EXPECTED_HASH),
    "case_1": ("benchmark_case_1.json", CASE_1_EXPECTED_HASH),
    "2": ("benchmark_case_2.json", CASE_2_EXPECTED_HASH),
    "case_2": ("benchmark_case_2.json", CASE_2_EXPECTED_HASH),
}


class BenchmarkCollector(BaseCollector):
    """
    Collector for frozen SIH ground truth benchmark datasets.
    Cryptographically verifies the integrity of the benchmark package
    against the locked Phase 0 SHA-256 anchors before releasing it.
    """

    def __init__(self, data_dir: Path = None):
        self.data_dir = data_dir or (Path(__file__).parent.parent.parent / "data")

    def collect(self, source_descriptor: Dict[str, Any]) -> Dict[str, Any]:
        case_id = str(source_descriptor.get("case_id", "")).strip().lower()
        if case_id not in BENCHMARK_REGISTRY:
            raise ValueError(
                f"Unknown benchmark case '{case_id}'. Allowed cases: {sorted(list(BENCHMARK_REGISTRY.keys()))}"
            )

        filename, expected_hash = BENCHMARK_REGISTRY[case_id]
        filepath = self.data_dir / filename
        if not filepath.exists():
            raise FileNotFoundError(f"Benchmark file not found at: {filepath}")

        content_bytes = filepath.read_bytes()
        computed_hash = hashlib.sha256(content_bytes).hexdigest()

        if computed_hash != expected_hash:
            raise ValueError(
                f"Benchmark file '{filename}' integrity check failed! "
                f"Expected SHA-256 '{expected_hash}', got '{computed_hash}'."
            )

        return json.loads(content_bytes.decode("utf-8"))
