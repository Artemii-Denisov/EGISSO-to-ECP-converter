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
