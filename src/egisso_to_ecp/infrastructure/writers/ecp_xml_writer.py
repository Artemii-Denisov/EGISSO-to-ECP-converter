"""Hierarchical GIS ECP XML (МСЗСР) writer according to SFR/NSUD specification."""

from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from pathlib import Path
from xml.dom import minidom

from egisso_to_ecp.domain.models import EcpPackage
from egisso_to_ecp.domain.normalizers import format_snils

logger = logging.getLogger(__name__)

XML_NAMESPACE = "urn://x-artefacts-sfr-gov-ru/mszsr/1.0.0"


class EcpXmlWriter:
    """Writes GIS ECP compliant hierarchical XML (МСЗСР) packages."""

    def __init__(self, output_dir: Path) -> None:
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def write_package(self, package: EcpPackage) -> Path:
        """
        Writes an EcpPackage to an XML file according to SFR / NSUD МСЗСР specification.
        Returns the path of the created file.
        """
        filename = f"Пакет_Решений_{package.year_month}_{package.package_id}.xml"
        file_path = self.output_dir / filename

        root = ET.Element("ЭДСФР", attrib={"xmlns": XML_NAMESPACE})

        pkg_attrs = {
            "ПоставщикИнформации": package.provider_code,
            "ИДПакета": package.package_id,
            "КоличествоЗаписей": str(package.total_records),
        }
        pkg_elem = ET.SubElement(root, "МСЗСР", attrib=pkg_attrs)

        for dec in package.decisions:
            dec_attrs = {
                "ИДЗаписи": dec.id_decision,
                "ТипДокумента": dec.document_type,
                "КодМСЗ": dec.code_msz or dec.id_onmsz,
                "ТипДействия": dec.action_type,
            }
            if dec.code_lmsz:
                dec_attrs["КодЛМСЗ"] = dec.code_lmsz

            dec_elem = ET.SubElement(pkg_elem, "Решение", attrib=dec_attrs)

            # 1. Получатель
            recip_elem = ET.SubElement(dec_elem, "Получатель")
            ET.SubElement(recip_elem, "СНИЛС").text = format_snils(dec.snils_recipient)

            fio_elem = ET.SubElement(recip_elem, "ФИО")
            ET.SubElement(fio_elem, "Фамилия").text = dec.family_name
            ET.SubElement(fio_elem, "Имя").text = dec.first_name
            if dec.patronymic:
                ET.SubElement(fio_elem, "Отчество").text = dec.patronymic

            ET.SubElement(recip_elem, "ДатаРождения").text = dec.birth_date

            # 2. РеквизитыРешения
            reqs_elem = ET.SubElement(dec_elem, "РеквизитыРешения")
            ET.SubElement(reqs_elem, "НомерРешения").text = dec.reason_num or dec.id_decision
            ET.SubElement(reqs_elem, "ДатаРешения").text = dec.decision_date
            ET.SubElement(reqs_elem, "ТехническиеДатаВремя").text = f"{dec.decision_date}T10:00:00"

            # 3. ОНМСЗ
            onmsz_elem = ET.SubElement(dec_elem, "ОНМСЗ")
            if dec.id_onmsz:
                ET.SubElement(onmsz_elem, "ИдентификаторОНМСЗ").text = dec.id_onmsz
            if dec.inn and dec.kpp and dec.ogrn:
                req_onmsz = ET.SubElement(onmsz_elem, "РеквизитыОНМСЗ")
                ET.SubElement(req_onmsz, "ИНН").text = dec.inn
                ET.SubElement(req_onmsz, "КПП").text = dec.kpp
                ET.SubElement(req_onmsz, "ОГРН").text = dec.ogrn

            # 4. СведенияОНазначении
            assign_elem = ET.SubElement(dec_elem, "СведенияОНазначении")
            ET.SubElement(assign_elem, "ОснованиеРешения").text = dec.decision_basis
            if dec.id_statement:
                ET.SubElement(assign_elem, "ИДЗаявления").text = dec.id_statement
            ET.SubElement(assign_elem, "ФормаПредоставления").text = dec.assignment_form
            ET.SubElement(assign_elem, "ПериодичностьПредоставления").text = dec.periodicity
            ET.SubElement(assign_elem, "ИсточникФинансирования").text = dec.funding_source

            # ПериодыНазначения
            for period in dec.periods:
                p_elem = ET.SubElement(assign_elem, "ПериодыНазначения")
                ET.SubElement(p_elem, "СуммаКоличество").text = period.amount
                ET.SubElement(p_elem, "ЕдИзмерения").text = period.measury_code
                ET.SubElement(p_elem, "ДатаС").text = period.date_start
                if period.date_finish:
                    ET.SubElement(p_elem, "ДатаПо").text = period.date_finish
                ET.SubElement(p_elem, "ДенежныйЭквивалент").text = (
                    period.equivalent_amount or period.amount
                )
                if period.monetization is not None:
                    ET.SubElement(p_elem, "ПризнакМонетизации").text = (
                        "true" if period.monetization else "false"
                    )
                if period.comment:
                    ET.SubElement(p_elem, "Комментарий").text = period.comment
                if period.content:
                    ET.SubElement(p_elem, "Содержание").text = period.content

            # СвязанныеЛица
            for rp in dec.related_persons:
                rp_elem = ET.SubElement(assign_elem, "СвязанноеЛицо")
                ET.SubElement(rp_elem, "СНИЛС").text = format_snils(rp.snils)
                rp_fio = ET.SubElement(rp_elem, "ФИО")
                ET.SubElement(rp_fio, "Фамилия").text = rp.family_name
                ET.SubElement(rp_fio, "Имя").text = rp.first_name
                if rp.patronymic:
                    ET.SubElement(rp_fio, "Отчество").text = rp.patronymic
                ET.SubElement(rp_elem, "ДатаРождения").text = rp.birth_date

            ET.SubElement(assign_elem, "ИДМеры").text = dec.id_measure or dec.id_decision
            ET.SubElement(assign_elem, "КодРегиона").text = dec.region_code
            ET.SubElement(assign_elem, "ОКТМО").text = dec.oktmo
            ET.SubElement(assign_elem, "ЛМСЗ").text = (
                dec.lmsz_code_num or dec.code_lmsz or dec.code_msz or dec.id_onmsz
            )
            cat_val = dec.category_code_num or dec.id_category
            ET.SubElement(assign_elem, "КатегорияПолучателяЛокальная").text = cat_val
            ET.SubElement(assign_elem, "КодЛокальнойКатегории").text = (
                dec.local_category_code or cat_val
            )
            ET.SubElement(assign_elem, "ПризнакИсторическихДанных").text = (
                "true" if dec.is_historical else "false"
            )

        # Pretty-print XML with XML declaration
        raw_xml = ET.tostring(root, encoding="utf-8")
        parsed = minidom.parseString(raw_xml)
        pretty_xml = parsed.toprettyxml(indent="  ", encoding="utf-8")

        with open(file_path, "wb") as f:
            f.write(pretty_xml)

        logger.info(
            "XML пакет успешно записан: %s (записей: %d)",
            file_path.name,
            package.total_records,
        )
        return file_path
