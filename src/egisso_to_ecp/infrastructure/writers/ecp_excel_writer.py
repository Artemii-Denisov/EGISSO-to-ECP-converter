"""GIS ECP Excel (.xlsx) writer."""

from __future__ import annotations

import logging
from pathlib import Path

import openpyxl

from egisso_to_ecp.domain.models import EcpPackage
from egisso_to_ecp.infrastructure.writers.ecp_schema import COL_INDEX, ECP_COLUMNS

logger = logging.getLogger(__name__)


class EcpExcelWriter:
    """Writes GIS ECP compliant 107-column Excel packages."""

    def __init__(self, output_dir: Path) -> None:
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def write_package(self, package: EcpPackage) -> Path:
        """
        Writes an EcpPackage to an Excel (.xlsx) file.
        Returns the path of the created file.
        """
        filename = f"Пакет_Решений_{package.year_month}_{package.package_id}.xlsx"
        file_path = self.output_dir / filename

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Пакет"

        total_cols = len(ECP_COLUMNS)

        # 1. Header row
        ws.append(list(ECP_COLUMNS))

        # 2. Package Base Row
        base_row = [""] * total_cols
        base_row[COL_INDEX["ПоставщикИнформации"]] = package.provider_code
        base_row[COL_INDEX["ИДПакета"]] = package.package_id
        base_row[COL_INDEX["КоличествоЗаписей"]] = str(package.total_records)
        ws.append(base_row)

        # 3. Decision & Period rows
        for dec in package.decisions:
            dec_row = [""] * total_cols
            dec_row[COL_INDEX["Решение_ИДЗаписи"]] = dec.id_decision
            dec_row[COL_INDEX["Решение_ТипДокумента"]] = "01"
            dec_row[COL_INDEX["Решение_Получатель_СНИЛС"]] = dec.snils_recipient
            dec_row[COL_INDEX["Решение_Получатель_ФИО_Фамилия"]] = dec.family_name
            dec_row[COL_INDEX["Решение_Получатель_ФИО_Имя"]] = dec.first_name
            if dec.patronymic:
                dec_row[COL_INDEX["Решение_Получатель_ФИО_Отчество"]] = dec.patronymic
            dec_row[COL_INDEX["Решение_Получатель_ДатаРождения"]] = dec.birth_date
            dec_row[COL_INDEX["Решение_РеквизитыРешения_НомерРешения"]] = dec.reason_num or dec.id_decision[:12]
            dec_row[COL_INDEX["Решение_РеквизитыРешения_ДатаРешения"]] = dec.decision_date
            dec_row[COL_INDEX["Решение_РеквизитыРешения_ТехническиеДатаВремя"]] = f"{dec.decision_date}T10:00:00"
            dec_row[COL_INDEX["Решение_ОНМСЗ_ИдентификаторОНМСЗ"]] = dec.id_onmsz
            dec_row[COL_INDEX["Решение_КодМСЗ"]] = dec.id_onmsz
            dec_row[COL_INDEX["Решение_ТипДействия"]] = "1"
            dec_row[COL_INDEX["Решение_СведенияОНазначении_ФормаПредоставления"]] = "01"
            dec_row[COL_INDEX["Решение_СведенияОНазначении_ПериодичностьПредоставления"]] = "01"
            dec_row[COL_INDEX["Решение_СведенияОНазначении_ОКТМО"]] = dec.oktmo
            dec_row[COL_INDEX["Решение_СведенияОНазначении_КодЛокальнойКатегории"]] = dec.id_category
            dec_row[COL_INDEX["Решение_СведенияОНазначении_ПризнакИсторическихДанных"]] = (
                "true" if dec.is_historical else "false"
            )

            if dec.periods:
                first_p = dec.periods[0]
                dec_row[COL_INDEX["Решение_СведенияОНазначении_ПериодыНазначения_СуммаКоличество"]] = first_p.amount
                dec_row[COL_INDEX["Решение_СведенияОНазначении_ПериодыНазначения_ЕдИзмерения"]] = first_p.measury_code
                dec_row[COL_INDEX["Решение_СведенияОНазначении_ПериодыНазначения_ДатаС"]] = first_p.date_start
                if first_p.date_finish:
                    dec_row[COL_INDEX["Решение_СведенияОНазначении_ПериодыНазначения_ДатаПо"]] = first_p.date_finish
                dec_row[COL_INDEX["Решение_СведенияОНазначении_ПериодыНазначения_ДенежныйЭквивалент"]] = first_p.amount

            ws.append(dec_row)

            for extra_p in dec.periods[1:]:
                sub_row = [""] * total_cols
                sub_row[COL_INDEX["Решение_СведенияОНазначении_ПериодыНазначения_СуммаКоличество"]] = extra_p.amount
                sub_row[COL_INDEX["Решение_СведенияОНазначении_ПериодыНазначения_ЕдИзмерения"]] = extra_p.measury_code
                sub_row[COL_INDEX["Решение_СведенияОНазначении_ПериодыНазначения_ДатаС"]] = extra_p.date_start
                if extra_p.date_finish:
                    sub_row[COL_INDEX["Решение_СведенияОНазначении_ПериодыНазначения_ДатаПо"]] = extra_p.date_finish
                sub_row[COL_INDEX["Решение_СведенияОНазначении_ПериодыНазначения_ДенежныйЭквивалент"]] = extra_p.amount
                ws.append(sub_row)

        wb.save(file_path)
        wb.close()

        logger.info("Excel пакет успешно записан: %s (записей: %d)", file_path.name, package.total_records)
        return file_path
