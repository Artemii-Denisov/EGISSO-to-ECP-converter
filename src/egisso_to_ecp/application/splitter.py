"""Decision grouping and package chunking logic."""

from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import datetime

from egisso_to_ecp.domain.models import EcpDecision, EcpPackage

# Conservative chunk size: ~20,000 records per package ensures < 18.5 MB CSV
DEFAULT_MAX_RECORDS_PER_CHUNK = 20_000


class PackageSplitter:
    """Splits and chunks decisions into compliant GIS ECP packages."""

    def __init__(
        self,
        provider_code: str = "PFR001",
        split_by_months: bool = True,
        max_records_per_chunk: int = DEFAULT_MAX_RECORDS_PER_CHUNK,
    ) -> None:
        self.provider_code = provider_code
        self.split_by_months = split_by_months
        self.max_records_per_chunk = max_records_per_chunk

    def split_into_packages(self, decisions: list[EcpDecision]) -> list[EcpPackage]:
        """
        Groups decisions by month/measure and partitions large groups into chunks.
        """
        if not decisions:
            return []

        # 1. Group decisions
        grouped: dict[tuple[str, str], list[EcpDecision]] = defaultdict(list)
        now_str = datetime.now().strftime("%Y-%m-%d")

        for dec in decisions:
            if self.split_by_months:
                # Year-Month from decision_date or date_start
                ym = dec.decision_date[:7] if dec.decision_date else dec.date_start[:7]
            else:
                ym = "ALL"

            key = (ym, dec.id_onmsz)
            grouped[key].append(dec)

        packages: list[EcpPackage] = []

        # 2. Chunk each group into packages <= max_records_per_chunk
        for (year_month, measure_code), group_decisions in sorted(grouped.items()):
            chunks = [
                group_decisions[i : i + self.max_records_per_chunk]
                for i in range(0, len(group_decisions), self.max_records_per_chunk)
            ]

            for idx, chunk in enumerate(chunks, start=1):
                chunk_suffix = f"_{idx}" if len(chunks) > 1 else ""
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
