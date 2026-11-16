"""Error and validation issues report generator."""

from __future__ import annotations

import logging
from pathlib import Path

import openpyxl
from openpyxl.styles import Font, PatternFill

from egisso_to_ecp.domain.models import ValidationIssue, ValidationSeverity

logger = logging.getLogger(__name__)


class ErrorReportWriter:
    """Generates user-friendly Excel error report."""

    def __init__(self, output_dir: Path) -> None:
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def write_report(self, issues: list[ValidationIssue]) -> Path:
        """Writes all collected validation issues to errors_report.xlsx."""
        file_path = self.output_dir / "errors_report.xlsx"

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Ошибки и предупреждения ФЛК"

        headers = [
            "Файл-источник",
            "Номер строки",
            "Поле",
            "Значение в источнике",
            "Тип замечания",
            "Описание ошибки / правила ФЛК",
        ]
        ws.append(headers)

        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
        error_fill = PatternFill(start_color="FFD9D9", end_color="FFD9D9", fill_type="solid")
        warning_fill = PatternFill(start_color="FFF2CC", end_color="FFF2CC", fill_type="solid")

        for col_idx in range(1, len(headers) + 1):
            cell = ws.cell(row=1, column=col_idx)
            cell.font = header_font
            cell.fill = header_fill

        for issue in issues:
            ws.append([
                issue.file_source,
                issue.row_index,
                issue.field_name,
                issue.value or "",
                issue.severity.value,
                issue.message,
            ])
            row_idx = ws.max_row
            fill = error_fill if issue.severity == ValidationSeverity.ERROR else warning_fill
            ws.cell(row=row_idx, column=5).fill = fill

        # Auto-adjust column widths
        for col in ws.columns:
            max_len = max(len(str(cell.value or "")) for cell in col)
            col_letter = openpyxl.utils.get_column_letter(col[0].column)
            ws.column_dimensions[col_letter].width = min(max(max_len + 3, 12), 60)

        wb.save(file_path)
        wb.close()
        logger.info("Отчёт об ошибках записан: %s (записей: %d)", file_path.name, len(issues))
        return file_path
