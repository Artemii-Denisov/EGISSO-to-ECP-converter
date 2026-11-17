"""Reader, writer and matcher for LMSZ and Category mapping directories."""

from __future__ import annotations

import csv
import json
import logging
import re
from pathlib import Path
from typing import Any

import openpyxl

from egisso_to_ecp.domain.models import LmszMappingRule
from egisso_to_ecp.domain.normalizers import (
    is_uuid_str,
    normalize_code_num,
    normalize_onmsz_id,
)

logger = logging.getLogger(__name__)

# Standard Russian headers for exported mapping files
MAPPING_CSV_HEADERS = [
    "Идентификатор ЛМСЗ (UUID)",
    "Код ЛМСЗ (число)",
    "Наименование ЛМСЗ",
    "Идентификатор категории (UUID)",
    "Код категории (число)",
    "Наименование категории",
    "Код ОНМСЗ",
]


def _clean_header(header: Any) -> str:
    """Removes whitespace, punctuation and lowers header string for fuzzy matching."""
    if not header:
        return ""
    h = str(header).lower().strip()
    return re.sub(r"[\s_()\-.\"]", "", h)


def _detect_columns(headers: list[str]) -> dict[str, int]:
    """Detects standard column indexes by flexible keyword patterns."""
    mapping: dict[str, int] = {}
    cleaned = [_clean_header(h) for h in headers]

    for idx, c in enumerate(cleaned):
        if not c:
            continue
        # 1. LMSZ UUID
        if "категор" not in c and "предыдущ" not in c and any(
            k in c
            for k in [
                "идентификаторлмсз",
                "идмсз",
                "lmszid",
                "lmszuuid",
                "uuidлмсз",
                "uuidмсз",
                "идентификаторлокальноймсз",
            ]
        ):
            mapping.setdefault("lmsz_uuid", idx)
        # 2. LMSZ Code
        elif "категор" not in c and any(
            k in c
            for k in [
                "кодлмсз",
                "кодмсз",
                "lmszcode",
                "кодлокальноймсз",
            ]
        ):
            mapping.setdefault("lmsz_code", idx)
        # 3. LMSZ Name
        elif "категор" not in c and any(
            k in c
            for k in [
                "наименованиелмсз",
                "наименованиемеры",
                "названиелмсз",
                "названиемеры",
                "лмсзнаименование",
                "lmszname",
                "наименование",
                "название",
            ]
        ):
            mapping.setdefault("lmsz_name", idx)
        # 4. Category UUID
        elif any(
            k in c
            for k in [
                "идентификаторлокальнойкатегории",
                "идентификаторкатегории",
                "categoryid",
                "categoryuuid",
                "идкатегории",
                "uuidкатегории",
            ]
        ):
            mapping.setdefault("category_uuid", idx)
        # 5. Category Code
        elif any(
            k in c
            for k in [
                "кодлокальнойкатегории",
                "кодкатегории",
                "categorycode",
            ]
        ):
            mapping.setdefault("category_code", idx)
        # 6. Category Name
        elif any(
            k in c
            for k in [
                "наименованиелокальнойкатегории",
                "наименованиекатегории",
                "названиекатегории",
                "categoryname",
                "категория",
            ]
        ):
            if "код" not in c and "ид" not in c and "uuid" not in c:
                mapping.setdefault("category_name", idx)
        # 7. ONMSZ Code
        elif any(
            k in c
            for k in [
                "кодонмсз",
                "идентификаторонмсз",
                "onmszcode",
                "онмсз",
            ]
        ):
            mapping.setdefault("onmsz_code", idx)

    return mapping


def load_mapping_file(file_path: Path) -> list[LmszMappingRule]:
    """
    Parses a mapping table from CSV, XLSX, or JSON.
    Supports official EGISSO / GIS ECP provider directory exports.
    """
    if not file_path.exists():
        logger.warning("Файл маппинга не найден: %s", file_path)
        return []

    suffix = file_path.suffix.lower()
    if suffix == ".json":
        return load_mapping_json(file_path)
    elif suffix in (".xlsx", ".xls"):
        return _load_mapping_excel(file_path)
    elif suffix == ".csv":
        return _load_mapping_csv(file_path)
    else:
        logger.warning("Неподдерживаемый формат файла маппинга: %s", suffix)
        return []


