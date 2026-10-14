"""License-choice approval must not silently clear release authorization."""
import importlib.util
from pathlib import Path

import pytest


spec = importlib.util.spec_from_file_location(
    "release_check", Path(__file__).resolve().parents[1] / "scripts/check_release.py")
release_check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release_check)


def release_fields():
    # Fictional test data; not a statement about this project's copyright holder.
    return dict(
        license_text="BSD 3-Clause License\nCopyright (c) 2026, Example Author\n",
        readme="Example released package",
        metadata='license = "BSD-3-Clause"\n',
        notice="Ownership confirmation: confirmed.\nPublication approval: confirmed.\n",
    )


def test_complete_recorded_markers():
    assert release_check.release_marker_errors(**release_fields()) == []


@pytest.mark.parametrize("field,value,expected", [
    ("license_text", "", "text has not been supplied"),
    ("license_text", "Copyright (c) 2026, [COPYRIGHT HOLDER TO BE CONFIRMED]\n", "placeholder"),
    ("readme", "Local draft — not released", "unreleased local draft"),
    ("metadata", 'license = "MIT"\n', "BSD-3-Clause license metadata missing"),
    ("notice", "Ownership confirmation: pending.\nPublication approval: confirmed.\n", "ownership confirmation"),
    ("notice", "Ownership confirmation: confirmed.\nPublication approval: pending.\n", "publication approval"),
    ("notice", "", "not recorded as confirmed"),
])
def test_missing_or_pending_release_markers(field, value, expected):
    fields = release_fields()
    fields[field] = value
    assert any(expected in error for error in release_check.release_marker_errors(**fields))
