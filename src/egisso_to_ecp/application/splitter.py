"""Decision grouping and package chunking logic."""

from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import datetime

from egisso_to_ecp.domain.models import EcpDecision, EcpPackage

# Conservative chunk size: ~20,000 records per package ensures < 18.5 MB CSV
DEFAULT_MAX_RECORDS_PER_CHUNK = 20_000
DEFAULT_MAX_SIZE_MB = 18.5
_HEADER_OVERHEAD_BYTES = 4096
_ROW_SEPARATOR_OVERHEAD_BYTES = 120


def _estimate_decision_bytes(dec: EcpDecision) -> int:
    """Conservatively estimates UTF-8 CSV byte size contributed by one decision and its child rows."""
    row_count = 1 + len(dec.periods) + len(dec.related_persons)
    text_fields = (
        dec.id_decision,
        dec.snils_recipient,
        dec.family_name,
        dec.first_name,
        dec.patronymic or "",
        dec.birth_date,
        dec.decision_date,
        dec.id_onmsz,
        dec.oktmo,
        dec.id_category,
        dec.reason_num or "",
    )
    payload_bytes = sum(len(val.encode("utf-8")) for val in text_fields)
    for period in dec.periods:
        payload_bytes += sum(
            len(val.encode("utf-8"))
            for val in (
                period.amount,
                period.measury_code,
                period.date_start,
                period.date_finish or "",
                period.equivalent_amount or "",
                period.comment or "",
                period.content or "",
            )
        )
    for rp in dec.related_persons:
        payload_bytes += sum(
            len(val.encode("utf-8"))
            for val in (rp.snils, rp.family_name, rp.first_name, rp.patronymic or "", rp.birth_date)
        )
    return payload_bytes + row_count * _ROW_SEPARATOR_OVERHEAD_BYTES


class PackageSplitter:
    """Splits and chunks decisions into compliant GIS ECP packages."""

    def __init__(
        self,
        provider_code: str = "430746",
        split_by_months: bool = True,
        max_records_per_chunk: int = DEFAULT_MAX_RECORDS_PER_CHUNK,
        max_size_mb: float = DEFAULT_MAX_SIZE_MB,
    ) -> None:
        self.provider_code = provider_code
        self.split_by_months = split_by_months
        self.max_records_per_chunk = max_records_per_chunk
        self.max_size_mb = max_size_mb

    def split_into_packages(self, decisions: list[EcpDecision]) -> list[EcpPackage]:
        """
        Groups decisions by month (or single package if split_by_months=False)
        and partitions large groups by record count and max_size_mb.
        """
        if not decisions:
            return []

        # 1. Group decisions by Year-Month (all measures in one monthly file)
        grouped: dict[str, list[EcpDecision]] = defaultdict(list)
        now_str = datetime.now().strftime("%Y-%m-%d")

        for dec in decisions:
            if self.split_by_months:
                ym = dec.decision_date[:7] if dec.decision_date else dec.date_start[:7]
            else:
                ym = "ALL"
            grouped[ym].append(dec)

        max_bytes = int(self.max_size_mb * 1024 * 1024)
        packages: list[EcpPackage] = []

        # 2. Chunk each group by max_records_per_chunk and max_bytes
        for year_month, group_decisions in sorted(grouped.items()):
            chunks: list[list[EcpDecision]] = []
            current_chunk: list[EcpDecision] = []
            current_bytes = _HEADER_OVERHEAD_BYTES

            for dec in group_decisions:
                dec_bytes = _estimate_decision_bytes(dec)
                exceeds_count = len(current_chunk) >= self.max_records_per_chunk
                exceeds_size = current_bytes + dec_bytes > max_bytes
                if current_chunk and (exceeds_count or exceeds_size):
                    chunks.append(current_chunk)
                    current_chunk = []
                    current_bytes = _HEADER_OVERHEAD_BYTES

                current_chunk.append(dec)
                current_bytes += dec_bytes

            if current_chunk:
                chunks.append(current_chunk)

            for idx, chunk in enumerate(chunks, start=1):
                chunk_suffix = f"_{idx}" if len(chunks) > 1 else ""
                unique_measures = {d.id_onmsz for d in chunk if d.id_onmsz}
                measure_code = next(iter(unique_measures)) if len(unique_measures) == 1 else "ALL"
                package_id = f"{uuid.uuid4()}"
                pkg = EcpPackage(
                    package_id=package_id,
                    provider_code=self.provider_code,
                    creation_date=now_str,
                    year_month=f"{year_month}{chunk_suffix}",
                    measure_code=measure_code,
                    decisions=chunk,
                )
                packages.append(pkg)

        return packages
