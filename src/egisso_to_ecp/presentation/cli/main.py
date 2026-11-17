"""Command Line Interface for egisso-to-ecp."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.table import Table

from egisso_to_ecp.application.pipeline import ConversionPipeline
from egisso_to_ecp.domain.models import ConversionConfig

app = typer.Typer(
    name="egisso-to-ecp",
    help="Конвертер исторических данных ЕГИССО в формат ГИС ЕЦП (ЛК РСМСЗ)",
    add_completion=False,
)
console = Console()


@app.command()
def convert(
    input_path: Annotated[
        Path,
        typer.Option(
            "--input",
            "-i",
            help="Путь к исходному каталогу или файлу реестра ЕГИССО (.xlsx)",
            exists=True,
            file_okay=True,
            dir_okay=True,
            readable=True,
            resolve_path=True,
        ),
    ],
    output_dir: Annotated[
        Path,
        typer.Option(
            "--output",
            "-o",
            help="Каталог для сохранения сконвертированных пакетов",
            resolve_path=True,
        ),
    ] = Path("./output"),
    recursive: Annotated[
        bool,
        typer.Option(
            "--recursive/--no-recursive",
            "-r/-R",
            help="Рекурсивный поиск в подкаталогах (по умолчанию: ВКЛ)",
        ),
    ] = True,
    split_months: Annotated[
        bool,
        typer.Option(
            "--split-months/--no-split-months",
            "-m/-M",
            help="Разбивать результат на помесячные файлы (по умолчанию: ВКЛ)",
        ),
    ] = True,
    format_csv: Annotated[
        bool,
        typer.Option(
            "--csv/--no-csv",
            help="Выгружать пакеты в формате CSV (по умолчанию: ВКЛ)",
        ),
    ] = True,
    format_xlsx: Annotated[
        bool,
        typer.Option(
            "--xlsx/--no-xlsx",
            help="Выгружать пакеты в формате Excel (.xlsx) (по умолчанию: ВЫКЛ)",
        ),
    ] = False,
    provider_code: Annotated[
        str,
        typer.Option(
            "--provider",
            "-p",
            help="Код поставщика информации в ГИС ЕЦП",
        ),
    ] = "1788",
    inn: Annotated[
        str,
        typer.Option(
            "--inn",
            help="ИНН организации (ОНМСЗ)",
        ),
    ] = "",
    kpp: Annotated[
        str,
        typer.Option(
            "--kpp",
            help="КПП организации (ОНМСЗ)",
        ),
    ] = "",
    ogrn: Annotated[
        str,
        typer.Option(
            "--ogrn",
            help="ОГРН организации (ОНМСЗ)",
        ),
    ] = "",
    code_tmsz: Annotated[
        str,
        typer.Option(
            "--tmsz",
            help="Код типовой меры в ЕЦП (ТМСЗ, по умолчанию 220119)",
        ),
    ] = "220119",
    code_lmsz: Annotated[
        str,
        typer.Option(
            "--lmsz",
            help="Локальный числовой код меры (ЛМСЗ)",
        ),
    ] = "",
    code_category: Annotated[
        str,
        typer.Option(
            "--category",
            help="Код категории получателя (локальной)",
        ),
    ] = "",
    funding_source: Annotated[
        str,
        typer.Option(
            "--funding",
            help="Код источника финансирования (по умолчанию: 5 - бюджет субъекта РФ)",
        ),
    ] = "5",
    assignment_form: Annotated[
        str,
        typer.Option(
            "--form",
            help="Код формы предоставления (по умолчанию: 3)",
        ),
    ] = "3",
) -> None:
    """Запуск конвертации реестров ЕГИССО в пакеты ГИС ЕЦП."""
    console.print(
        Panel.fit(
            "[bold cyan]Конвертер исторических данных ЕГИССО -> ГИС ЕЦП[/bold cyan]\n"
            f"[dim]Каталог источника: {input_path}[/dim]\n"
            f"[dim]Каталог назначения: {output_dir}[/dim]\n"
            f"[dim]Рекурсивный поиск: {'ВКЛ' if recursive else 'ВЫКЛ'} | Помесячно: {'ВКЛ' if split_months else 'ВЫКЛ'}[/dim]\n"
            f"[dim]Форматы: CSV={'ВКЛ' if format_csv else 'ВЫКЛ'}, XLSX={'ВКЛ' if format_xlsx else 'ВЫКЛ'}[/dim]",
            title="ГИС ЕЦП Миграция",
            border_style="cyan",
        )
    )

    if not format_csv and not format_xlsx:
        console.print("[bold red]Ошибка:[/bold red] Необходимо выбрать хотя бы один формат выгрузки (--csv или --xlsx)")
        raise typer.Exit(code=1)

    config = ConversionConfig(
        input_path=input_path,
        output_dir=output_dir,
        recursive_search=recursive,
        split_by_months=split_months,
        export_csv=format_csv,
        export_xlsx=format_xlsx,
        provider_code=provider_code,
        onmsz_inn=inn,
        onmsz_kpp=kpp,
        onmsz_ogrn=ogrn,
        code_tmsz=code_tmsz,
        code_lmsz_num=code_lmsz,
        code_category_num=code_category,
        funding_source=funding_source,
        assignment_form=assignment_form,
    )

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("[green]Обработка данных...", total=100)

        def on_progress(cur: int, tot: int, status: str) -> None:
            pct = int((cur / max(tot, 1)) * 100)
            progress.update(task, completed=pct, description=f"[green]{status}")

        def on_log(msg: str) -> None:
            # logs handled cleanly
            pass

        pipeline = ConversionPipeline(
            config=config,
            progress_callback=on_progress,
            log_callback=on_log,
        )
        summary = pipeline.run()

    # Results Table
    table = Table(title="Итоги конвертации", show_header=True, header_style="bold magenta")
    table.add_column("Параметр", style="cyan")
    table.add_column("Значение", style="bold green")

    table.add_row("Обработано файлов", str(summary.scanned_files_count))
    table.add_row("Прочитано записей", str(summary.parsed_records_count))
    table.add_row("Валидных решений", str(summary.valid_decisions_count))
    table.add_row("Сформировано пакетов", str(summary.packages_generated_count))
    table.add_row("Файлов CSV", str(len(summary.csv_files_written)))
    table.add_row("Файлов XLSX", str(len(summary.xlsx_files_written)))

    if summary.error_report_path:
        table.add_row("Отчёт об ошибках ФЛК", f"[yellow]{summary.error_report_path}[/yellow]")

    console.print(table)
    console.print("[bold green]Обработка завершена успешно![/bold green]")


@app.command()
def gui() -> None:
    """Запуск графического интерфейса пользователя (GUI)."""
    from egisso_to_ecp.presentation.gui.main import run_gui
    run_gui()


if __name__ == "__main__":
    app()
