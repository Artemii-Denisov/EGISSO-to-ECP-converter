"""Unit tests for FLK business validation rules."""

from pathlib import Path

from egisso_to_ecp.domain.flk_rules import validate_and_convert_record
from egisso_to_ecp.domain.models import ConversionConfig, OldEgissoRecord, ValidationSeverity


def make_valid_record() -> OldEgissoRecord:
    return OldEgissoRecord(
        file_source="test.xlsx",
        row_index=2,
        fact_id="FACT-001",
        lmsz_id="0377",
        category_id="101",
        onmsz_code="0377",
        snils_recip="112-233-445 95",
        family_name_recip="Иванов",
        name_recip="Иван",
        patronymic_recip="Иванович",
        gender_recip="1",
        birth_date_recip="2000-01-15",
        decision_date="2024-05-01",
        date_start="2024-05-01",
        date_finish="2024-05-31",
        amount=5000.0,
        measury_code="01",
        oktmo="62701000001",
    )


class TestFlkRules:
    def test_valid_record_conversion(self) -> None:
        cfg = ConversionConfig(input_path=Path("."), output_dir=Path("."))
        rec = make_valid_record()
        decision, issues = validate_and_convert_record(rec, cfg)

        assert decision is not None
        assert decision.snils_recipient == "11223344595"
        assert decision.family_name == "Иванов"
        assert decision.first_name == "Иван"
        assert decision.patronymic == "Иванович"
        assert decision.birth_date == "2000-01-15"
        assert decision.oktmo == "62701000001"
        assert decision.is_historical is True
        assert len(decision.periods) == 1
        assert decision.periods[0].amount == "5000.00"
        assert decision.periods[0].measury_code == "383"
        assert decision.id_measure == decision.id_decision
        assert decision.id_onmsz == "0377"
        assert decision.reason_num == "FACT-001"

    def test_uuid_measure_and_generated_decision_num(self) -> None:
        cfg = ConversionConfig(input_path=Path("."), output_dir=Path("."))
        rec = OldEgissoRecord(
            file_source="sample.xlsx",
            row_index=4,
            lmsz_id="88e2558c-7d6a-42e5-94c8-af9e8444d6c1",
            category_id="d534a0cc-c323-4845-b18f-00ea013493bb",
            onmsz_code="6220.000001",
            snils_recip="11223344595",
            family_name_recip="Иванов",
            name_recip="Иван",
            birth_date_recip="2000-01-15",
            decision_date="2026-11-11",
            date_start="2026-11-06",
            amount=940.13,
        )
        decision, issues = validate_and_convert_record(rec, cfg)
        assert decision is not None
        assert decision.id_onmsz == "6220000001"
        assert decision.code_msz == "6220000001"
        assert decision.reason_num == "РЕШ-20261111-0004"
        assert decision.id_measure == decision.id_decision
        assert decision.code_lmsz == "88e2558c-7d6a-42e5-94c8-af9e8444d6c1"
        assert decision.local_category_code == "d534a0cc-c323-4845-b18f-00ea013493bb"
        assert not [i for i in issues if i.severity.value == "ERROR"]

    def test_invalid_snils_blocks_decision(self) -> None:
        cfg = ConversionConfig(input_path=Path("."), output_dir=Path("."))
        rec = make_valid_record()
        rec.snils_recip = "000-000-000 00"  # Invalid identical digits

        decision, issues = validate_and_convert_record(rec, cfg)
        assert decision is None
        assert any(i.field_name == "СНИЛС_recip" and i.severity == ValidationSeverity.ERROR for i in issues)

    def test_birth_date_after_decision_blocks(self) -> None:
        cfg = ConversionConfig(input_path=Path("."), output_dir=Path("."))
        rec = make_valid_record()
        rec.birth_date_recip = "2025-01-01"
        rec.decision_date = "2024-01-01"

        decision, issues = validate_and_convert_record(rec, cfg)
        assert decision is None
        assert any("рождения не может быть позже" in i.message for i in issues)

    def test_start_date_after_finish_blocks(self) -> None:
        cfg = ConversionConfig(input_path=Path("."), output_dir=Path("."))
        rec = make_valid_record()
        rec.date_start = "2024-06-01"
        rec.date_finish = "2024-05-01"

        decision, issues = validate_and_convert_record(rec, cfg)
        assert decision is None
        assert any("начала назначения не может быть позже даты окончания" in i.message for i in issues)

    def test_empty_recipient_name_blocks(self) -> None:
        cfg = ConversionConfig(input_path=Path("."), output_dir=Path("."))
        rec = make_valid_record()
        rec.family_name_recip = ""

        decision, issues = validate_and_convert_record(rec, cfg)
        assert decision is None
        assert any(i.field_name == "FamilyName_recip" for i in issues)

    def test_numeric_excel_cells_coerced(self) -> None:
        cfg = ConversionConfig(input_path=Path("."), output_dir=Path("."))
        rec = OldEgissoRecord(
            file_source="sample.xlsx",
            row_index=5,
            lmsz_id=377,  # type: ignore[arg-type]
            category_id=101,  # type: ignore[arg-type]
            onmsz_code=377,  # type: ignore[arg-type]
            snils_recip=11223344595,  # type: ignore[arg-type]
            family_name_recip="Иванов",
            name_recip="Иван",
            gender_recip=1,  # type: ignore[arg-type]
            birth_date_recip="2000-01-15",
            decision_date="2024-05-01",
            date_start="2024-05-01",
            amount=3500,
            oktmo=62701000001,  # type: ignore[arg-type]
        )
        decision, issues = validate_and_convert_record(rec, cfg)
        assert decision is not None
        assert decision.snils_recipient == "11223344595"
        assert decision.oktmo == "62701000001"
        assert decision.region_code == "62"
        assert not [i for i in issues if i.severity == ValidationSeverity.ERROR]

    def test_path_year_month_hint_fallback(self) -> None:
        cfg = ConversionConfig(input_path=Path("."), output_dir=Path("."))
        rec = make_valid_record()
        rec.decision_date = None
        rec.date_start = None
        rec.date_finish = None
        rec.year_hint = 2024
        rec.month_hint = 7

        decision, issues = validate_and_convert_record(rec, cfg)
        assert decision is not None
        assert decision.decision_date == "2024-07-01"
        assert decision.date_start == "2024-07-01"
        assert any(i.severity == ValidationSeverity.WARNING and i.field_name == "decision_date" for i in issues)

    def test_related_person_valid_and_invalid(self) -> None:
        cfg = ConversionConfig(input_path=Path("."), output_dir=Path("."))
        rec = make_valid_record()
        rec.snils_reason = "112-233-445 95"
        rec.family_name_reason = "Петрова"
        rec.name_reason = "Анна"
        rec.birth_date_reason = "1980-03-10"

        decision, issues = validate_and_convert_record(rec, cfg)
        assert decision is not None
        assert len(decision.related_persons) == 1
        assert decision.related_persons[0].snils == "11223344595"

        rec_bad = make_valid_record()
        rec_bad.snils_reason = "12345"
        rec_bad.family_name_reason = ""
        decision_bad, bad_issues = validate_and_convert_record(rec_bad, cfg)
        assert decision_bad is None
        assert any(i.field_name == "SNILS_reason" and i.severity == ValidationSeverity.ERROR for i in bad_issues)

    def test_future_decision_date_warning_flk29(self) -> None:
        cfg = ConversionConfig(input_path=Path("."), output_dir=Path("."))
        rec = make_valid_record()
        rec.decision_date = "2099-01-01"
        decision, issues = validate_and_convert_record(rec, cfg)
        assert decision is not None
        assert any("ФЛК №29" in i.message and i.severity == ValidationSeverity.WARNING for i in issues)
