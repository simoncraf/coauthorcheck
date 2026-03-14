from __future__ import annotations

from pathlib import Path

import pytest


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    for item in items:
        path = Path(str(item.fspath))
        parts = set(path.parts)
        if "integration" in parts:
            item.add_marker(pytest.mark.integration)
        elif "unit" in parts:
            item.add_marker(pytest.mark.unit)
