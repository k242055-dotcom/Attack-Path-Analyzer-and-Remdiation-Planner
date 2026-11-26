"""Shared project-relative paths for bundled inputs and experiment artifacts."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
CHECKED_DIR = DATA_DIR / "scenarios" / "checked"
GENERATED_DIR = DATA_DIR / "scenarios" / "generated"
RESULTS_DIR = PROJECT_ROOT / "outputs" / "results"
FIGURES_DIR = PROJECT_ROOT / "outputs" / "figures"


def bundled_scenarios() -> tuple[Path, ...]:
    """List checked cases first, then generated cases, in filename order."""
    return tuple(sorted(CHECKED_DIR.glob("*.json"))) + tuple(sorted(GENERATED_DIR.glob("*.json")))
