"""Unit tests for package splitter and chunker."""

from egisso_to_ecp.application.splitter import PackageSplitter
from egisso_to_ecp.domain.models import EcpDecision, EcpPeriod


def make_decision(id_val: str, decision_date: str, measure: str = "0377") -> EcpDecision:
    return EcpDecision(
        id_decision=id_val,
        id_statement=None,
        id_onmsz=measure,
        id_category="101",
        snils_recipient="11223344595",
        family_name="Иванов",
        first_name="Иван",
        birth_date="2000-01-01",
        gender="М",
        oktmo="62701000001",
        decision_date=decision_date,
        date_start=decision_date,
        periods=[
            EcpPeriod(
                id_period=f"{id_val}_P1",
                date_start=decision_date,
                amount="5000.00",
                measury_code="383",
            )
        ],
    )


class TestPackageSplitter:
    def test_split_by_months(self) -> None:
        decisions = [
            make_decision("1", "2024-05-10"),
            make_decision("2", "2024-05-20"),
            make_decision("3", "2024-06-01"),
        ]

        splitter = PackageSplitter(provider_code="TEST01", split_by_months=True)
        packages = splitter.split_into_packages(decisions)

        assert len(packages) == 2
        p_may = [p for p in packages if p.year_month == "2024-05"][0]
        p_jun = [p for p in packages if p.year_month == "2024-06"][0]

        assert p_may.total_records == 2
        assert p_jun.total_records == 1
        assert p_may.provider_code == "TEST01"

    def test_no_split_by_months(self) -> None:
        decisions = [
            make_decision("1", "2024-05-10"),
            make_decision("2", "2024-06-01"),
        ]

        splitter = PackageSplitter(provider_code="TEST01", split_by_months=False)
        packages = splitter.split_into_packages(decisions)

        assert len(packages) == 1
        assert packages[0].year_month == "ALL"
        assert packages[0].total_records == 2

    def test_chunking_when_limit_exceeded(self) -> None:
        decisions = [make_decision(str(i), "2024-05-10") for i in range(5)]

        # Max 2 records per chunk
        splitter = PackageSplitter(provider_code="TEST01", split_by_months=True, max_records_per_chunk=2)
        packages = splitter.split_into_packages(decisions)

        assert len(packages) == 3
        assert packages[0].total_records == 2
        assert packages[1].total_records == 2
        assert packages[2].total_records == 1
        assert packages[0].year_month == "2024-05_1"
        assert packages[1].year_month == "2024-05_2"
        assert packages[2].year_month == "2024-05_3"

    def test_mixed_measures_grouped_in_single_monthly_package(self) -> None:
        decisions = [
            make_decision("1", "2024-05-10", measure="0377"),
            make_decision("2", "2024-05-20", measure="0410"),
        ]
        splitter = PackageSplitter(provider_code="430746", split_by_months=True)
        packages = splitter.split_into_packages(decisions)

        assert len(packages) == 1
        assert packages[0].year_month == "2024-05"
        assert packages[0].measure_code == "ALL"
        assert packages[0].total_records == 2

    def test_chunking_by_max_size_mb(self) -> None:
        decisions = [make_decision(f"ID-{i}-{'X' * 100}", "2024-05-10") for i in range(10)]
        # Very tiny size limit (~5 KB) to force splitting despite max_records_per_chunk=100
        splitter = PackageSplitter(
            provider_code="430746",
            split_by_months=True,
            max_records_per_chunk=100,
            max_size_mb=5 / 1024,
        )
        packages = splitter.split_into_packages(decisions)
        assert len(packages) > 1
        assert sum(p.total_records for p in packages) == 10