def _load_mapping_csv(file_path: Path) -> list[LmszMappingRule]:
    raw_bytes = file_path.read_bytes()
    content = ""
    for enc in ["utf-8-sig", "utf-8", "cp1251"]:
        try:
            content = raw_bytes.decode(enc)
            break
        except UnicodeDecodeError:
            continue

    lines = [line.strip() for line in content.splitlines() if line.strip()]
    if not lines:
        return []

    # Detect separator (, or ;)
    first_line = lines[0]
    delimiter = ";" if first_line.count(";") > first_line.count(",") else ","

    reader = csv.reader(lines, delimiter=delimiter)
    rows = list(reader)
    if not rows:
        return []

    header = rows[0]
    col_map = _detect_columns(header)
    return _parse_rows_with_col_map(rows[1:], col_map)


def _load_mapping_excel(file_path: Path) -> list[LmszMappingRule]:
    wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
    ws = wb.active
    if ws is None:
        return []

    rows: list[list[Any]] = []
    for r in ws.iter_rows(values_only=True):
        if any(cell is not None for cell in r):
            rows.append(list(r))
    wb.close()

    if not rows:
        return []

    header = [str(c or "") for c in rows[0]]
    col_map = _detect_columns(header)
    return _parse_rows_with_col_map(rows[1:], col_map)


def _parse_rows_with_col_map(
    rows: list[list[Any]], col_map: dict[str, int]
) -> list[LmszMappingRule]:
    rules: list[LmszMappingRule] = []
    default_onmsz = ""

    # First pass: check if any row represents standalone ONMSZ identifier
    for row in rows:
        if len(row) > 0 and row[0]:
            first_val = str(row[0]).strip()
            # If line is like '6220.000001' and no other columns populated
            if re.match(r"^\d{4}\.\d+$", first_val) or (
                first_val.isdigit() and len(first_val) >= 4 and not is_uuid_str(first_val)
            ):
                default_onmsz = normalize_onmsz_id(first_val)

    def _get_val(row_data: list[Any], key: str) -> str:
        idx = col_map.get(key)
        if idx is not None and idx < len(row_data) and row_data[idx] is not None:
            return str(row_data[idx]).strip()
        return ""

    for row in rows:
        lmsz_uuid = _get_val(row, "lmsz_uuid")
        lmsz_code = normalize_code_num(_get_val(row, "lmsz_code"))
        lmsz_name = _get_val(row, "lmsz_name")
        cat_uuid = _get_val(row, "category_uuid")
        cat_code = normalize_code_num(_get_val(row, "category_code"))
        cat_name = _get_val(row, "category_name")
        onmsz_val = _get_val(row, "onmsz_code")
        onmsz_code = normalize_onmsz_id(onmsz_val) if onmsz_val else default_onmsz

        # Skip rows where neither UUID nor code is present
        if not lmsz_uuid and not lmsz_code and not lmsz_name:
            continue

        rules.append(
            LmszMappingRule(
                lmsz_uuid=lmsz_uuid,
                lmsz_code=lmsz_code,
                lmsz_name=lmsz_name,
                category_uuid=cat_uuid,
                category_code=cat_code,
                category_name=cat_name,
                onmsz_code=onmsz_code,
            )
        )

    logger.info("Загружено правил соответствия ЛМСЗ: %d", len(rules))
    return rules


def save_mapping_csv(rules: list[LmszMappingRule], file_path: Path) -> None:
    """Exports mapping rules to CSV with UTF-8 encoding (with BOM for Excel compatibility)."""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(MAPPING_CSV_HEADERS)
        for r in rules:
            writer.writerow([
                r.lmsz_uuid,
                r.lmsz_code,
                r.lmsz_name,
                r.category_uuid,
                r.category_code,
                r.category_name,
                r.onmsz_code,
            ])


