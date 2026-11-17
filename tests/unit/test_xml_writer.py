"""Unit tests for EcpXmlWriter."""

import xml.etree.ElementTree as ET
from pathlib import Path

from egisso_to_ecp.domain.models import EcpDecision, EcpPackage, EcpPeriod, RelatedPerson
from egisso_to_ecp.infrastructure.writers.ecp_xml_writer import XML_NAMESPACE, EcpXmlWriter


def make_test_package() -> EcpPackage:
    period = EcpPeriod(
        id_period="DEC-01_P1",
        date_start="2024-05-01",
        date_finish="2024-05-31",
        amount="3500.00",
        measury_code="383",
        assignment_form="3",
        equivalent_amount="3500.00",
        monetization=True,
        comment="Выплата за май",
        content="Соцстипендия",
    )
    rel_person = RelatedPerson(
        snils="11223344595",
        family_name="Иванова",
        first_name="Мария",
        birth_date="1980-01-01",
    )
    dec = EcpDecision(
        id_decision="febd4cc8-61b3-4f6e-befd-76744a36f786",
        id_onmsz="6220000001",
        inn="3307010131",
        kpp="333401001",
        ogrn="1023302154226",
        id_category="101",
        snils_recipient="11223344595",
        family_name="Иванов",
        first_name="Иван",
        patronymic="Иванович",
        birth_date="2002-04-12",
        gender="М",
        oktmo="17735000",
        decision_date="2024-05-10",
        date_start="2024-05-01",
        date_finish="2024-05-31",
        code_msz="220119",
        code_lmsz="fea26e12-853b-4da9-98b6-1a25048fe6f4",
        lmsz_code_num="3200133300153",
        category_code_num="3200133300153115004",
        funding_source="5",
        periods=[period],
        related_persons=[rel_person],
    )
    return EcpPackage(
        package_id="7d9f8e44-4fc2-4635-a629-4c31e768cc75",
        provider_code="1788",
        creation_date="2024-05-15",
        year_month="2024-05",
        decisions=[dec],
    )


def test_xml_writer_creates_valid_structure(tmp_path: Path) -> None:
    writer = EcpXmlWriter(tmp_path)
    pkg = make_test_package()
    xml_file = writer.write_package(pkg)

    assert xml_file.exists()
    assert xml_file.suffix == ".xml"

    # Verify XML can be parsed
    tree = ET.parse(xml_file)
    root = tree.getroot()

    ns = {"ns": XML_NAMESPACE}
    assert root.tag.endswith("ЭДСФР")
    assert XML_NAMESPACE in root.tag

    mszsr = root.find("ns:МСЗСР", ns)
    assert mszsr is not None
    assert mszsr.attrib["ПоставщикИнформации"] == "1788"
    assert mszsr.attrib["ИДПакета"] == "7d9f8e44-4fc2-4635-a629-4c31e768cc75"
    assert mszsr.attrib["КоличествоЗаписей"] == "1"

    decision = mszsr.find("ns:Решение", ns)
    assert decision is not None
    assert decision.attrib["ИДЗаписи"] == "febd4cc8-61b3-4f6e-befd-76744a36f786"
    assert decision.attrib["ТипДокумента"] == "3"
    assert decision.attrib["КодМСЗ"] == "220119"
    assert decision.attrib["КодЛМСЗ"] == "fea26e12-853b-4da9-98b6-1a25048fe6f4"

    # Check recipient
    recip = decision.find("ns:Получатель", ns)
    assert recip is not None
    assert recip.findtext("ns:СНИЛС", namespaces=ns) == "112-233-445 95"
    assert recip.findtext("ns:ФИО/ns:Фамилия", namespaces=ns) == "Иванов"
    assert recip.findtext("ns:ФИО/ns:Имя", namespaces=ns) == "Иван"
    assert recip.findtext("ns:ФИО/ns:Отчество", namespaces=ns) == "Иванович"

    # Check ONMSZ requisites
    onmsz = decision.find("ns:ОНМСЗ", ns)
    assert onmsz is not None
    assert onmsz.findtext("ns:РеквизитыОНМСЗ/ns:ИНН", namespaces=ns) == "3307010131"
    assert onmsz.findtext("ns:РеквизитыОНМСЗ/ns:КПП", namespaces=ns) == "333401001"
    assert onmsz.findtext("ns:РеквизитыОНМСЗ/ns:ОГРН", namespaces=ns) == "1023302154226"

    # Check assignment details
    assign = decision.find("ns:СведенияОНазначении", ns)
    assert assign is not None
    assert assign.findtext("ns:ЛМСЗ", namespaces=ns) == "3200133300153"
    assert assign.findtext("ns:КатегорияПолучателяЛокальная", namespaces=ns) == "3200133300153115004"
    assert assign.findtext("ns:КодЛокальнойКатегории", namespaces=ns) == "3200133300153115004"
    assert assign.findtext("ns:ИсточникФинансирования", namespaces=ns) == "5"
    assert assign.findtext("ns:ПризнакИсторическихДанных", namespaces=ns) == "true"

    # Check period
    period = assign.find("ns:ПериодыНазначения", ns)
    assert period is not None
    assert period.findtext("ns:СуммаКоличество", namespaces=ns) == "3500.00"
    assert period.findtext("ns:ЕдИзмерения", namespaces=ns) == "383"
    assert period.findtext("ns:ПризнакМонетизации", namespaces=ns) == "true"

    # Check related person
    rel = assign.find("ns:СвязанноеЛицо", ns)
    assert rel is not None
    assert rel.findtext("ns:СНИЛС", namespaces=ns) == "112-233-445 95"
    assert rel.findtext("ns:ФИО/ns:Фамилия", namespaces=ns) == "Иванова"
