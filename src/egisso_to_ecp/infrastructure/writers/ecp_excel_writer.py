"""GIS ECP Excel (.xlsx) writer."""

from __future__ import annotations

import logging
from pathlib import Path

import openpyxl

from egisso_to_ecp.domain.models import EcpPackage
from egisso_to_ecp.infrastructure.writers.ecp_schema import build_package_rows

logger = logging.getLogger(__name__)


class EcpExcelWriter:
    """Writes GIS ECP compliant 107-column Excel packages."""

    def __init__(self, output_dir: Path) -> None:
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def write_package(self, package: EcpPackage) -> Path:
        """
        Writes an EcpPackage to an Excel (.xlsx) file.
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

        for row in build_package_rows(package):
            ws.append(row)

        wb.save(file_path)
        wb.close()

        logger.info("Excel пакет успешно записан: %s (записей: %d)", file_path.name, package.total_records)
        return file_path
