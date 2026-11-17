"""Data normalizers and cleaners for EGISSO and GIS ECP formats."""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any

# Excel epoch: 1899-12-30 (handling the famous Lotus 1-2-3 leap year bug)
EXCEL_EPOCH = datetime(1899, 12, 30)

_UUID_RE = re.compile(
    r"^\{?[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\}?$"
)


def is_uuid_str(raw: str | None) -> bool:
    """Checks whether the given string matches standard GUID/UUID format."""
    if not raw:
        return False
    return bool(_UUID_RE.match(raw.strip()))


def normalize_onmsz_id(raw: Any) -> str:
    """
    Normalizes ONMSZ code to a numeric integer string suitable for ECP `long` field
    `Решение_ОНМСЗ_ИдентификаторОНМСЗ` (e.g. '6220.000001' -> '6220000001').
    If no digits exist, returns the trimmed string or '0'.
    """
    if raw is None:
        return "0"
    raw_str = str(raw).strip()
    if not raw_str:
        return "0"
    digits = re.sub(r"\D", "", raw_str)
    if digits:
        return digits
    return raw_str


def normalize_snils(raw: Any) -> tuple[str | None, str | None]:
    """
    Normalizes and validates SNILS according to Russian Pension Fund (PFR) algorithm.

    Returns:
        tuple[normalized_snils, error_message]
        If valid: ("12345678901", None)
        If invalid: (None, "Reason")
    """
    if raw is None:
        return None, "СНИЛС отсутствует"

    digits = re.sub(r"\D", "", str(raw).strip())
    if not digits:
        return None, "СНИЛС пустой"

    # Pad leading zeros if Excel stripped them (e.g. 9 or 10 digits)
    if len(digits) in (9, 10):
        digits = digits.zfill(11)

    if len(digits) != 11:
        return None, f"Неверная длина СНИЛС ({len(digits)} вместо 11 цифр): '{raw}'"

    # All identical digits check (e.g. 00000000000, 11111111111 are invalid)
    if digits == digits[0] * 11:
        return None, f"СНИЛС не может состоять из одинаковых цифр: '{digits}'"

    number_part = int(digits[:9])
    check_digits = int(digits[9:])

    # Numbers <= 001-001-998 are not verified by checksum
    if number_part <= 1001998:
        return digits, None

    # Calculate PFR checksum
    total = sum(int(digit) * (9 - idx) for idx, digit in enumerate(digits[:9]))

    if total < 100:
        expected = total
    elif total in (100, 101):
        expected = 0
    else:
        rem = total % 101
        expected = 0 if rem in (100, 101) else rem

    if expected != check_digits:
        return None, f"Неверная контрольная сумма СНИЛС (ожидалось {expected:02d}, указано {check_digits:02d}): '{digits}'"

    return digits, None


def format_snils(digits: str) -> str:
    """
    Formats an 11-digit normalized SNILS as 'XXX-XXX-XXX YY', the representation
    used in the official GIS ECP CSV template (e.g. '001-230-354 57').
    Values that are not exactly 11 digits are returned unchanged.
    """
    if len(digits) != 11 or not digits.isdigit():
        return digits
    return f"{digits[0:3]}-{digits[3:6]}-{digits[6:9]} {digits[9:11]}"


