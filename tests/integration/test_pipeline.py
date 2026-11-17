"""End-to-end integration test for ConversionPipeline."""

import csv
from pathlib import Path

import openpyxl
import pytest

from egisso_to_ecp.application.pipeline import ConversionPipeline
from egisso_to_ecp.domain.models import ConversionConfig
from egisso_to_ecp.domain.normalizers import is_uuid_str
from egisso_to_ecp.infrastructure.writers.ecp_schema import COL_INDEX, ECP_COLUMNS


def create_test_registry(file_path: Path) -> None:
    """Creates a sample EGISSO registry with realistic numeric and string test records."""
    wb = openpyxl.Workbook()
    ws = wb.active
    assert ws is not None
    ws.title = "Sheet1"

    headers = [
        "RecType",
        "assignmentFactUuid",
        "LMSZID",
        "categoryID",
        "ONMSZCode",
        "SNILS_recip",
        "FamilyName_recip",
        "Name_recip",
        "Patronymic_recip",
        "Gender_recip",
        "BirthDate_recip",
        "decision_date",
        "dateStart",
        "dateFinish",
        "FormCode",
        "amount",
        "measuryCode",
        "monetization",
        "comment",
        "reasonType",
        "reasonTitle",
        "reasonDate",
        "reasonNum",
        "OKTMO",
        "SNILS_reason",
        "FamilyName_reason",
        "Name_reason",
        "BirthDate_reason",
    ]
    ws.append(headers)

    # Row 1: Valid record (May 2024) with numeric SNILS & OKTMO and a related person
    ws.append([
        "Fact",
        "FACT-001",
        "0377",
        "101",
        "0377",
        11223344595,
        "Иванов",
        "Иван",
        "Иванович",
        "Мужской",
        "2002-04-12",
        "2024-05-15",
        "2024-05-01",
        "2024-05-31",
        "01",
        "3500.00",
        "01",
        "Нет",
        "Выплата за май",
        "Приказ",
        "О назначении стипендии",
        "2024-05-10",
        "123-ОД",
        62701000001,
        "112-233-445 95",
        "Иванова",
        "Мария",
        "1978-02-01",
    ])

    # Row 2: Valid record (June 2024)
    ws.append([
        "Fact",
        "FACT-002",
        "0377",
        "101",
        "0377",
        "112-233-445 95",
        "Петров",
        "Петр",
        "Сергеевич",
        "1",
        "2001-08-20",
        "2024-06-10",
        "2024-06-01",
        "2024-06-30",
        "01",
        "4200.50",
        "руб.",
        False,
        None,
        "Приказ",
        "О назначении стипендии",
        "2024-06-05",
        "145-ОД",
        "62701000001",
        None,
        None,
        None,
        None,
    ])

    # Row 3: Invalid record (Invalid SNILS checksum)
    ws.append([
        "Fact",
        "FACT-003",
        "0377",
        "101",
        "0377",
        "000-000-000 00",
        "Сидоров",
        "Сидор",
        "Сидорович",
        "Мужской",
        "2003-01-01",
        "2024-06-15",
        "2024-06-01",
        "2024-06-30",
        "01",
        "3000.00",
        "01",
        None,
        None,
        "Приказ",
        "О назначении",
        "2024-06-10",
        "150-ОД",
        "62701000001",
        None,
        None,
        None,
        None,
    ])

    wb.save(file_path)
    wb.close()


