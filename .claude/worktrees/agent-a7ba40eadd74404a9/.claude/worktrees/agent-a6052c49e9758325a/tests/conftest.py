from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
import yaml

FIXTURES_ROOT = Path(__file__).resolve().parent / "fixtures"
STAR_RAIL_FIXTURES = FIXTURES_ROOT / "star_rail"
_GENERATOR = FIXTURES_ROOT / "generate_star_rail.py"


@pytest.fixture(scope="session", autouse=True)
def ensure_star_rail_fixtures() -> None:
    marker = STAR_RAIL_FIXTURES / "frames" / "main_menu.png"
    if marker.is_file():
        return
    subprocess.run([sys.executable, str(_GENERATOR)], check=True)


def load_star_rail_manifest() -> dict[str, Any]:
    path = STAR_RAIL_FIXTURES / "manifest.yaml"
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data if isinstance(data, dict) else {}


def star_rail_fixture_path(relative: str) -> Path:
    return STAR_RAIL_FIXTURES / relative
