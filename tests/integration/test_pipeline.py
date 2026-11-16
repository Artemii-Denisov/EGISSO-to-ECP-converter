"""End-to-end integration test for ConversionPipeline."""

import csv
from pathlib import Path

import openpyxl

from egisso_to_ecp.application.pipeline import ConversionPipeline
from egisso_to_ecp.domain.models import ConversionConfig
from egisso_to_ecp.infrastructure.writers.ecp_schema import COL_INDEX, ECP_COLUMNS


def create_test_registry(file_path: Path) -> None:
    """Creates a sample EGISSO registry with realistic test records."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Sheet1"

    headers = [
        "Fact",
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
        "amount",
        "measuryCode",
        "reasonType",
        "reasonTitle",
        "reasonDate",
        "reasonNum",
        "OKTMO",
    ]
    ws.append(headers)

    # Row 1: Valid record (May 2024)
    ws.append([
        "FACT-001",
        "0377",
        "101",
        "0377",
        "112-233-445 95",
        "Иванов",
        "Иван",
        "Иванович",
        "Мужской",
        "2002-04-12",
        "2024-05-15",
        "2024-05-01",
        "2024-05-31",
        "3500.00",
        "01",
        "Приказ",
        "О назначении стипендии",
        "2024-05-10",
        "123-ОД",
        "62701000001",
    ])

    # Row 2: Valid record (June 2024)
    ws.append([
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
        "4200.50",
        "руб.",
        "Приказ",
        "О назначении стипендии",
        "2024-06-05",
        "145-ОД",
        "62701000001",
    ])

    # Row 3: Invalid record (Invalid SNILS checksum)
    ws.append([
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
        "3000.00",
        "01",
        "Приказ",
        "О назначении",
        "2024-06-10",
        "150-ОД",
        "62701000001",
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
    assert csv_dir.exists()
    assert xlsx_dir.exists()

    csv_files = list(csv_dir.glob("*.csv"))
    xlsx_files = list(xlsx_dir.glob("*.xlsx"))
    assert len(csv_files) == 2
    assert len(xlsx_files) == 2

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

        # Row 3: Decision row
        assert reader[2][COL_INDEX["Решение_ИДЗаписи"]] == "FACT-001"
        assert reader[2][COL_INDEX["Решение_Получатель_СНИЛС"]] == "11223344595"
        assert reader[2][COL_INDEX["Решение_Получатель_ФИО_Фамилия"]] == "Иванов"
        assert reader[2][COL_INDEX["Решение_Получатель_ФИО_Имя"]] == "Иван"
        assert reader[2][COL_INDEX["Решение_Получатель_ДатаРождения"]] == "2002-04-12"
        assert reader[2][COL_INDEX["Решение_СведенияОНазначении_ОКТМО"]] == "62701000001"
        assert reader[2][COL_INDEX["Решение_СведенияОНазначении_ПризнакИсторическихДанных"]] == "true"
        assert reader[2][COL_INDEX["Решение_СведенияОНазначении_ПериодыНазначения_СуммаКоличество"]] == "3500.00"
        assert reader[2][COL_INDEX["Решение_СведенияОНазначении_ПериодыНазначения_ЕдИзмерения"]] == "383"
        assert reader[2][COL_INDEX["Решение_СведенияОНазначении_ПериодыНазначения_ДатаС"]] == "2024-05-01"
        assert reader[2][COL_INDEX["Решение_СведенияОНазначении_ПериодыНазначения_ДатаПо"]] == "2024-05-31"