def test_end_to_end_conversion(tmp_path: Path) -> None:
    in_dir = tmp_path / "input"
    in_dir.mkdir()
    sample_file = in_dir / "social_stipends_2024.xlsx"
    create_test_registry(sample_file)

    out_dir = tmp_path / "output"

    config = ConversionConfig(
        input_path=in_dir,
        output_dir=out_dir,
        recursive_search=True,
        split_by_months=True,
        export_csv=True,
        export_xlsx=True,
        export_xml=True,
        provider_code="TEST_PROVIDER_99",
    )

    pipeline = ConversionPipeline(config=config)
    summary = pipeline.run()

    # 1. Assert summary statistics
    assert summary.scanned_files_count == 1
    assert summary.parsed_records_count == 3
    assert summary.valid_decisions_count == 2
    assert summary.packages_generated_count == 2  # One for May 2024, one for June 2024

    # 2. Check output directories and files
    csv_dir = out_dir / "csv"
    xlsx_dir = out_dir / "xlsx"
    xml_dir = out_dir / "xml"
    assert csv_dir.exists()
    assert xlsx_dir.exists()
    assert xml_dir.exists()

    csv_files = list(csv_dir.glob("*.csv"))
    xlsx_files = list(xlsx_dir.glob("*.xlsx"))
    xml_files = list(xml_dir.glob("*.xml"))
    assert len(csv_files) == 2
    assert len(xlsx_files) == 2
    assert len(xml_files) == 2

    # 3. Check error report
    err_report = out_dir / "errors_report.xlsx"
    assert err_report.exists()
    assert summary.error_report_path == err_report

    # 4. Validate CSV structure & RFC 4180 / UTF-8-BOM compliance
    may_csv = [f for f in csv_files if "2024-05" in f.name][0]
    with open(may_csv, encoding="utf-8-sig") as f:
        reader = list(csv.reader(f))

        # Row 1: Headers (107 columns)
        assert len(reader[0]) == len(ECP_COLUMNS)
        assert reader[0][0] == "ПоставщикИнформации"
        assert reader[0][1] == "ИДПакета"
        assert reader[0][-1] == "КоличествоЗаписей"

        # Row 2: Document base row
        assert reader[1][COL_INDEX["ПоставщикИнформации"]] == "TEST_PROVIDER_99"
        assert reader[1][COL_INDEX["ИДПакета"]] != ""
        assert reader[1][COL_INDEX["КоличествоЗаписей"]] == "1"

        # Row 3: Parent decision row (nested repeating blocks must remain empty)
        # Non-GUID source ID "FACT-001" must not leak into Решение_ИДЗаписи (GUID pattern).
        assert is_uuid_str(reader[2][COL_INDEX["Решение_ИДЗаписи"]])
        assert reader[2][COL_INDEX["Решение_ТипДокумента"]] == "3"
        assert reader[2][COL_INDEX["Решение_ТипДействия"]] == "1"
        assert reader[2][COL_INDEX["Решение_Получатель_СНИЛС"]] == "112-233-445 95"
        assert reader[2][COL_INDEX["Решение_Получатель_ФИО_Фамилия"]] == "Иванов"
        assert reader[2][COL_INDEX["Решение_Получатель_ФИО_Имя"]] == "Иван"
        assert reader[2][COL_INDEX["Решение_Получатель_ДатаРождения"]] == "2002-04-12"
        assert reader[2][COL_INDEX["Решение_СведенияОНазначении_ОКТМО"]] == "62701000001"
        assert reader[2][COL_INDEX["Решение_СведенияОНазначении_ПризнакИсторическихДанных"]] == "true"
        assert reader[2][COL_INDEX["Решение_СведенияОНазначении_ПериодыНазначения_СуммаКоличество"]] == ""
        assert reader[2][COL_INDEX["Решение_СведенияОНазначении_СвязанноеЛицо_СНИЛС"]] == ""

        # Row 4: Child ПериодыНазначения row
        assert reader[3][COL_INDEX["Решение_ИДЗаписи"]] == ""
        assert reader[3][COL_INDEX["Решение_СведенияОНазначении_ПериодыНазначения_СуммаКоличество"]] == "3500.00"
        assert reader[3][COL_INDEX["Решение_СведенияОНазначении_ПериодыНазначения_ЕдИзмерения"]] == "383"
        assert reader[3][COL_INDEX["Решение_СведенияОНазначении_ПериодыНазначения_ДатаС"]] == "2024-05-01"
        assert reader[3][COL_INDEX["Решение_СведенияОНазначении_ПериодыНазначения_ДатаПо"]] == "2024-05-31"
        assert reader[3][COL_INDEX["Решение_СведенияОНазначении_ПериодыНазначения_ПризнакМонетизации"]] == "false"
        assert reader[3][COL_INDEX["Решение_СведенияОНазначении_ПериодыНазначения_Комментарий"]] == "Выплата за май"

        # Row 5: Child СвязанноеЛицо row
        assert reader[4][COL_INDEX["Решение_ИДЗаписи"]] == ""
        assert reader[4][COL_INDEX["Решение_СведенияОНазначении_СвязанноеЛицо_СНИЛС"]] == "112-233-445 95"
        assert reader[4][COL_INDEX["Решение_СведенияОНазначении_СвязанноеЛицо_ФИО_Фамилия"]] == "Иванова"
        assert reader[4][COL_INDEX["Решение_СведенияОНазначении_СвязанноеЛицо_ДатаРождения"]] == "1978-02-01"

    # 5. Validate XLSX structure, native types, and column widths
    may_xlsx = [f for f in xlsx_files if "2024-05" in f.name][0]
    wb_xlsx = openpyxl.load_workbook(may_xlsx)
    ws_xlsx = wb_xlsx.active
    assert ws_xlsx is not None
    assert ws_xlsx.freeze_panes == "A2"
    assert ws_xlsx.auto_filter.ref is not None

    # Check column widths for all 107 columns
    for col_idx in range(1, len(ECP_COLUMNS) + 1):
        col_letter = openpyxl.utils.get_column_letter(col_idx)
        col_width = ws_xlsx.column_dimensions[col_letter].width
        assert col_width is not None and col_width >= 14

    # Check native int/float cell types in XLSX
    assert ws_xlsx.cell(row=2, column=COL_INDEX["КоличествоЗаписей"] + 1).value == 1
    assert isinstance(ws_xlsx.cell(row=2, column=COL_INDEX["КоличествоЗаписей"] + 1).value, int)
    assert ws_xlsx.cell(row=3, column=COL_INDEX["Решение_Получатель_СНИЛС"] + 1).value == "112-233-445 95"
    assert ws_xlsx.cell(row=3, column=COL_INDEX["Решение_ОНМСЗ_ИдентификаторОНМСЗ"] + 1).value == 377
    amt_cell = ws_xlsx.cell(row=4, column=COL_INDEX["Решение_СведенияОНазначении_ПериодыНазначения_СуммаКоличество"] + 1)
    assert amt_cell.value == 3500.0
    assert isinstance(amt_cell.value, (int, float))
    assert amt_cell.number_format == "0.00"
    wb_xlsx.close()


