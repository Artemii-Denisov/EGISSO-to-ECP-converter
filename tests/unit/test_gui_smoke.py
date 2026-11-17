"""Smoke and asset tests for GUI components and custom application icon."""

from __future__ import annotations

import os
import struct
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from egisso_to_ecp.presentation.gui.icon import (  # noqa: E402
    ICO_SIZES,
    ICON_SIZES,
    create_app_icon,
    write_ico_file,
)
from egisso_to_ecp.presentation.gui.main import MainWindow  # noqa: E402


def test_write_ico_file_valid_header_and_frames(tmp_path: Path) -> None:
    ico_path = tmp_path / "app_icon.ico"
    result = write_ico_file(ico_path)
    assert result == ico_path
    assert ico_path.exists()

    data = ico_path.read_bytes()
    reserved, icon_type, count = struct.unpack("<HHH", data[:6])
    assert reserved == 0
    assert icon_type == 1
    assert count == len(ICO_SIZES)
    assert len(data) > 1000


def test_app_icon_and_main_window_icon() -> None:
    app = QApplication.instance()
    if not isinstance(app, QApplication):
        app = QApplication([])

    icon = create_app_icon()
    assert not icon.isNull()
    available = {(s.width(), s.height()) for s in icon.availableSizes()}
    for size in ICON_SIZES:
        assert (size, size) in available

    window = MainWindow(initial_theme="dark")
    try:
        assert not window.windowIcon().isNull()
        assert window.tab_widget.count() == 2
        assert window.tab_widget.tabText(0) == "⚡ Конвертация"
        assert "Справочник" in window.tab_widget.tabText(1)
        assert window.table_mapping.columnCount() == 7

        # Test adding an empty row
        init_rows = window.table_mapping.rowCount()
        window._add_empty_mapping_row()
        assert window.table_mapping.rowCount() == init_rows + 1

        # Test getting rules
        rules = window._get_rules_from_table()
        assert isinstance(rules, list)
    finally:
        window.close()
