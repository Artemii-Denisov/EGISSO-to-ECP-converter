"""Core conversion orchestrator and processing pipeline."""

from __future__ import annotations

import logging
from collections.abc import Callable

from egisso_to_ecp.application.splitter import PackageSplitter
from egisso_to_ecp.domain.flk_rules import validate_and_convert_record
from egisso_to_ecp.domain.models import (
    ConversionConfig,
    ConversionSummary,
    EcpDecision,
    ValidationIssue,
)
from egisso_to_ecp.infrastructure.readers.excel_reader import ExcelRegistryReader
from egisso_to_ecp.infrastructure.scanner import DirectoryScanner
from egisso_to_ecp.infrastructure.writers.ecp_csv_writer import EcpCsvWriter
from egisso_to_ecp.infrastructure.writers.ecp_excel_writer import EcpExcelWriter
from egisso_to_ecp.infrastructure.writers.error_report_writer import ErrorReportWriter

logger = logging.getLogger(__name__)

ProgressCallback = Callable[[int, int, str], None]
LogCallback = Callable[[str], None]


class ConversionPipeline:
    """End-to-end data processing pipeline."""

    def __init__(
        self,
        config: ConversionConfig,
        progress_callback: ProgressCallback | None = None,
        log_callback: LogCallback | None = None,
    ) -> None:
        self.config = config
        self.progress_callback = progress_callback
        self.log_callback = log_callback

    def _log(self, message: str) -> None:
        logger.info(message)
        if self.log_callback:
            self.log_callback(message)

    def _report_progress(self, current: int, total: int, status: str) -> None:
        if self.progress_callback:
            self.progress_callback(current, total, status)

    def run(self) -> ConversionSummary:
        """Executes full pipeline: scan -> read -> validate -> group -> write."""
        summary = ConversionSummary()
        self.config.output_dir.mkdir(parents=True, exist_ok=True)

        # 1. Scanning
        self._log(f"Начало сканирования каталога: {self.config.input_path}")
        scanner = DirectoryScanner(recursive=self.config.recursive_search)
        scanned_files = scanner.scan(self.config.input_path)
        summary.scanned_files_count = len(scanned_files)

        if not scanned_files:
            self._log("В указанном каталоге не найдены файлы для обработки (.xlsx, .xls)")
            return summary

        self._log(f"Найдено файлов для обработки: {len(scanned_files)}")

        # 2. Reading and Validating
        all_decisions: list[EcpDecision] = []
        all_issues: list[ValidationIssue] = []
        total_records = 0

        for f_idx, s_file in enumerate(scanned_files, start=1):
            status_msg = f"Обработка файла {f_idx}/{len(scanned_files)}: {s_file.path.name}"
            self._report_progress(f_idx, len(scanned_files), status_msg)
            self._log(status_msg)

            reader = ExcelRegistryReader(
                s_file.path,
                year_hint=s_file.year_hint,
                month_hint=s_file.month_hint,
            )
            try:
                for record in reader.read_records():
                    total_records += 1
                    decision, issues = validate_and_convert_record(record, self.config)
                    if issues:
                        all_issues.extend(issues)
                    if decision:
                        all_decisions.append(decision)
            except Exception as e:
                self._log(f"Ошибка при чтении файла {s_file.path.name}: {e}")

        summary.parsed_records_count = total_records
        summary.valid_decisions_count = len(all_decisions)
        summary.issues = all_issues

        self._log(
            f"Чтение завершено. Прочитано строк: {total_records}, валидных решений: {len(all_decisions)}, замечаний ФЛК: {len(all_issues)}"
        )

        if not all_decisions:
            self._log("Нет валидных записей для формирования пакетов.")
            if all_issues:
                err_writer = ErrorReportWriter(self.config.output_dir)
                summary.error_report_path = err_writer.write_report(all_issues)
            return summary

        # 3. Grouping and Splitting
        self._log("Формирование пакетов решений...")
        splitter = PackageSplitter(
            provider_code=self.config.provider_code,
            split_by_months=self.config.split_by_months,
            max_size_mb=self.config.package_size_limit_mb,
        )
        packages = splitter.split_into_packages(all_decisions)
        summary.packages_generated_count = len(packages)
        self._log(f"Сформировано пакетов: {len(packages)}")

        # 4. Writing Output Formats
        if self.config.export_csv:
            csv_dir = self.config.output_dir / "csv"
            csv_writer = EcpCsvWriter(csv_dir)
            for pkg in packages:
                written_csv = csv_writer.write_package(pkg)
                summary.csv_files_written.append(written_csv)

        if self.config.export_xlsx:
            xlsx_dir = self.config.output_dir / "xlsx"
            xlsx_writer = EcpExcelWriter(xlsx_dir)
            for pkg in packages:
                written_xlsx = xlsx_writer.write_package(pkg)
                summary.xlsx_files_written.append(written_xlsx)

        # 5. Writing Error Report
        if all_issues:
            err_writer = ErrorReportWriter(self.config.output_dir)
            summary.error_report_path = err_writer.write_report(all_issues)
            self._log(f"Сформирован отчёт об ошибках ФЛК: {summary.error_report_path.name}")

        self._report_progress(len(scanned_files), len(scanned_files), "Обработка успешно завершена!")
        self._log("Конвертация успешно завершена!")
        return summary
