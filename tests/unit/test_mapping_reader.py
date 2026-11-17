"""Unit tests for LMSZ and Category mapping reader, matcher, and persistence."""

from __future__ import annotations

import csv
from pathlib import Path

from egisso_to_ecp.domain.flk_rules import find_matching_rule
from egisso_to_ecp.domain.models import LmszMappingRule, OldEgissoRecord
from egisso_to_ecp.infrastructure.readers.mapping_reader import (
    create_mapping_template_csv,
    create_mapping_template_excel,
    load_mapping_file,
    load_mapping_json,
    save_mapping_csv,
    save_mapping_json,
)


def test_load_mapping_csv_comma(tmp_path: Path) -> None:
    csv_file = tmp_path / "mapping.csv"
    content = (
        "Идентификатор ЛМСЗ,Код ЛМСЗ,Наименование ЛМСЗ,Идентификатор локальной категории,Код локальной категории,Наименование локальной категории,Код ОНМСЗ\n"
        "88e2558c-7d6a-42e5-94c8-af9e8444d6c1,1.0,Социальная стипендия,d534a0cc-c323-4845-b18f-00ea013493bb,1.0,Студенты,6220000001\n"
        "c22b75fb-c0e5-45ff-a45a-c5b10da25e5d,3.0,Бесплатное питание,aa171a84-34a9-41dc-980c-80d749b560c7,4.0,Сироты,6220000001\n"
    )
    csv_file.write_text(content, encoding="utf-8")

    rules = load_mapping_file(csv_file)
    assert len(rules) == 2
    r1 = rules[0]
    assert r1.lmsz_uuid == "88e2558c-7d6a-42e5-94c8-af9e8444d6c1"
    assert r1.lmsz_code == "1"
    assert r1.category_uuid == "d534a0cc-c323-4845-b18f-00ea013493bb"
    assert r1.category_code == "1"
    assert r1.category_name == "Студенты"
    assert r1.onmsz_code == "6220000001"


def test_load_mapping_csv_semicolon_and_cp1251(tmp_path: Path) -> None:
    csv_file = tmp_path / "mapping_1251.csv"
    content = (
        "LMSZID;КодЛМСЗ;Название;CategoryID;КодКатегории;Категория\n"
        "a485f4af-2f6a-4e2e-9373-e30c920c90d8;6;Личная гигиена;f446f551-a565-4f28-9fc7-a9f96c1c745b;4;Дети-сироты\n"
    )
    csv_file.write_bytes(content.encode("cp1251"))

    rules = load_mapping_file(csv_file)
    assert len(rules) == 1
    assert rules[0].lmsz_uuid == "a485f4af-2f6a-4e2e-9373-e30c920c90d8"
    assert rules[0].lmsz_code == "6"
    assert rules[0].category_name == "Дети-сироты"


def test_save_and_load_mapping_json(tmp_path: Path) -> None:
    json_file = tmp_path / "mapping.json"
    rules = [
        LmszMappingRule(
            lmsz_uuid="88e2558c-7d6a-42e5-94c8-af9e8444d6c1",
            lmsz_code="1",
            lmsz_name="Соцстипендия",
            category_uuid="d534a0cc-c323-4845-b18f-00ea013493bb",
            category_code="1",
            category_name="Студенты",
            onmsz_code="6220000001",
        )
    ]
    save_mapping_json(rules, json_file)
    assert json_file.exists()

    loaded = load_mapping_json(json_file)
    assert len(loaded) == 1
    assert loaded[0].lmsz_uuid == rules[0].lmsz_uuid
    assert loaded[0].lmsz_name == "Соцстипендия"


def test_save_mapping_csv(tmp_path: Path) -> None:
    csv_file = tmp_path / "export.csv"
    rules = [
        LmszMappingRule(
            lmsz_uuid="88e2558c-7d6a-42e5-94c8-af9e8444d6c1",
            lmsz_code="1",
            lmsz_name="Соцстипендия",
            category_uuid="d534a0cc-c323-4845-b18f-00ea013493bb",
            category_code="1",
            category_name="Студенты",
            onmsz_code="6220000001",
        )
    ]
    save_mapping_csv(rules, csv_file)
    assert csv_file.exists()

    with open(csv_file, encoding="utf-8-sig") as f:
        reader = list(csv.reader(f))
        assert len(reader) == 2  # header + 1 row
        assert reader[1][0] == "88e2558c-7d6a-42e5-94c8-af9e8444d6c1"