def save_mapping_json(rules: list[LmszMappingRule], file_path: Path) -> None:
    """Serializes mapping rules to a formatted JSON file."""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    data = [r.model_dump() for r in rules]
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_mapping_json(file_path: Path) -> list[LmszMappingRule]:
    """Deserializes mapping rules from JSON."""
    if not file_path.exists():
        return []
    with open(file_path, encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        return [LmszMappingRule(**item) for item in data if isinstance(item, dict)]
    return []


def create_mapping_template_excel(file_path: Path) -> Path:
    """Generates an annotated, user-friendly Excel mapping template (.xlsx)."""
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter

    wb = openpyxl.Workbook()
    ws = wb.active
    assert ws is not None
    ws.title = "Сопоставление мер"

    header_font = Font(name="Segoe UI", size=10, bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
    header_align = Alignment(horizontal="center", vertical="center", wrap_text=True)

    data_font = Font(name="Segoe UI", size=10)
    data_align_center = Alignment(horizontal="center", vertical="center")
    data_align_left = Alignment(horizontal="left", vertical="center")

    thin_border = Border(
        left=Side(style="thin", color="CBD5E1"),
        right=Side(style="thin", color="CBD5E1"),
        top=Side(style="thin", color="CBD5E1"),
        bottom=Side(style="thin", color="CBD5E1"),
    )

    ws.append(MAPPING_CSV_HEADERS)
    ws.row_dimensions[1].height = 28

    for col_idx in range(1, len(MAPPING_CSV_HEADERS) + 1):
        cell = ws.cell(row=1, column=col_idx)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_align
        cell.border = thin_border

    sample_rows = [
        [
            "88e2558c-7d6a-42e5-94c8-af9e8444d6c1",
            "1",
            "Государственная социальная стипендия",
            "d534a0cc-c323-4845-b18f-00ea013493bb",
            "1",
            "Студенты",
            "6220000001",
        ],
        [
            "9901ff43-8b72-4e81-92aa-dbd07489be3c",
            "2",
            "Государственная академическая стипендия",
            "f568dbff-00e0-4736-acdf-dff0fcb8fdf1",
            "1",
            "Студенты",
            "6220000001",
        ],
        [
            "c22b75fb-c0e5-45ff-a45a-c5b10da25e5d",
            "3",
            "Предоставление бесплатного питания",
            "aa171a84-34a9-41dc-980c-80d749b560c7",
            "4",
            "Лица из числа детей-сирот и детей, оставшихся без попечения родителей",
            "6220000001",
        ],
    ]

    for row_idx, row_data in enumerate(sample_rows, start=2):
        ws.append(row_data)
        ws.row_dimensions[row_idx].height = 22
        for col_idx in range(1, len(row_data) + 1):
            cell = ws.cell(row=row_idx, column=col_idx)
            cell.font = data_font
            cell.border = thin_border
            if col_idx in (1, 2, 4, 5, 7):
                cell.alignment = data_align_center
            else:
                cell.alignment = data_align_left

    col_widths = {1: 40, 2: 18, 3: 45, 4: 40, 5: 22, 6: 45, 7: 18}
    for col_idx, w in col_widths.items():
        ws.column_dimensions[get_column_letter(col_idx)].width = w

    ws.freeze_panes = "A2"
    file_path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(file_path)
    wb.close()
    return file_path


def create_mapping_template_csv(file_path: Path) -> Path:
    """Generates a CSV mapping template with UTF-8 BOM encoding."""
    rules = [
        LmszMappingRule(
            lmsz_uuid="88e2558c-7d6a-42e5-94c8-af9e8444d6c1",
            lmsz_code="1",
            lmsz_name="Государственная социальная стипендия",
            category_uuid="d534a0cc-c323-4845-b18f-00ea013493bb",
            category_code="1",
            category_name="Студенты",
            onmsz_code="6220000001",
        ),
        LmszMappingRule(
            lmsz_uuid="9901ff43-8b72-4e81-92aa-dbd07489be3c",
            lmsz_code="2",
            lmsz_name="Государственная академическая стипендия",
            category_uuid="f568dbff-00e0-4736-acdf-dff0fcb8fdf1",
            category_code="1",
            category_name="Студенты",
            onmsz_code="6220000001",
        ),
        LmszMappingRule(
            lmsz_uuid="c22b75fb-c0e5-45ff-a45a-c5b10da25e5d",
            lmsz_code="3",
            lmsz_name="Предоставление бесплатного питания",
            category_uuid="aa171a84-34a9-41dc-980c-80d749b560c7",
            category_code="4",
            category_name="Лица из числа детей-сирот и детей, оставшихся без попечения родителей",
            onmsz_code="6220000001",
        ),
    ]
    save_mapping_csv(rules, file_path)
    return file_path

