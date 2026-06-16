"""Smoke tests para hermes-orchestrator."""
import pytest
from pathlib import Path


def test_skills_dir_exists():
    """skills/ deve existir e ter orchestrator skills."""
    skills_dir = Path(__file__).parent.parent / "skills"
    assert skills_dir.exists()
    skills = [d for d in skills_dir.iterdir() if d.is_dir()]
    assert len(skills) > 0
