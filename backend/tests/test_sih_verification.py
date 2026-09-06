import os
import sys
from pathlib import Path

# Ensure root directory is accessible to import scripts
root_dir = Path(__file__).parent.parent.parent
scripts_dir = root_dir / "scripts"
if str(scripts_dir) not in sys.path:
    sys.path.insert(0, str(scripts_dir))

from verify_sih_submission import run_all_checkpoints


def test_sih_acceptance_checkpoints():
    """
    Asserts that all 10 TRACE-X SIH Acceptance Checkpoints pass sequentially.
    Enforces cross-phase consistency, 10MB input boundaries, Decision #10/#11/#12 invariants,
    and dossier reconstruction integrity.
    """
    success = run_all_checkpoints()
    assert success is True, "TRACE-X SIH acceptance verification failed on one or more checkpoints"
