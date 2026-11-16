"""Domain models for EGISSO to GIS ECP conversion."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class ValidationSeverity(str, Enum):
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"


class ValidationIssue(BaseModel):
    """Represents a data validation or FLK rule violation."""
    file_source: str
    row_index: int
    field_name: str
    value: str | None = None
    message: str
    severity: ValidationSeverity = ValidationSeverity.ERROR


class OldEgissoRecord(BaseModel):
    """Raw record extracted from old EGISSO registers/spreadsheets."""
    file_source: str
    row_index: int
    fact_id: str | None = None
    lmsz_id: str = Field(..., description="Код МСЗ (например, 0377)")
    category_id: str = Field(..., description="ИД категории получателя")
    onmsz_code: str = Field(..., description="Код ОНМСЗ")
    snils_recip: str = Field(..., description="СНИЛС получателя")
    family_name_recip: str
    name_recip: str
    patronymic_recip: str | None = None
    gender_recip: str
    birth_date_recip: date | str
    decision_date: date | str
    date_start: date | str
    date_finish: date | str | None = None
    amount: Decimal | float | None = None
    measury_code: str | None = None
    reason_type: str | None = None
    reason_title: str | None = None
    reason_date: date | str | None = None
    reason_num: str | None = None
    suspension_date: date | str | None = None
    stop_reason_title: str | None = None
    payer_inn: str | None = None
    payer_kpp: str | None = None
    oktmo: str | None = None
    kbk: str | None = None
    raw_extra: dict[str, Any] = Field(default_factory=dict)


class EcpPeriod(BaseModel):
    """Period of assignment (child row in ECP package)."""
    id_period: str
    date_start: str = Field(..., description="ISO date YYYY-MM-DD")
    date_finish: str | None = Field(None, description="ISO date YYYY-MM-DD")
    amount: str = Field(..., description="Сумма назначения (строка с десятичной точкой)")
    measury_code: str = Field(default="383", description="ОКЕИ (383 = рубль)")
    assignment_form: str = Field(default="01", description="Форма предоставления (01=денежная)")


class EcpDecision(BaseModel):
    """Single decision on measure assignment (parent row in ECP package)."""
    id_decision: str = Field(..., description="Уникальный идентификатор решения")
    id_statement: str | None = Field(None, description="ИД заявления (для исторических опционально)")
    id_onmsz: str
    id_category: str
    snils_recipient: str
    family_name: str
    first_name: str
    patronymic: str | None = None
    birth_date: str = Field(..., description="ISO date YYYY-MM-DD")
    gender: str = Field(..., description="М или Ж")
    oktmo: str = Field(..., description="ОКТМО без разделителей")
    decision_type: str = Field(default="01", description="01=Решение о назначении")
    decision_date: str = Field(..., description="ISO date YYYY-MM-DD")
    date_start: str = Field(..., description="ISO date YYYY-MM-DD")
    date_finish: str | None = Field(None, description="ISO date YYYY-MM-DD")
    reason_type: str | None = None
    reason_title: str | None = None
    reason_date: str | None = None
    reason_num: str | None = None
    is_historical: bool = True
    periods: list[EcpPeriod] = Field(default_factory=list)
    source_file: str = ""
    source_row: int = 0


class EcpPackage(BaseModel):
    """Complete package of decisions ready for export to CSV/XLSX."""
    package_id: str
    provider_code: str
    creation_date: str = Field(..., description="ISO date YYYY-MM-DD")
    year_month: str = Field(..., description="YYYY-MM (метка периода)")
    measure_code: str = Field(default="", description="Код МСЗ/ОНМСЗ")
    decisions: list[EcpDecision] = Field(default_factory=list)

    @property
    def total_records(self) -> int:
        """Total number of decision rows."""
        return len(self.decisions)


class ConversionConfig(BaseModel):
    """Runtime configuration for data conversion."""
    input_path: Path
    output_dir: Path
    recursive_search: bool = True
    split_by_months: bool = True
    export_csv: bool = True
    export_xlsx: bool = False
    provider_code: str = "PFR001"
    package_size_limit_mb: float = 18.5
    default_oktmo: str = "62701000001"
    default_measury_code: str = "383"


class ConversionSummary(BaseModel):
    """Summary statistics for conversion execution."""
    scanned_files_count: int = 0
    parsed_records_count: int = 0
    valid_decisions_count: int = 0
    packages_generated_count: int = 0
    csv_files_written: list[Path] = Field(default_factory=list)
    xlsx_files_written: list[Path] = Field(default_factory=list)
    error_report_path: Path | None = None
    issues: list[ValidationIssue] = Field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        return any(i.severity == ValidationSeverity.ERROR for i in self.issues)