def normalize_date(raw: Any) -> tuple[str | None, str | None]:
    """
    Normalizes various date inputs (date, datetime, Excel serial number, string)
    to ISO format 'YYYY-MM-DD'.

    Returns:
        tuple[iso_date, error_message]
    """
    if raw is None:
        return None, "Дата отсутствует"

    if isinstance(raw, datetime):
        return raw.strftime("%Y-%m-%d"), None

    if isinstance(raw, date):
        return raw.strftime("%Y-%m-%d"), None

    if isinstance(raw, bool):
        return None, "Некорректное значение даты (bool)"

    # Excel numeric serial date (e.g. 45300 or 45300.0)
    if isinstance(raw, (int, float)):
        try:
            val_float = float(raw)
            if val_float <= 0 or val_float > 100000:
                return None, f"Некорректное числовое значение даты Excel: {raw}"
            dt = EXCEL_EPOCH + timedelta(days=val_float)
            return dt.strftime("%Y-%m-%d"), None
        except Exception as e:
            return None, f"Ошибка преобразования серийного номера даты Excel '{raw}': {e}"

    raw_str = str(raw).strip()
    if not raw_str:
        return None, "Дата пустая"

    # Check if raw_str is numeric string representing Excel serial float (e.g. '45300.0')
    if re.match(r"^\d{4,6}(\.\d+)?$", raw_str):
        try:
            val_float = float(raw_str)
            dt = EXCEL_EPOCH + timedelta(days=val_float)
            return dt.strftime("%Y-%m-%d"), None
        except Exception:
            pass

    # Standard date patterns
    patterns = [
        ("%Y-%m-%d", r"^\d{4}-\d{2}-\d{2}$"),
        ("%d.%m.%Y", r"^\d{1,2}\.\d{1,2}\.\d{4}$"),
        ("%d/%m/%Y", r"^\d{1,2}/\d{1,2}/\d{4}$"),
        ("%d-%m-%Y", r"^\d{1,2}-\d{1,2}-\d{4}$"),
        ("%Y.%m.%d", r"^\d{4}\.\d{1,2}\.\d{1,2}$"),
    ]

    # If datetime string with time component
    clean_date_part = raw_str.split("T")[0].split(" ")[0]

    for fmt, regex in patterns:
        if re.match(regex, clean_date_part):
            try:
                parsed = datetime.strptime(clean_date_part, fmt).date()
                return parsed.strftime("%Y-%m-%d"), None
            except ValueError:
                continue

    return None, f"Неизвестный формат даты: '{raw_str}'"


def normalize_oktmo(raw: Any, default_oktmo: str = "62701000001") -> tuple[str, str | None]:
    """
    Cleans OKTMO code, strips decimals/dots (e.g. from float conversion '62701000001.0').
    Valid OKTMO is either 8 or 11 digits.

    Returns:
        tuple[cleaned_oktmo, warning_or_error_message]
    """
    if raw is None:
        return default_oktmo, "ОКТМО не указан, использовано значение по умолчанию"

    cleaned = re.sub(r"\D", "", str(raw).split(".")[0].strip())
    if not cleaned:
        return default_oktmo, "ОКТМО пустой, использовано значение по умолчанию"

    if len(cleaned) in (8, 11):
        return cleaned, None

    # Common issue: leading zeros lost (e.g. 7 digits -> pad to 8, 10 digits -> pad to 11)
    if len(cleaned) == 7:
        return cleaned.zfill(8), None
    if len(cleaned) == 10:
        return cleaned.zfill(11), None

    return cleaned, f"Нестандартная длина ОКТМО ({len(cleaned)} цифр): '{cleaned}'"


def normalize_gender(raw: Any) -> str:
    """Normalizes gender to 'М' or 'Ж'."""
    if raw is None:
        return "М"

    val = str(raw).strip().upper()
    if val in ("1", "М", "M", "МУЖ", "МУЖСКОЙ", "MALE"):
        return "М"
    if val in ("2", "Ж", "F", "ЖЕН", "ЖЕНСКИЙ", "FEMALE"):
        return "Ж"

    return "М"


def normalize_amount(raw: Any) -> tuple[str, str | None]:
    """
    Normalizes monetary amount to decimal string format (e.g. '1234.50').

    Returns:
        tuple[amount_str, error_message]
    """
    if raw is None:
        return "0.00", "Сумма отсутствует"

    raw_str = str(raw).strip().replace(" ", "").replace(",", ".")
    if not raw_str:
        return "0.00", "Сумма пустая"

    try:
        dec = Decimal(raw_str)
        return f"{dec:.2f}", None
    except InvalidOperation:
        return "0.00", f"Некорректная сумма: '{raw}'"


