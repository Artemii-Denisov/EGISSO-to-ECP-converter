"""Format-Logical Control (FLK) rules according to GIS ECP specification."""

from __future__ import annotations

import uuid
from datetime import date
from typing import TYPE_CHECKING

from egisso_to_ecp.domain.models import (
    EcpDecision,
    EcpPeriod,
    OldEgissoRecord,
    RelatedPerson,
    ValidationIssue,
    ValidationSeverity,
)
from egisso_to_ecp.domain.normalizers import (
    normalize_amount,
    normalize_boolean_flag,
    normalize_date,
    normalize_form_code,
    normalize_gender,
    normalize_measury_code,
    normalize_oktmo,
    normalize_snils,
)

if TYPE_CHECKING:
    from egisso_to_ecp.domain.models import ConversionConfig


def validate_and_convert_record(
    record: OldEgissoRecord,
    config: ConversionConfig,
) -> tuple[EcpDecision | None, list[ValidationIssue]]:
    """
    Validates an incoming EGISSO record against ECP FLK rules and converts it
    to an EcpDecision with associated EcpPeriod if valid.

    Returns:
        tuple[EcpDecision | None, list[ValidationIssue]]
    """
    issues: list[ValidationIssue] = []

    # 1. SNILS
    snils, snils_err = normalize_snils(record.snils_recip)
    if snils_err:
        issues.append(
            ValidationIssue(
                file_source=record.file_source,
                row_index=record.row_index,
                field_name="СНИЛС_recip",
                value=str(record.snils_recip),
                message=snils_err,
                severity=ValidationSeverity.ERROR,
            )
        )

    # 2. Names
    f_name = (record.family_name_recip or "").strip()
    n_name = (record.name_recip or "").strip()
    p_name = (record.patronymic_recip or "").strip() or None

    if not f_name:
        issues.append(
            ValidationIssue(
                file_source=record.file_source,
                row_index=record.row_index,
                field_name="FamilyName_recip",
                value=f_name,
                message="Фамилия получателя не может быть пустой",
                severity=ValidationSeverity.ERROR,
            )
        )
    if not n_name:
        issues.append(
            ValidationIssue(
                file_source=record.file_source,
                row_index=record.row_index,
                field_name="Name_recip",
                value=n_name,
                message="Имя получателя не может быть пустым",
                severity=ValidationSeverity.ERROR,
            )
        )

    # 3. Birth Date
    birth_date, bdate_err = normalize_date(record.birth_date_recip)
    if bdate_err:
        issues.append(
            ValidationIssue(
                file_source=record.file_source,
                row_index=record.row_index,
                field_name="BirthDate_recip",
                value=str(record.birth_date_recip),
                message=f"Ошибка даты рождения: {bdate_err}",
                severity=ValidationSeverity.ERROR,
            )
        )

    # 4. Gender
    gender = normalize_gender(record.gender_recip)

    # 5. Codes: Category and ONMSZ
    category_id = str(record.category_id).strip()
    if not category_id:
        issues.append(
            ValidationIssue(
                file_source=record.file_source,
                row_index=record.row_index,
                field_name="categoryID",
                value=category_id,
                message="ИД категории получателя обязателен",
                severity=ValidationSeverity.ERROR,
            )
        )

    onmsz_code = str(record.onmsz_code or record.lmsz_id).strip()
    if not onmsz_code:
        issues.append(
            ValidationIssue(
                file_source=record.file_source,
                row_index=record.row_index,
                field_name="ONMSZCode",
                value=onmsz_code,
                message="Код ОНМСЗ / МСЗ обязателен",
                severity=ValidationSeverity.ERROR,
            )
        )

    # 6. OKTMO
    oktmo, oktmo_warn = normalize_oktmo(record.oktmo, config.default_oktmo)
    if oktmo_warn:
        issues.append(
            ValidationIssue(
                file_source=record.file_source,
                row_index=record.row_index,
                field_name="OKTMO",
                value=str(record.oktmo),
                message=oktmo_warn,
                severity=ValidationSeverity.WARNING,
            )
        )

    # 7. Dates: decision_date, date_start, date_finish (with path year/month fallback)
    hint_date: str | None = None
    if record.year_hint and record.month_hint:
        hint_date = f"{record.year_hint:04d}-{record.month_hint:02d}-01"

    dec_date: str | None
    is_dec_empty = record.decision_date is None or str(record.decision_date).strip() == ""
    if is_dec_empty and hint_date:
        dec_date = hint_date
        issues.append(
            ValidationIssue(
                file_source=record.file_source,
                row_index=record.row_index,
                field_name="decision_date",
                value=dec_date,
                message=f"Дата решения не указана, восстановлена из пути/имени файла ({dec_date})",
                severity=ValidationSeverity.WARNING,
            )
        )
    else:
        dec_date, dec_err = normalize_date(record.decision_date)
        if dec_err:
            issues.append(
                ValidationIssue(
                    file_source=record.file_source,
                    row_index=record.row_index,
                    field_name="decision_date",
                    value=str(record.decision_date),
                    message=f"Ошибка даты решения: {dec_err}",
                    severity=ValidationSeverity.ERROR,
                )
            )

    start_date: str | None
    is_start_empty = record.date_start is None or str(record.date_start).strip() == ""
    if is_start_empty and hint_date:
        start_date = hint_date
        issues.append(
            ValidationIssue(
                file_source=record.file_source,
                row_index=record.row_index,
                field_name="dateStart",
                value=start_date,
                message=f"Дата начала не указана, восстановлена из пути/имени файла ({start_date})",
                severity=ValidationSeverity.WARNING,
            )
        )
    else:
        start_date, start_err = normalize_date(record.date_start)
        if start_err:
            issues.append(
                ValidationIssue(
                    file_source=record.file_source,
                    row_index=record.row_index,
                    field_name="dateStart",
                    value=str(record.date_start),
                    message=f"Ошибка даты начала: {start_err}",
                    severity=ValidationSeverity.ERROR,
                )
            )

    finish_date: str | None = None
    if record.date_finish:
        finish_date, finish_err = normalize_date(record.date_finish)
        if finish_err:
            issues.append(
                ValidationIssue(
                    file_source=record.file_source,
                    row_index=record.row_index,
                    field_name="dateFinish",
                    value=str(record.date_finish),
                    message=f"Ошибка даты окончания: {finish_err}",
                    severity=ValidationSeverity.WARNING,
                )
            )

    # Cross-date validation
    if start_date and finish_date and start_date > finish_date:
        issues.append(
            ValidationIssue(
                file_source=record.file_source,
                row_index=record.row_index,
                field_name="dateStart_dateFinish",
                value=f"{start_date} > {finish_date}",
                message="Дата начала назначения не может быть позже даты окончания",
                severity=ValidationSeverity.ERROR,
            )
        )

    if birth_date and dec_date and birth_date > dec_date:
        issues.append(
            ValidationIssue(
                file_source=record.file_source,
                row_index=record.row_index,
                field_name="BirthDate_decisionDate",
                value=f"{birth_date} > {dec_date}",
                message="Дата рождения не может быть позже даты принятия решения",
                severity=ValidationSeverity.ERROR,
            )
        )

    if dec_date and dec_date > date.today().strftime("%Y-%m-%d"):
        issues.append(
            ValidationIssue(
                file_source=record.file_source,
                row_index=record.row_index,
                field_name="decision_date",
                value=dec_date,
                message="Дата решения позже текущей даты (ФЛК №29)",
                severity=ValidationSeverity.WARNING,
            )
        )

    # 8. Amount, Equivalent Amount, Form, Monetization and Measury Code
    amount_str, amt_err = normalize_amount(record.amount)
    if amt_err:
        issues.append(
            ValidationIssue(
                file_source=record.file_source,
                row_index=record.row_index,
                field_name="amount",
                value=str(record.amount),
                message=amt_err,
                severity=ValidationSeverity.WARNING,
            )
        )

    eq_amount_str: str | None = None
    if record.equivalent_amount is not None and str(record.equivalent_amount).strip() != "":
        eq_val, eq_err = normalize_amount(record.equivalent_amount)
        if eq_err:
            issues.append(
                ValidationIssue(
                    file_source=record.file_source,
                    row_index=record.row_index,
                    field_name="equivalentAmount",
                    value=str(record.equivalent_amount),
                    message=eq_err,
                    severity=ValidationSeverity.WARNING,
                )
            )
        else:
            eq_amount_str = eq_val

    measury = normalize_measury_code(record.measury_code, config.default_measury_code)
    assignment_form = normalize_form_code(record.form_code, default="1")
    monetization_flag = (
        normalize_boolean_flag(record.monetization)
        if record.monetization is not None and str(record.monetization).strip() != ""
        else None
    )

    # 9. Related person (СвязанноеЛицо / *_reason) validation
    related_persons: list[RelatedPerson] = []
    if record.snils_reason and record.snils_reason.strip():
        rel_snils, rel_snils_err = normalize_snils(record.snils_reason)
        if rel_snils_err:
            issues.append(
                ValidationIssue(
                    file_source=record.file_source,
                    row_index=record.row_index,
                    field_name="SNILS_reason",
                    value=record.snils_reason,
                    message=f"Ошибка СНИЛС связанного лица: {rel_snils_err}",
                    severity=ValidationSeverity.ERROR,
                )
            )
        rel_f = (record.family_name_reason or "").strip()
        rel_n = (record.name_reason or "").strip()
        rel_p = (record.patronymic_reason or "").strip() or None
        if not rel_f or not rel_n:
            issues.append(
                ValidationIssue(
                    file_source=record.file_source,
                    row_index=record.row_index,
                    field_name="FamilyName_reason",
                    value=f"{rel_f} {rel_n}".strip(),
                    message="Для связанного лица не заполнены фамилия или имя",
                    severity=ValidationSeverity.ERROR,
                )
            )
        rel_bdate, rel_bdate_err = normalize_date(record.birth_date_reason)
        if rel_bdate_err:
            issues.append(
                ValidationIssue(
                    file_source=record.file_source,
                    row_index=record.row_index,
                    field_name="BirthDate_reason",
                    value=str(record.birth_date_reason),
                    message=f"Ошибка даты рождения связанного лица: {rel_bdate_err}",
                    severity=ValidationSeverity.ERROR,
                )
            )
        if rel_snils and rel_f and rel_n and rel_bdate:
            related_persons.append(
                RelatedPerson(
                    snils=rel_snils,
                    family_name=rel_f,
                    first_name=rel_n,
                    patronymic=rel_p,
                    birth_date=rel_bdate,
                )
            )

    # Reason dates if present
    reason_date_str: str | None = None
    if record.reason_date:
        reason_date_str, _ = normalize_date(record.reason_date)

    # Check for blocking errors
    has_fatal_error = any(i.severity == ValidationSeverity.ERROR for i in issues)
    if has_fatal_error or not snils or not birth_date or not dec_date or not start_date:
        return None, issues

    # Generate deterministic or unique decision ID
    decision_id = record.assignment_fact_uuid or record.fact_id or str(uuid.uuid4())
    period_id = f"{decision_id}_P1"
    region_code = oktmo[:2] if len(oktmo) >= 2 and oktmo[:2].isdigit() else config.default_region_code

    period = EcpPeriod(
        id_period=period_id,
        date_start=start_date,
        date_finish=finish_date,
        amount=amount_str,
        measury_code=measury,
        assignment_form=assignment_form,
        equivalent_amount=eq_amount_str,
        monetization=monetization_flag,
        comment=record.comment,
        content=record.content,
    )

    decision = EcpDecision(
        id_decision=decision_id,
        id_statement=None,
        id_onmsz=onmsz_code,
        id_category=category_id,
        snils_recipient=snils,
        family_name=f_name,
        first_name=n_name,
        patronymic=p_name,
        birth_date=birth_date,
        gender=gender,
        oktmo=oktmo,
        document_type="3",
        action_type="1",
        decision_basis="1",
        decision_type="01",
        decision_date=dec_date,
        date_start=start_date,
        date_finish=finish_date,
        assignment_form=assignment_form,
        periodicity="2",
        funding_source="1",
        id_measure=record.lmsz_id or None,
        region_code=region_code,
        code_msz=record.lmsz_id or None,
        code_lmsz=record.lmsz_id or None,
        local_category_code=category_id or None,
        reason_type=record.reason_type,
        reason_title=record.reason_title,
        reason_date=reason_date_str,
        reason_num=record.reason_num,
        is_historical=True,
        periods=[period],
        related_persons=related_persons,
        source_file=record.file_source,
        source_row=record.row_index,
    )

    return decision, issues
