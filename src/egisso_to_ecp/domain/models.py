"""Domain models for EGISSO to GIS ECP conversion."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator

from egisso_to_ecp.domain.normalizers import clean_cell_to_str


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
    rec_type: str | None = None
    fact_id: str | None = None
    assignment_fact_uuid: str | None = None
    lmsz_id: str = Field(default="", description="Код МСЗ (например, 0377)")
    category_id: str = Field(default="", description="ИД категории получателя")
    onmsz_code: str = Field(default="", description="Код ОНМСЗ")
    lmsz_provider_code: str | None = None
    provider_code: str | None = None
    snils_recip: str = Field(default="", description="СНИЛС получателя")
    family_name_recip: str = ""
    name_recip: str = ""
    patronymic_recip: str | None = None
    gender_recip: str = "М"
    birth_date_recip: date | datetime | str | int | float | None = None
    decision_date: date | datetime | str | int | float | None = None
    date_start: date | datetime | str | int | float | None = None
    date_finish: date | datetime | str | int | float | None = None
    using_sign: Any = None
    form_code: str | None = None
    amount: Decimal | float | str | None = None
    measury_code: str | None = None
    monetization: Any = None
    content: str | None = None
    comment: str | None = None
    equivalent_amount: Decimal | float | str | None = None
    reason_type: str | None = None
    reason_title: str | None = None
    reason_date: date | datetime | str | int | float | None = None
    reason_num: str | None = None
    suspension_date: date | datetime | str | int | float | None = None
    stop_reason_title: str | None = None
    payer_inn: str | None = None
    payer_kpp: str | None = None
    oktmo: str | None = None
    kbk: str | None = None
    snils_reason: str | None = None
    family_name_reason: str | None = None
    name_reason: str | None = None
    patronymic_reason: str | None = None
    gender_reason: str | None = None
    birth_date_reason: date | datetime | str | int | float | None = None
    kinship_type_code: str | None = None
    year_hint: int | None = None
    month_hint: int | None = None
    raw_extra: dict[str, Any] = Field(default_factory=dict)

    @field_validator(
        "lmsz_id",
        "category_id",
        "onmsz_code",
        "snils_recip",
        "family_name_recip",
        "name_recip",
        "gender_recip",
        mode="before",
    )
    @classmethod
    def _coerce_required_str(cls, v: Any) -> str:
        return clean_cell_to_str(v) or ""

    @field_validator(
        "rec_type",
        "fact_id",
        "assignment_fact_uuid",
        "lmsz_provider_code",
        "provider_code",
        "patronymic_recip",
        "form_code",
        "measury_code",
        "content",
        "comment",
        "reason_type",
        "reason_title",
        "reason_num",
        "stop_reason_title",
        "payer_inn",
        "payer_kpp",
        "oktmo",
        "kbk",
        "snils_reason",
        "family_name_reason",
        "name_reason",
        "patronymic_reason",
        "gender_reason",
        "kinship_type_code",
        mode="before",
    )
    @classmethod
    def _coerce_optional_str(cls, v: Any) -> str | None:
        return clean_cell_to_str(v)


class RelatedPerson(BaseModel):
    """Related person / basis person (СвязанноеЛицо child row in ECP package)."""
    snils: str
    family_name: str
    first_name: str
    patronymic: str | None = None
    birth_date: str = Field(..., description="ISO date YYYY-MM-DD")


class EcpPeriod(BaseModel):
    """Period of assignment (child row in ECP package)."""
    id_period: str
    date_start: str = Field(..., description="ISO date YYYY-MM-DD")
    date_finish: str | None = Field(None, description="ISO date YYYY-MM-DD")
    amount: str = Field(..., description="Сумма назначения (строка с десятичной точкой)")
    measury_code: str = Field(default="383", description="ОКЕИ (383 = рубль)")
    assignment_form: str = Field(default="1", description="Форма предоставления (1=денежная)")
    equivalent_amount: str | None = None
    monetization: bool | None = None
    comment: str | None = None
    content: str | None = None


class EcpDecision(BaseModel):
    """Single decision on measure assignment (parent row in ECP package)."""
    id_decision: str = Field(..., description="Уникальный идентификатор решения")
    id_statement: str | None = Field(None, description="ИД заявления (для исторических опционально)")
    id_onmsz: str
    inn: str | None = None
    kpp: str | None = None
    ogrn: str | None = None
    id_category: str
    snils_recipient: str
    family_name: str
    first_name: str
    patronymic: str | None = None
    birth_date: str = Field(..., description="ISO date YYYY-MM-DD")
    gender: str = Field(..., description="М или Ж")
    oktmo: str = Field(..., description="ОКТМО без разделителей")
    document_type: str = Field(default="3", description="3=Решение о назначении")
    action_type: str = Field(default="1", description="1=Назначение/Первичное")
    decision_basis: str = Field(default="1", description="Основание решения")
    decision_type: str = Field(default="01", description="Внутренний код типа решения")
    decision_date: str = Field(..., description="ISO date YYYY-MM-DD")
    date_start: str = Field(..., description="ISO date YYYY-MM-DD")
    date_finish: str | None = Field(None, description="ISO date YYYY-MM-DD")
    assignment_form: str = Field(default="3", description="3=Услуга/Стипендия или 1=Денежная")
    periodicity: str = Field(default="2", description="Периодичность предоставления")
    funding_source: str = Field(default="5", description="Источник финансирования (5=Бюджет субъекта РФ)")
    id_measure: str | None = None
    region_code: str = Field(default="62", description="Код субъекта РФ")
    code_msz: str | None = None
    code_lmsz: str | None = None
    lmsz_code_num: str | None = None
    category_code_num: str | None = None
    local_category_code: str | None = None
    reason_type: str | None = None
    reason_title: str | None = None
    reason_date: str | None = None
    reason_num: str | None = None
    is_historical: bool = True
    periods: list[EcpPeriod] = Field(default_factory=list)
    related_persons: list[RelatedPerson] = Field(default_factory=list)
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


class LmszMappingRule(BaseModel):
    """Mapping rule between source LMSZ/category and GIS ECP directory."""
    lmsz_uuid: str = Field(default="", description="UUID карточки ЛМСЗ (например: 88e2558c-...)")
    lmsz_code: str = Field(default="", description="Числовой код ЛМСЗ (например: 1 или 1.0)")
    lmsz_name: str = Field(default="", description="Наименование меры")
    category_uuid: str = Field(default="", description="UUID локальной категории")
    category_code: str = Field(default="", description="Числовой код локальной категории (например: 1 или 1.0)")
    category_name: str = Field(default="", description="Наименование категории")
    onmsz_code: str = Field(default="", description="Код ОНМСЗ (например: 6220000001)")


class ConversionConfig(BaseModel):
    """Runtime configuration for data conversion."""
    input_path: Path
    output_dir: Path
    recursive_search: bool = True
    split_by_months: bool = True
    export_csv: bool = True
    export_xlsx: bool = False
    export_xml: bool = False
    provider_code: str = "1788"
    onmsz_id: str = ""
    onmsz_inn: str = ""
    onmsz_kpp: str = ""
    onmsz_ogrn: str = ""
    code_tmsz: str = "220119"
    code_lmsz_num: str = ""
    code_category_num: str = ""
    mapping_rules: list[LmszMappingRule] = Field(default_factory=list)
    mapping_file: Path | None = None
    funding_source: str = "5"
    assignment_form: str = "3"
    periodicity: str = "2"
    decision_basis: str = "1"
    package_size_limit_mb: float = 18.5
    default_oktmo: str = "62701000001"
    default_region_code: str = "62"
    default_measury_code: str = "383"


class ConversionSummary(BaseModel):
    """Summary statistics for conversion execution."""
    scanned_files_count: int = 0
    parsed_records_count: int = 0
    valid_decisions_count: int = 0
    packages_generated_count: int = 0
    csv_files_written: list[Path] = Field(default_factory=list)
    xlsx_files_written: list[Path] = Field(default_factory=list)
    xml_files_written: list[Path] = Field(default_factory=list)
    error_report_path: Path | None = None
    issues: list[ValidationIssue] = Field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        return any(i.severity == ValidationSeverity.ERROR for i in self.issues)
