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


def test_scanner_excludes_output_dir_and_generated_reports(tmp_path: Path) -> None:
    in_dir = tmp_path / "data"
    out_dir = in_dir / "output"
    out_dir.mkdir(parents=True)

    src_file = in_dir / "registry.xlsx"
    src_file.write_text("dummy")

    report_file = in_dir / "errors_report.xlsx"
    report_file.write_text("dummy")

    pkg_file = in_dir / "Пакет_Решений_2026-11_uuid.xlsx"
    pkg_file.write_text("dummy")

    out_nested_file = out_dir / "custom.xlsx"
    out_nested_file.write_text("dummy")

    scanner = DirectoryScanner(recursive=True)
    results = scanner.scan(in_dir, exclude_dir=out_dir)

    assert len(results) == 1
    assert results[0].path == src_file
