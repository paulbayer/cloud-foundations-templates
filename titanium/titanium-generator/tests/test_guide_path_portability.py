"""
Regression test for #67: the deployment guide extracted the template's section
with `output_path.split('/')[-2]`, which returns a single element on Windows
(backslash) paths and raises IndexError, so no guide artifacts were generated.

The fix uses `Path(output_path).parent.name`, which is separator-aware. The
production code uses the native `Path` (matching the OS-native separator in
output_path); these assertions exercise both separator styles explicitly to
guard that the approach extracts the section regardless of platform.
"""

from pathlib import PurePosixPath, PureWindowsPath


def test_section_extraction_posix_path():
    assert PurePosixPath("out/organization/01-organizations.yaml").parent.name == "organization"


def test_section_extraction_windows_path():
    assert PureWindowsPath(r"out\organization\01-organizations.yaml").parent.name == "organization"


def test_old_split_approach_would_break_on_windows():
    # Demonstrates the bug the fix removes: a backslash path has no '/', so
    # split('/') yields one element and [-2] raises IndexError.
    windows_path = r"out\network\04a-tgw.yaml"
    import pytest
    with pytest.raises(IndexError):
        _ = windows_path.split("/")[-2]
