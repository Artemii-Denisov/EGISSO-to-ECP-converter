"""Hierarchical GIS ECP CSV writer with UTF-8-BOM and RFC 4180 compliance."""

from __future__ import annotations

import csv
import logging
from pathlib import Path

from egisso_to_ecp.domain.models import EcpPackage
from egisso_to_ecp.infrastructure.writers.ecp_schema import build_package_rows

logger = logging.getLogger(__name__)


class EcpCsvWriter:
    """Writes GIS ECP compliant 107-column CSV packages."""

    def __init__(self, output_dir: Path) -> None:
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def write_package(self, package: EcpPackage) -> Path:
        """
        Writes an EcpPackage to a CSV file.
        Returns the path of the created file.
        """
        filename = f"Пакет_Решений_{package.year_month}_{package.package_id}.csv"
        file_path = self.output_dir / filename

        rows = build_package_rows(package)
        with open(file_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f, delimiter=",", quoting=csv.QUOTE_MINIMAL)
            writer.writerows(rows)

        logger.info("CSV пакет успешно записан: %s (записей: %d)", file_path.name, package.total_records)
        return file_path
