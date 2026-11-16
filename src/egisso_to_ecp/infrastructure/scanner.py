"""Directory and file scanning utilities."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from egisso_to_ecp.domain.normalizers import extract_year_month_from_path

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".xlsx", ".xls"}


@dataclass(frozen=True)
class ScannedFileInfo:
    path: Path
    year_hint: int | None
    month_hint: int | None


class DirectoryScanner:
    """Scans directories for input Excel registry files."""

    def __init__(self, recursive: bool = True) -> None:
        self.recursive = recursive

    def scan(self, root_path: Path) -> list[ScannedFileInfo]:
        """
        Scans root_path for supported Excel files.
        Ignores temporary Excel files (starting with ~$ and dot-files).
        """
        if not root_path.exists():
            raise FileNotFoundError(f"Каталог не найден: {root_path}")

        results: list[ScannedFileInfo] = []

        if root_path.is_file():
            if root_path.suffix.lower() in SUPPORTED_EXTENSIONS and not root_path.name.startswith("~"):
                hint = extract_year_month_from_path(str(root_path))
                y_hint, m_hint = hint if hint else (None, None)
                results.append(ScannedFileInfo(path=root_path, year_hint=y_hint, month_hint=m_hint))
            return results

        pattern_generator = (
            root_path.rglob("*") if self.recursive else root_path.glob("*")
        )

        for p in pattern_generator:
            if not p.is_file():
                continue
            # Ignore Excel temporary lock files or hidden files
            if p.name.startswith("~$") or p.name.startswith("."):
                continue

            if p.suffix.lower() in SUPPORTED_EXTENSIONS:
                hint = extract_year_month_from_path(str(p))
                y_hint, m_hint = hint if hint else (None, None)
                results.append(
                    ScannedFileInfo(
                        path=p,
                        year_hint=y_hint,
                        month_hint=m_hint,
                    )
                )

        # Sort for deterministic processing
        results.sort(key=lambda x: str(x.path))
        logger.info("Найдено файлов для обработки: %d (рекурсивно=%s)", len(results), self.recursive)
        return results
