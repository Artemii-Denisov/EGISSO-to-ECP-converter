"""GIS ECP Excel (.xlsx) writer with native cell typing and visual structure."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from egisso_to_ecp.domain.models import EcpPackage
from egisso_to_ecp.infrastructure.writers.ecp_schema import (
    COL_INDEX,
    ECP_COLUMNS,
    build_package_rows,
)

logger = logging.getLogger(__name__)

_DECIMAL_COLUMNS: frozenset[str] = frozenset(
    col
    for col in ECP_COLUMNS
    if col.endswith(("СуммаКоличество", "ДенежныйЭквивалент"))
)

_INT_COLUMNS: frozenset[str] = frozenset(
    {
        "ПоставщикИнформации",
        "КоличествоЗаписей",
        "Решение_ТипДокумента",
        "Решение_ОНМСЗ_ИдентификаторОНМСЗ",
        "Решение_ОНМСЗ_РеквизитыОНМСЗ_ИНН",
        "Решение_ОНМСЗ_РеквизитыОНМСЗ_КПП",
        "Решение_ОНМСЗ_РеквизитыОНМСЗ_ОГРН",
        "Решение_КодМСЗ",
        "Решение_ТипДействия",
        "Решение_ИДМерыЕЦП",
        "Решение_СведенияОНазначении_ОснованиеРешения",
        "Решение_СведенияОНазначении_ИДЗаявления",
        "Решение_СведенияОНазначении_ФормаПредоставления",
        "Решение_СведенияОНазначении_ПериодичностьПредоставления",
        "Решение_СведенияОНазначении_ИсточникФинансирования",
        "Решение_СведенияОНазначении_ПериодыНазначения_ЕдИзмерения",
        "Решение_СведенияОНазначении_ИДМеры",
        "Решение_СведенияОНазначении_КодРегиона",
        "Решение_СведенияОНазначении_ОКТМО",
        "Решение_СведенияОНазначении_ЛМСЗ",
        "Решение_СведенияОНазначении_КатегорияПолучателяЛокальная",
    }
)


def _convert_cell_value(col_name: str, raw_val: str) -> tuple[Any, str | None]:
    """Converts raw schema string value to native Excel type and display number_format."""
    if raw_val == "":
        return None, None

    if col_name in _DECIMAL_COLUMNS:
        try:
            return float(raw_val), "0.00"
        except ValueError:
            return raw_val, None

    if col_name in _INT_COLUMNS and raw_val.isdigit() and len(raw_val) <= 15:
        fmt = "0" * len(raw_val) if (raw_val.startswith("0") or len(raw_val) >= 10) else "0"
        return int(raw_val), fmt

    return raw_val, None


class EcpExcelWriter:
    """Writes GIS ECP compliant 107-column Excel packages."""

    def __init__(self, output_dir: Path) -> None:
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def write_package(self, package: EcpPackage) -> Path:
        """
        Writes an EcpPackage to a structured, formatted Excel (.xlsx) file.
        Returns the path of the created file.
        """
        filename = f"Пакет_Решений_{package.year_month}_{package.package_id}.xlsx"
        file_path = self.output_dir / filename

        wb = openpyxl.Workbook()
        ws = wb.active
        if ws is None:
            ws = wb.create_sheet("Пакет")
        else:
            ws.title = "Пакет"

        rows = build_package_rows(package)
        total_cols = len(ECP_COLUMNS)
        max_lengths = [len(col) for col in ECP_COLUMNS]

        # Styles
        header_font = Font(name="Segoe UI", size=10, bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
        header_align = Alignment(horizontal="center", vertical="center")

        base_font = Font(name="Segoe UI", size=10, bold=True, color="0F172A")
        base_fill = PatternFill(start_color="D9E8F5", end_color="D9E8F5", fill_type="solid")

        parent_font = Font(name="Segoe UI", size=10, bold=False, color="0F172A")
        parent_fill = PatternFill(start_color="EDF4FB", end_color="EDF4FB", fill_type="solid")

        child_font = Font(name="Segoe UI", size=10, bold=False, color="1E293B")
        child_fill = PatternFill(start_color="FFFFFF", end_color="FFFFFF", fill_type="solid")

        thin_side = Side(style="thin", color="CBD5E1")
        med_top_side = Side(style="medium", color="94A3B8")
        header_side = Side(style="thin", color="3B6998")

        header_border = Border(left=header_side, right=header_side, top=header_side, bottom=header_side)
        regular_border = Border(left=thin_side, right=thin_side, top=thin_side, bottom=thin_side)
        parent_border = Border(left=thin_side, right=thin_side, top=med_top_side, bottom=thin_side)
        data_align = Alignment(vertical="center")

        decision_id_col = COL_INDEX["Решение_ИДЗаписи"]

        for row_idx, raw_row in enumerate(rows, start=1):
            if row_idx == 1:
                ws.row_dimensions[row_idx].height = 28
                for col_idx, header_text in enumerate(raw_row, start=1):
                    cell = ws.cell(row=row_idx, column=col_idx, value=header_text)
                    cell.font = header_font
                    cell.fill = header_fill
                    cell.alignment = header_align
                    cell.border = header_border
                continue

            is_base_row = row_idx == 2
            is_parent_row = not is_base_row and raw_row[decision_id_col] != ""

            if is_base_row:
                ws.row_dimensions[row_idx].height = 22
                row_font, row_fill, row_border = base_font, base_fill, regular_border
            elif is_parent_row:
                ws.row_dimensions[row_idx].height = 20
                row_font, row_fill, row_border = parent_font, parent_fill, parent_border
            else:
                ws.row_dimensions[row_idx].height = 20
                row_font, row_fill, row_border = child_font, child_fill, regular_border

            for col_idx, raw_val in enumerate(raw_row, start=1):
                col_name = ECP_COLUMNS[col_idx - 1]
                typed_val, num_fmt = _convert_cell_value(col_name, raw_val)
                cell = ws.cell(row=row_idx, column=col_idx, value=typed_val)
                if num_fmt is not None:
                    cell.number_format = num_fmt
                cell.font = row_font
                cell.fill = row_fill
                cell.border = row_border
                cell.alignment = data_align

                if raw_val and len(raw_val) > max_lengths[col_idx - 1]:
                    max_lengths[col_idx - 1] = len(raw_val)

        # Auto-fit column widths across all 107 columns
        for col_idx in range(1, total_cols + 1):
            col_letter = get_column_letter(col_idx)
            ws.column_dimensions[col_letter].width = min(max(max_lengths[col_idx - 1] + 4, 14), 75)

        ws.freeze_panes = "A2"
        last_col_letter = get_column_letter(total_cols)
        ws.auto_filter.ref = f"A1:{last_col_letter}{len(rows)}"

        wb.save(file_path)
        wb.close()

        logger.info("Excel пакет успешно записан: %s (записей: %d)", file_path.name, package.total_records)
        return file_path