def normalize_measury_code(raw: Any, default_code: str = "383") -> str:
    """
    Translates old EGISSO measure unit codes to OKEI.
    Old '01' (рубли) -> '383' (российский рубль по ОКЕИ).
    """
    if raw is None:
        return default_code

    val = str(raw).strip()
    if val in ("01", "1", "руб", "руб.", "рубль", "RUB"):
        return "383"
    if val:
        return val.zfill(3) if len(val) <= 3 and val.isdigit() else val

    return default_code


def clean_cell_to_str(raw: Any) -> str | None:
    """Safely converts an arbitrary cell value (int, float, Decimal, str) to a stripped string or None."""
    if raw is None:
        return None
    if isinstance(raw, bool):
        return "true" if raw else "false"
    if isinstance(raw, int):
        return str(raw)
    if isinstance(raw, float):
        if raw.is_integer():
            return str(int(raw))
        return str(raw).strip()
    if isinstance(raw, Decimal):
        if raw == raw.to_integral_value():
            return str(int(raw))
        return str(raw).strip()
    s = str(raw).strip()
    if not s or s.lower() == "none":
        return None
    return s


def normalize_boolean_flag(raw: Any, default: bool = False) -> bool:
    """Normalizes Excel boolean / Russian 'Да'/'Нет' / '1'/'0' values to bool."""
    if raw is None:
        return default
    if isinstance(raw, bool):
        return raw
    if isinstance(raw, (int, float)):
        return bool(int(raw))
    val = str(raw).strip().lower()
    if val in ("true", "1", "да", "yes", "y", "+"):
        return True
    if val in ("false", "0", "нет", "no", "n", "-"):
        return False
    return default


def normalize_form_code(raw: Any, default: str = "1") -> str:
    """
    Translates EGISSO FormCode ('01', '02', ...) to ECP 1-digit form code ('1' = денежная, etc.).
    """
    s = clean_cell_to_str(raw)
    if not s:
        return default
    if s.isdigit():
        return str(int(s))
    low = s.lower()
    if "денеж" in low:
        return "1"
    if "натур" in low:
        return "2"
    if "льгот" in low:
        return "3"
    if "услуг" in low:
        return "4"
    return s


def extract_year_month_from_path(file_path: str) -> tuple[int, int] | None:
    """
    Extracts year and month from file path or file name.
    Supports formats:
      - 2024/05 or 2024\\05
      - 2024_05 or 2024-05
      - 05_2024 or 05.2024
      - 'май 2024' or '2024_май'
    """
    path_normalized = file_path.replace("\\", "/")

    # Check for YYYY/MM or YYYY-MM or YYYY_MM (2020..2029) without requiring word boundary at _
    match_iso = re.search(r"(?<!\d)(202[3-9]|203[0-9])[-_/.](\d{1,2})(?!\d)", path_normalized)
    if match_iso:
        y, m = int(match_iso.group(1)), int(match_iso.group(2))
        if 1 <= m <= 12:
            return y, m

    # Check for MM/YYYY or MM.YYYY or MM_YYYY
    match_rev = re.search(r"(?<!\d)(\d{1,2})[-_/.]*(202[3-9]|203[0-9])(?!\d)", path_normalized)
    if match_rev:
        m, y = int(match_rev.group(1)), int(match_rev.group(2))
        if 1 <= m <= 12:
            return y, m

    # Russian month names
    ru_months = {
        "янв": 1, "фев": 2, "мар": 3, "апр": 4, "май": 5, "мая": 5,
        "июн": 6, "июл": 7, "авг": 8, "сен": 9, "окт": 10, "ноя": 11, "дек": 12,
    }
    for ru_m, m_num in ru_months.items():
        if ru_m in path_normalized.lower():
            match_y = re.search(r"(?<!\d)(202[3-9]|203[0-9])(?!\d)", path_normalized)
            if match_y:
                return int(match_y.group(1)), m_num

    return None
