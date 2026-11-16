"""Unit tests for directory scanner."""

from pathlib import Path

from egisso_to_ecp.infrastructure.scanner import DirectoryScanner


def test_scanner_recursive_and_non_recursive(tmp_path: Path) -> None:
    # Setup directories
    sub_dir = tmp_path / "2024" / "05"
    sub_dir.mkdir(parents=True)

    # Root files
    file_root = tmp_path / "stipend_root.xlsx"
    file_root.write_text("dummy")

    # Sub-directory files
    file_sub = sub_dir / "payments.xlsx"
    file_sub.write_text("dummy")

    # Excel temporary lock file (should be ignored)
    lock_file = tmp_path / "~$stipend_root.xlsx"
    lock_file.write_text("dummy")

    # Non-excel file (should be ignored)
    txt_file = tmp_path / "notes.txt"
    txt_file.write_text("dummy")

    # 1. Non-recursive scan
    scanner_non_rec = DirectoryScanner(recursive=False)
    results_non_rec = scanner_non_rec.scan(tmp_path)
    assert len(results_non_rec) == 1
    assert results_non_rec[0].path == file_root

    # 2. Recursive scan
    scanner_rec = DirectoryScanner(recursive=True)
    results_rec = scanner_rec.scan(tmp_path)
    assert len(results_rec) == 2
    paths = {r.path for r in results_rec}
    assert file_root in paths
    assert file_sub in paths

    # Check path hints
    sub_info = [r for r in results_rec if r.path == file_sub][0]
    assert sub_info.year_hint == 2024
    assert sub_info.month_hint == 5
