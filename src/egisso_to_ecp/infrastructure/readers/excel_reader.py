"""Excel reader for EGISSO registry files with robust column mapping."""

from __future__ import annotations

import logging
import re
from collections.abc import Generator
from pathlib import Path
from typing import Any

import openpyxl

from egisso_to_ecp.domain.exceptions import ParsingError
from egisso_to_ecp.domain.models import OldEgissoRecord

logger = logging.getLogger(__name__)

# Canonical field mapping dictionary
FIELD_ALIASES: dict[str, list[str]] = {
    "snils_recip": ["snils_recip", "снилс_recip", "снилс", "snils", "снилсполучателя"],
    "family_name_recip": ["familyname_recip", "фамилия_recip", "фамилия", "familyname"],
    "name_recip": ["name_recip", "имя_recip", "имя", "name", "firstname"],
    "patronymic_recip": ["patronymic_recip", "отчество_recip", "отчество", "patronymic"],
    "gender_recip": ["gender_recip", "пол_recip", "пол", "gender"],
    "birth_date_recip": ["birthdate_recip", "датарождения_recip", "датарождения", "birthdate"],
    "decision_date": ["decision_date", "decisiondate", "датарешения", "дата_решения"],
    "date_start": ["datestart", "датаначала", "дата_начала", "датаназначения"],
    "date_finish": ["datefinish", "датаокончания", "дата_окончания"],
    "amount": ["amount", "сумма", "размер", "размерпособия"],
    "measury_code": ["measurycode", "единицаизмерения", "океи", "кодединицыизмерения"],
    "onmsz_code": ["onmszcode", "онмсз", "кодонмсз", "код_онмсз"],
    "category_id": ["categoryid", "категория", "идкатегории", "код_категории"],
    "lmsz_id": ["lmszid", "мсз", "кодмсз", "ид_мсз", "идмсз"],
    "oktmo": ["oktmo", "октмо"],
    "kbk": ["kbk", "кбк"],
    "fact_id": ["fact", "fact_id", "идфакта", "идентификаторфакта"],
    "reason_type": ["reasontype", "типдокументаоснования", "виддокумента"],
    "reason_title": ["reasontitle", "наименованиедокумента"],
    "reason_date": ["reasondate", "датадокументаоснования", "датадокумента"],
    "reason_num": ["reasonnum", "номердокументаоснования", "номердокумента"],
}


def _clean_header(header: Any) -> str:
    """Normalizes header string for fuzzy alias lookup."""
    if header is None:
        return ""
    # Remove all non-alphanumeric chars and convert to lower
    return re.sub(r"[\s_.\-()]+", "", str(header).strip().lower())


class ExcelRegistryReader:
    """Reads Excel (.xlsx/.xls) registries and streams OldEgissoRecord models."""

    def __init__(self, file_path: Path) -> None:
        self.file_path = file_path

    def read_records(self) -> Generator[OldEgissoRecord, None, None]:
        """Streams records from the first active worksheet."""
        try:
            # openpyxl with data_only=True evaluates Excel formulas
            wb = openpyxl.load_workbook(
                filename=str(self.file_path),
                read_only=True,
                data_only=True,
            )
        except Exception as e:
            raise ParsingError(f"Не удалось открыть файл Excel '{self.file_path.name}': {e}") from e

        try:
            ws = wb.active
            if ws is None:
                raise ParsingError(f"В файле '{self.file_path.name}' нет активных листов")

            rows_iter = ws.iter_rows(values_only=True)
            try:
                raw_headers = next(rows_iter)
            except StopIteration:
                return

            if not raw_headers:
                return

            col_index_to_field = self._map_columns(raw_headers)
            required_fields = {"snils_recip", "family_name_recip", "name_recip"}
            mapped_fields = set(col_index_to_field.values())

            missing_critical = required_fields - mapped_fields
            if missing_critical:
                logger.warning(
                    "Файл %s: не найдены обязательные столбцы %s. Доступные заголовки: %s",
                    self.file_path.name,
                    missing_critical,
                    raw_headers,
                )

            row_num = 1
            for row in rows_iter:
                row_num += 1
                # Skip entirely empty rows
                if not any(cell is not None and str(cell).strip() != "" for cell in row):
                    continue

                record_dict: dict[str, Any] = {
                    "file_source": self.file_path.name,
                    "row_index": row_num,
                    "raw_extra": {},
                }

                for col_idx, cell_value in enumerate(row):
                    field_name = col_index_to_field.get(col_idx)
                    if field_name:
                        record_dict[field_name] = cell_value
                    elif cell_value is not None and col_idx < len(raw_headers):
                        orig_header = str(raw_headers[col_idx])
                        record_dict["raw_extra"][orig_header] = cell_value

                # Provide fallbacks if missing in row
                if not record_dict.get("lmsz_id"):
                    record_dict["lmsz_id"] = record_dict.get("onmsz_code", "0000")
                if not record_dict.get("onmsz_code"):
                    record_dict["onmsz_code"] = record_dict.get("lmsz_id", "0000")
                if not record_dict.get("category_id"):
                    record_dict["category_id"] = "0"
                if not record_dict.get("gender_recip"):
                    record_dict["gender_recip"] = "М"

                try:
                    record = OldEgissoRecord(**record_dict)
                    yield record
                except Exception as e:
                    logger.debug("Пропуск строки %d в %s из-за ошибки парсинга: %e", row_num, self.file_path.name, e)
        finally:
            wb.close()

    def _map_columns(self, headers: tuple[Any, ...]) -> dict[int, str]:
        """Maps column index to canonical field name with exact match priority."""
        mapping: dict[int, str] = {}
        mapped_canonicals: set[str] = set()
        cleaned_headers = [_clean_header(h) for h in headers]

        # Pass 1: Exact matches (highest priority)
        for canonical_name, aliases in FIELD_ALIASES.items():
            if canonical_name in mapped_canonicals:
                continue
            cleaned_aliases = [_clean_header(a) for a in aliases]
            for idx, h_clean in enumerate(cleaned_headers):
                if not h_clean or idx in mapping:
                    continue
                if h_clean in cleaned_aliases:
                    mapping[idx] = canonical_name
                    mapped_canonicals.add(canonical_name)
                    break

        # Pass 2: Substring matches (alias inside header)
        for canonical_name, aliases in FIELD_ALIASES.items():
            if canonical_name in mapped_canonicals:
                continue
            cleaned_aliases = [_clean_header(a) for a in aliases if len(_clean_header(a)) >= 4]
            for idx, h_clean in enumerate(cleaned_headers):
                if not h_clean or idx in mapping:
                    continue
                # Special case: don't match short 'name' into 'familyname'
                if canonical_name == "name_recip" and "family" in h_clean:
                    continue
                for c_alias in cleaned_aliases:
                    if c_alias in h_clean:
                        mapping[idx] = canonical_name
                        mapped_canonicals.add(canonical_name)
                        break
                if idx in mapping:
                    break

        return mapping