def test_recursive_folder_date_hint_fallback(tmp_path: Path) -> None:
    nested = tmp_path / "input" / "2024" / "08"
    nested.mkdir(parents=True)
    sample_file = nested / "registry.xlsx"

    wb = openpyxl.Workbook()
    ws = wb.active
    assert ws is not None
    ws.append(["LMSZID", "categoryID", "SNILS_recip", "FamilyName_recip", "Name_recip", "BirthDate_recip", "amount"])
    ws.append(["0377", "101", 11223344595, "Смирнова", "Ольга", "1995-03-20", 1500])
    wb.save(sample_file)
    wb.close()

    out_dir = tmp_path / "output"
    config = ConversionConfig(input_path=tmp_path / "input", output_dir=out_dir)
    summary = ConversionPipeline(config).run()

    assert summary.valid_decisions_count == 1
    assert len(summary.csv_files_written) == 1
    assert "2024-08" in summary.csv_files_written[0].name


_DOCS_SAMPLES = Path(__file__).resolve().parents[2] / "docs_and_samples"
_REAL_SAMPLE = _DOCS_SAMPLES / "ЕГИССО соц. стипен_ИСГД..xlsx"


@pytest.mark.skipif(not _REAL_SAMPLE.exists(), reason="Real sample file not present")
def test_real_sample_file_smoke(tmp_path: Path) -> None:
    out_dir = tmp_path / "output"
    config = ConversionConfig(
        input_path=_DOCS_SAMPLES,
        output_dir=out_dir,
        export_csv=True,
        export_xlsx=True,
    )
    summary = ConversionPipeline(config).run()

    # Template Primerzapolneniya... must be skipped without generating false errors
    assert all("Primerzapolneniya" not in issue.file_source for issue in summary.issues)
    assert summary.parsed_records_count == 4
    assert summary.valid_decisions_count == 2
    assert len(summary.csv_files_written) == 1
    assert len(summary.xlsx_files_written) == 1

    # Verify structured XLSX contents and types
    wb = openpyxl.load_workbook(summary.xlsx_files_written[0])
    ws = wb.active
    assert ws is not None
    assert ws.freeze_panes == "A2"

    for col_idx in range(1, len(ECP_COLUMNS) + 1):
        col_letter = openpyxl.utils.get_column_letter(col_idx)
        assert ws.column_dimensions[col_letter].width >= 14

    # Row 2: Base row
    assert ws.cell(row=2, column=COL_INDEX["ПоставщикИнформации"] + 1).value == 1788
    assert ws.cell(row=2, column=COL_INDEX["КоличествоЗаписей"] + 1).value == 2

    # Rows 3 & 5: Valid decisions (Губалев, Глызарев)
    assert ws.cell(row=3, column=COL_INDEX["Решение_Получатель_ФИО_Фамилия"] + 1).value == "Губалев"
    assert ws.cell(row=3, column=COL_INDEX["Решение_РеквизитыРешения_НомерРешения"] + 1).value == "РЕШ-20261111-0004"
    assert ws.cell(row=3, column=COL_INDEX["Решение_ОНМСЗ_ИдентификаторОНМСЗ"] + 1).value == 6220000001
    assert ws.cell(row=3, column=COL_INDEX["Решение_КодМСЗ"] + 1).value == 220119
    assert ws.cell(row=3, column=COL_INDEX["Решение_КодЛМСЗ"] + 1).value == "88e2558c-7d6a-42e5-94c8-af9e8444d6c1"
    id_measure_1 = ws.cell(row=3, column=COL_INDEX["Решение_СведенияОНазначении_ИДМеры"] + 1).value

    assert ws.cell(row=5, column=COL_INDEX["Решение_Получатель_ФИО_Фамилия"] + 1).value == "Глызарев"
    assert ws.cell(row=5, column=COL_INDEX["Решение_РеквизитыРешения_НомерРешения"] + 1).value == "РЕШ-20261111-0005"
    assert ws.cell(row=5, column=COL_INDEX["Решение_ОНМСЗ_ИдентификаторОНМСЗ"] + 1).value == 6220000001
    assert ws.cell(row=5, column=COL_INDEX["Решение_КодМСЗ"] + 1).value == 220119
    id_measure_2 = ws.cell(row=5, column=COL_INDEX["Решение_СведенияОНазначении_ИДМеры"] + 1).value

    assert id_measure_1 != id_measure_2
    assert id_measure_1 == ws.cell(row=3, column=COL_INDEX["Решение_ИДЗаписи"] + 1).value

    # Rows 4 & 6: Period rows with native numeric types
    amt_cell = ws.cell(row=4, column=COL_INDEX["Решение_СведенияОНазначении_ПериодыНазначения_СуммаКоличество"] + 1)
    assert isinstance(amt_cell.value, float)
    assert amt_cell.value == 940.13
    unit_cell = ws.cell(row=4, column=COL_INDEX["Решение_СведенияОНазначении_ПериодыНазначения_ЕдИзмерения"] + 1)
    assert isinstance(unit_cell.value, int)
    assert unit_cell.value == 383
    wb.close()
