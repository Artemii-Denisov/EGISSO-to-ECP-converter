"""Unit tests for data normalizers and validators."""

from datetime import date, datetime

from egisso_to_ecp.domain.normalizers import (
    clean_cell_to_str,
    extract_year_month_from_path,
    is_uuid_str,
    normalize_amount,
    normalize_boolean_flag,
    normalize_date,
    normalize_form_code,
    normalize_gender,
    normalize_measury_code,
    normalize_oktmo,
    normalize_onmsz_id,
    normalize_snils,
)


class TestSnilsNormalizer:
    def test_valid_snils_with_hyphens(self) -> None:
        # Standard valid SNILS: 112-233-445 95 (checksum: 1*9 + 1*8 + 2*7 + 2*6 + 3*5 + 3*4 + 4*3 + 4*2 + 5*1 = 9+8+14+12+15+12+12+8+5 = 95)
        snils, err = normalize_snils("112-233-445 95")
        assert err is None
        assert snils == "11223344595"

    def test_valid_snils_pure_digits(self) -> None:
        snils, err = normalize_snils("11223344595")
        assert err is None
        assert snils == "11223344595"

    def test_invalid_snils_checksum(self) -> None:
        snils, err = normalize_snils("11223344500")
        assert snils is None
        assert err is not None
        assert "Неверная контрольная сумма" in err

    def test_all_identical_digits_invalid(self) -> None:
        snils, err = normalize_snils("11111111111")
        assert snils is None
        assert err is not None
        assert "одинаковых цифр" in err

    def test_invalid_length(self) -> None:
        snils, err = normalize_snils("12345")
        assert snils is None
        assert "Неверная длина" in err

    def test_none_snils(self) -> None:
        snils, err = normalize_snils(None)
        assert snils is None
        assert "отсутствует" in err


class TestDateNormalizer:
    def test_iso_date_string(self) -> None:
        res, err = normalize_date("2024-05-15")
        assert err is None
        assert res == "2024-05-15"

    def test_russian_dot_date_string(self) -> None:
        res, err = normalize_date("15.05.2024")
        assert err is None
        assert res == "2024-05-15"

    def test_slash_date_string(self) -> None:
        res, err = normalize_date("15/05/2024")
        assert err is None
        assert res == "2024-05-15"

    def test_date_object(self) -> None:
        d = date(2025, 1, 10)
        res, err = normalize_date(d)
        assert err is None
        assert res == "2025-01-10"

    def test_datetime_object(self) -> None:
        dt = datetime(2025, 1, 10, 15, 30, 0)
        res, err = normalize_date(dt)
        assert err is None
        assert res == "2025-01-10"

    def test_excel_serial_number(self) -> None:
        # Excel 45300: 2024-01-09
        res, err = normalize_date(45300)
        assert err is None
        assert res == "2024-01-09"

    def test_excel_serial_float_string(self) -> None:
        res, err = normalize_date("45300.0")
        assert err is None
        assert res == "2024-01-09"

    def test_invalid_date_string(self) -> None:
        res, err = normalize_date("not-a-date")
        assert res is None
        assert err is not None
        assert "Неизвестный формат" in err

    def test_bool_date_rejected(self) -> None:
        res, err = normalize_date(True)
        assert res is None
        assert err is not None
        assert "bool" in err


class TestOktmoNormalizer:
    def test_clean_oktmo(self) -> None:
        res, err = normalize_oktmo("62701000001")
        assert res == "62701000001"
        assert err is None

    def test_oktmo_with_float_dot(self) -> None:
        res, err = normalize_oktmo("62701000001.0")
        assert res == "62701000001"
        assert err is None

    def test_default_oktmo_on_none(self) -> None:
        res, warn = normalize_oktmo(None, default_oktmo="62701000001")
        assert res == "62701000001"
        assert warn is not None


class TestPathDateExtractor:
    def test_extract_from_year_month_folder(self) -> None:
        path = "C:/welfare_data/2024/05/payments.xlsx"
        res = extract_year_month_from_path(path)
        assert res == (2024, 5)

    def test_extract_from_filename_hyphen(self) -> None:
        path = "C:/data/stipend_2025-11.xlsx"
        res = extract_year_month_from_path(path)
        assert res == (2025, 11)

    def test_extract_from_filename_underscore(self) -> None:
        path = "C:/data/2026_03_social.xlsx"
        res = extract_year_month_from_path(path)
        assert res == (2026, 3)

    def test_extract_from_russian_month(self) -> None:
        path = "C:/data/2024/май/выплаты.xlsx"
        res = extract_year_month_from_path(path)
        assert res == (2024, 5)


class TestOtherNormalizers:
    def test_normalize_gender(self) -> None:
        assert normalize_gender("Мужской") == "М"
        assert normalize_gender("Ж") == "Ж"
        assert normalize_gender("1") == "М"
        assert normalize_gender("2") == "Ж"

    def test_normalize_amount(self) -> None:
        res, err = normalize_amount("1 250,50")
        assert res == "1250.50"
        assert err is None

    def test_normalize_measury_code(self) -> None:
        assert normalize_measury_code("01") == "383"
        assert normalize_measury_code("руб.") == "383"
        assert normalize_measury_code("383") == "383"

    def test_clean_cell_to_str_numeric_cells(self) -> None:
        assert clean_cell_to_str(16503111144) == "16503111144"
        assert clean_cell_to_str(45300.0) == "45300"
        assert clean_cell_to_str(125.5) == "125.5"
        assert clean_cell_to_str(None) is None
        assert clean_cell_to_str("  ") is None

    def test_normalize_boolean_flag(self) -> None:
        assert normalize_boolean_flag("Да") is True
        assert normalize_boolean_flag("true") is True
        assert normalize_boolean_flag(1) is True
        assert normalize_boolean_flag("Нет") is False
        assert normalize_boolean_flag(0) is False

    def test_normalize_form_code(self) -> None:
        assert normalize_form_code("01") == "1"
        assert normalize_form_code("02") == "2"
        assert normalize_form_code("Денежная") == "1"

    def test_is_uuid_str(self) -> None:
        assert is_uuid_str("88e2558c-7d6a-42e5-94c8-af9e8444d6c1") is True
        assert is_uuid_str("{88e2558c-7d6a-42e5-94c8-af9e8444d6c1}") is True
        assert is_uuid_str("6220.000001") is False
        assert is_uuid_str(None) is False

    def test_normalize_onmsz_id(self) -> None:
        assert normalize_onmsz_id("6220.000001") == "6220000001"
        assert normalize_onmsz_id(" 0377 ") == "0377"
        assert normalize_onmsz_id(None) == "0"