def test_find_matching_rule_priorities() -> None:
    rule_stipend_student = LmszMappingRule(
        lmsz_uuid="88e2558c-7d6a-42e5-94c8-af9e8444d6c1",
        lmsz_code="1",
        lmsz_name="Государственная социальная стипендия",
        category_uuid="d534a0cc-c323-4845-b18f-00ea013493bb",
        category_code="1",
        category_name="Студенты",
        onmsz_code="6220000001",
    )
    rule_stipend_orphan = LmszMappingRule(
        lmsz_uuid="88e2558c-7d6a-42e5-94c8-af9e8444d6c1",
        lmsz_code="1",
        lmsz_name="Государственная социальная стипендия",
        category_uuid="f45fcee2-6d15-4b23-99a7-7f12f9709c2c",
        category_code="3",
        category_name="Дети-сироты",
        onmsz_code="6220000001",
    )
    rules = [rule_stipend_student, rule_stipend_orphan]

    # 1. Exact UUID match on both
    rec1 = OldEgissoRecord(
        file_source="test.xlsx",
        row_index=1,
        lmsz_id="88e2558c-7d6a-42e5-94c8-af9e8444d6c1",
        category_id="d534a0cc-c323-4845-b18f-00ea013493bb",
    )
    m1 = find_matching_rule(rec1, rules)
    assert m1 is not None
    assert m1.category_code == "1"

    # 2. UUID match on LMSZ and numeric category code match
    rec2 = OldEgissoRecord(
        file_source="test.xlsx",
        row_index=2,
        lmsz_id="88e2558c-7d6a-42e5-94c8-af9e8444d6c1",
        category_id="3.0",
    )
    m2 = find_matching_rule(rec2, rules)
    assert m2 is not None
    assert m2.category_name == "Дети-сироты"

    # 3. Numeric code match on both (1.0 and 1.0)
    rec3 = OldEgissoRecord(
        file_source="test.xlsx",
        row_index=3,
        lmsz_id="1.0",
        category_id="1.0",
    )
    m3 = find_matching_rule(rec3, rules)
    assert m3 is not None
    assert m3.lmsz_uuid == "88e2558c-7d6a-42e5-94c8-af9e8444d6c1"
    assert m3.category_code == "1"

    # 4. Measure name substring fallback
    rec4 = OldEgissoRecord(
        file_source="test.xlsx",
        row_index=4,
        lmsz_id="",
        category_id="",
        content="Выплата государственной социальной стипендии за май",
    )
    m4 = find_matching_rule(rec4, rules)
    assert m4 is not None
    assert m4.lmsz_code == "1"


def test_create_mapping_template_excel(tmp_path: Path) -> None:
    tpl_path = tmp_path / "Шаблон_сопоставления_мер_ЕЦП.xlsx"
    res = create_mapping_template_excel(tpl_path)
    assert res == tpl_path
    assert tpl_path.exists()
    assert tpl_path.stat().st_size > 1000

    # Ensure it can be loaded by the mapping reader
    loaded = load_mapping_file(tpl_path)
    assert len(loaded) == 3
    assert loaded[0].lmsz_uuid == "88e2558c-7d6a-42e5-94c8-af9e8444d6c1"
    assert loaded[0].lmsz_code == "1"
    assert "стипендия" in loaded[0].lmsz_name


def test_create_mapping_template_csv(tmp_path: Path) -> None:
    tpl_path = tmp_path / "Шаблон_сопоставления_мер_ЕЦП.csv"
    res = create_mapping_template_csv(tpl_path)
    assert res == tpl_path
    assert tpl_path.exists()

    loaded = load_mapping_file(tpl_path)
    assert len(loaded) == 3
    assert loaded[0].lmsz_uuid == "88e2558c-7d6a-42e5-94c8-af9e8444d6c1"

