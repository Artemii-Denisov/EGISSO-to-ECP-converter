"""Antigravity / Codex inspired Desktop GUI for egisso-to-ecp."""

from __future__ import annotations

import ctypes
import os
import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QCloseEvent, QColor, QFont, QPalette
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from egisso_to_ecp.domain.models import ConversionConfig, ConversionSummary
from egisso_to_ecp.presentation.gui.worker import ConversionWorker

APP_VERSION = "0.1.0"

LICENSE_AND_DISCLAIMER_TEXT = """Лицензия на бесплатное использование (MIT) и отказ от ответственности

1. Условия использования (лицензия MIT)
Программа распространяется свободно и бесплатно с открытым исходным кодом. Любые физические и юридические лица, включая государственные, муниципальные, образовательные и социальные учреждения (ОНМСЗ), могут безвозмездно устанавливать, запускать, копировать и адаптировать данное ПО без лицензионных отчислений.

2. Независимый статус
Утилита является самостоятельным инструментом подготовки реестров и не является официальным программным продуктом СФР, Минтруда России или операторов ГИС «ЕЦП» / ЕГИССО / ЛК РСМСЗ.

3. Отказ разработчика от ответственности
ПО предоставляется без прямых или подразумеваемых гарантий. Разработчик не несёт ответственности за:
• полноту и достоверность исходных реестров и сформированных выходных файлов (CSV, XLSX);
• результаты прохождения форматно-логического контроля (ФЛК) и приёмки пакетов на портале ГИС «ЕЦП» / ЛК РСМСЗ;
• любые прямые или косвенные убытки, штрафы или нарушение сроков отчётности;
• соблюдение требований Федерального закона № 152-ФЗ «О персональных данных».

Все данные обрабатываются исключительно локально на компьютере пользователя без передачи в сеть Интернет. Проверку сформированных пакетов перед загрузкой в государственные системы осуществляет пользователь / уполномоченный оператор."""

STUDIO_STYLESHEET = """
QMainWindow, QWidget#CentralCanvas {
    background-color: #0D0F13;
    color: #E5E7EB;
    font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif;
    font-size: 13px;
}

QFrame#SurfaceCard {
    background-color: #151821;
    border: 1px solid #242934;
    border-radius: 10px;
}

QFrame#Divider {
    background-color: #232833;
    max-height: 1px;
    min-height: 1px;
    border: none;
}

QLabel#HeaderTitle {
    color: #F3F4F6;
    font-size: 17px;
    font-weight: 600;
}

QLabel#VersionBadge {
    background-color: #1B2436;
    color: #60A5FA;
    border: 1px solid #2A3A57;
    border-radius: 5px;
    padding: 2px 8px;
    font-size: 11px;
    font-weight: 600;
}

QLabel#HeaderSubtitle {
    color: #8B93A6;
    font-size: 12px;
}

QLabel#SectionTitle {
    color: #7C8599;
    font-size: 11px;
    font-weight: 600;
}

QLabel#FieldLabel {
    color: #C7CDD9;
    font-size: 13px;
}

QLabel#MutedText {
    color: #7C8599;
    font-size: 12px;
}

QLineEdit {
    background-color: #0A0C10;
    color: #F3F4F6;
    border: 1px solid #282E3A;
    border-radius: 6px;
    padding: 0px 12px;
    font-size: 13px;
    selection-background-color: #2563EB;
    selection-color: #FFFFFF;
}

QLineEdit:hover {
    border-color: #363E4F;
}

QLineEdit:focus {
    border-color: #3B82F6;
    background-color: #0C0F14;
}

QPushButton {
    background-color: #1C202B;
    color: #E5E7EB;
    border: 1px solid #2D3342;
    border-radius: 6px;
    padding: 0px 16px;
    font-size: 13px;
    font-weight: 500;
}

QPushButton:hover {
    background-color: #242A38;
    border-color: #3E4659;
}

QPushButton:pressed {
    background-color: #171B24;
}

QPushButton:disabled {
    background-color: #14171F;
    color: #555D6E;
    border-color: #202530;
}

QPushButton#SubtleButton {
    background-color: #151821;
    color: #9CA3AF;
    border: 1px solid #272C38;
    padding: 0px 12px;
    font-size: 12px;
}

QPushButton#SubtleButton:hover {
    background-color: #1D222E;
    color: #E5E7EB;
    border-color: #363D4E;
}

QPushButton#PrimaryButton {
    background-color: #2563EB;
    color: #FFFFFF;
    border: 1px solid #3B82F6;
    font-weight: 600;
    padding: 0px 20px;
}

QPushButton#PrimaryButton:hover {
    background-color: #1D4ED8;
    border-color: #60A5FA;
}

QPushButton#PrimaryButton:pressed {
    background-color: #1E40AF;
}

QPushButton#PrimaryButton:disabled {
    background-color: #1C273F;
    color: #64748B;
    border-color: #23314F;
}

QCheckBox {
    color: #E2E6EE;
    spacing: 8px;
    font-size: 13px;
}

QCheckBox::indicator {
    width: 16px;
    height: 16px;
}

QProgressBar {
    background-color: #1E232E;
    border: none;
    border-radius: 3px;
}

QProgressBar::chunk {
    background-color: #3B82F6;
    border-radius: 3px;
}

QTextEdit#ConsoleLog {
    background-color: #090B0E;
    color: #A6B1C4;
    border: 1px solid #202530;
    border-radius: 8px;
    font-family: 'Cascadia Code', 'Consolas', 'Courier New', monospace;
    font-size: 12px;
    padding: 8px 10px;
}
"""


def _get_default_output_dir() -> Path:
    """Returns default output directory next to executable when frozen, or in cwd."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent / "output"
    return Path.cwd() / "output"


def apply_studio_theme(app: QApplication) -> None:
    """Applies Fusion style and dark Antigravity/Codex palette to the application."""
    app.setStyle("Fusion")
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor("#0D0F13"))
    palette.setColor(QPalette.ColorRole.WindowText, QColor("#E5E7EB"))
    palette.setColor(QPalette.ColorRole.Base, QColor("#1C202B"))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#151821"))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor("#151821"))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor("#E5E7EB"))
    palette.setColor(QPalette.ColorRole.Text, QColor("#F3F4F6"))
    palette.setColor(QPalette.ColorRole.Button, QColor("#1C202B"))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor("#E5E7EB"))
    palette.setColor(QPalette.ColorRole.Highlight, QColor("#2563EB"))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#FFFFFF"))
    palette.setColor(QPalette.ColorRole.PlaceholderText, QColor("#646D80"))
    app.setPalette(palette)


def _enable_windows_dark_titlebar(window: QMainWindow) -> None:
    """Requests Windows 10/11 dark titlebar frame via DWM API when available."""
    if sys.platform != "win32":
        return
    try:
        hwnd = int(window.winId())
        value = ctypes.c_int(1)
        dwmapi = ctypes.windll.dwmapi
        # Attribute 20 on Windows 11 / 20H1+, fallback attribute 19 on older Win10 builds
        res = dwmapi.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(value), ctypes.sizeof(value))
        if res != 0:
            dwmapi.DwmSetWindowAttribute(hwnd, 19, ctypes.byref(value), ctypes.sizeof(value))
    except (AttributeError, OSError, ValueError):
        pass


class MainWindow(QMainWindow):
    """Main application window for EGISSO -> ECP migration tool."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("EGISSO → ГИС ЕЦП (ЛК РСМСЗ)")
        self.resize(840, 720)
        self.setMinimumSize(700, 600)
        self.setStyleSheet(STUDIO_STYLESHEET)

        self.worker: ConversionWorker | None = None
        self._init_ui()
        _enable_windows_dark_titlebar(self)

    def _init_ui(self) -> None:
        central_widget = QWidget()
        central_widget.setObjectName("CentralCanvas")
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 18, 20, 18)
        main_layout.setSpacing(14)

        # 1. Top Header Bar
        header_row = QHBoxLayout()
        header_row.setSpacing(10)

        title_block = QVBoxLayout()
        title_block.setSpacing(4)

        title_line = QHBoxLayout()
        title_line.setSpacing(10)
        title_label = QLabel("EGISSO → ГИС ЕЦП")
        title_label.setObjectName("HeaderTitle")
        title_label.setFont(QFont("Segoe UI", 16, QFont.Weight.DemiBold))
        title_line.addWidget(title_label)

        version_badge = QLabel(f"v{APP_VERSION}")
        version_badge.setObjectName("VersionBadge")
        title_line.addWidget(version_badge)
        title_line.addStretch()

        subtitle_label = QLabel(
            "Конвертация исторических сведений о решениях ЛК РСМСЗ · 107 столбцов · ФЛК · UTF-8 BOM / XLSX"
        )
        subtitle_label.setObjectName("HeaderSubtitle")

        title_block.addLayout(title_line)
        title_block.addWidget(subtitle_label)
        header_row.addLayout(title_block, stretch=1)

        btn_about = QPushButton("О программе и лицензии")
        btn_about.setObjectName("SubtleButton")
        btn_about.setFixedHeight(32)
        btn_about.clicked.connect(self._show_license_dialog)
        header_row.addWidget(btn_about, alignment=Qt.AlignmentFlag.AlignVCenter)

        main_layout.addLayout(header_row)

        # 2. Card 1: Data Paths
        paths_card = QFrame()
        paths_card.setObjectName("SurfaceCard")
        paths_layout = QGridLayout(paths_card)
        paths_layout.setContentsMargins(16, 14, 16, 16)
        paths_layout.setHorizontalSpacing(12)
        paths_layout.setVerticalSpacing(10)

        lbl_paths_title = QLabel("МАРШРУТЫ ДАННЫХ")
        lbl_paths_title.setObjectName("SectionTitle")
        paths_layout.addWidget(lbl_paths_title, 0, 0, 1, 3)

        lbl_in = QLabel("Исходная папка:")
        lbl_in.setObjectName("FieldLabel")
        paths_layout.addWidget(lbl_in, 1, 0)

        self.txt_input = QLineEdit()
        self.txt_input.setFixedHeight(36)
        self.txt_input.setPlaceholderText("Выберите каталог с реестрами ЕГИССО (.xlsx)")
        paths_layout.addWidget(self.txt_input, 1, 1)

        btn_browse_input = QPushButton("Обзор…")
        btn_browse_input.setFixedHeight(36)
        btn_browse_input.setMinimumWidth(96)
        btn_browse_input.clicked.connect(self._browse_input)
        paths_layout.addWidget(btn_browse_input, 1, 2)

        lbl_out = QLabel("Папка выгрузки:")
        lbl_out.setObjectName("FieldLabel")
        paths_layout.addWidget(lbl_out, 2, 0)

        self.txt_output = QLineEdit()
        self.txt_output.setFixedHeight(36)
        self.txt_output.setPlaceholderText("Выберите каталог для готовых пакетов")
        self.txt_output.setText(str(_get_default_output_dir()))
        paths_layout.addWidget(self.txt_output, 2, 1)

        btn_browse_output = QPushButton("Обзор…")
        btn_browse_output.setFixedHeight(36)
        btn_browse_output.setMinimumWidth(96)
        btn_browse_output.clicked.connect(self._browse_output)
        paths_layout.addWidget(btn_browse_output, 2, 2)

        paths_layout.setColumnStretch(1, 1)
        main_layout.addWidget(paths_card)

        # 3. Card 2: Conversion Parameters
        options_card = QFrame()
        options_card.setObjectName("SurfaceCard")
        options_outer = QVBoxLayout(options_card)
        options_outer.setContentsMargins(16, 14, 16, 16)
        options_outer.setSpacing(12)

        lbl_opts_title = QLabel("ПАРАМЕТРЫ КОНВЕРТАЦИИ")
        lbl_opts_title.setObjectName("SectionTitle")
        options_outer.addWidget(lbl_opts_title)

        checks_grid = QGridLayout()
        checks_grid.setHorizontalSpacing(24)
        checks_grid.setVerticalSpacing(10)

        self.cb_recursive = QCheckBox("Рекурсивный поиск в подпапках")
        self.cb_recursive.setChecked(True)
        self.cb_recursive.setToolTip("Сканировать все вложенные каталоги и извлекать месяц/год из путей")
        checks_grid.addWidget(self.cb_recursive, 0, 0)

        self.cb_split_months = QCheckBox("Разбивать пакеты по месяцам (2023–2026)")
        self.cb_split_months.setChecked(True)
        self.cb_split_months.setToolTip("Объединять все меры за один календарный месяц в помесячный пакет")
        checks_grid.addWidget(self.cb_split_months, 0, 1)

        self.cb_format_csv = QCheckBox("Формат CSV (стандарт ГИС ЕЦП)")
        self.cb_format_csv.setChecked(True)
        self.cb_format_csv.setToolTip("Сохранять пакеты CSV в отдельную папку /csv/")
        checks_grid.addWidget(self.cb_format_csv, 1, 0)

        self.cb_format_xlsx = QCheckBox("Формат Excel (.xlsx)")
        self.cb_format_xlsx.setChecked(False)
        self.cb_format_xlsx.setToolTip("Сохранять пакеты XLSX в отдельную папку /xlsx/")
        checks_grid.addWidget(self.cb_format_xlsx, 1, 1)

        options_outer.addLayout(checks_grid)

        divider = QFrame()
        divider.setObjectName("Divider")
        divider.setFrameShape(QFrame.Shape.HLine)
        options_outer.addWidget(divider)

        provider_row = QHBoxLayout()
        provider_row.setSpacing(12)
        lbl_provider = QLabel("Код поставщика (ПоставщикИнформации):")
        lbl_provider.setObjectName("FieldLabel")
        provider_row.addWidget(lbl_provider)

        self.txt_provider = QLineEdit("430746")
        self.txt_provider.setFixedHeight(36)
        self.txt_provider.setFixedWidth(180)
        self.txt_provider.setToolTip("Числовой код поставщика информации из реестра ГИС ЕЦП")
        provider_row.addWidget(self.txt_provider)
        provider_row.addStretch()

        options_outer.addLayout(provider_row)
        main_layout.addWidget(options_card)

        # 4. Card 3: Execution Log Console
        log_card = QFrame()
        log_card.setObjectName("SurfaceCard")
        log_layout = QVBoxLayout(log_card)
        log_layout.setContentsMargins(16, 14, 16, 16)
        log_layout.setSpacing(10)

        log_header = QHBoxLayout()
        lbl_log_title = QLabel("ЖУРНАЛ ВЫПОЛНЕНИЯ")
        lbl_log_title.setObjectName("SectionTitle")
        log_header.addWidget(lbl_log_title)
        log_header.addStretch()

        self.lbl_status = QLabel("Готов к работе")
        self.lbl_status.setObjectName("MutedText")
        log_header.addWidget(self.lbl_status)
        log_layout.addLayout(log_header)

        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setValue(0)
        log_layout.addWidget(self.progress_bar)

        self.txt_log = QTextEdit()
        self.txt_log.setObjectName("ConsoleLog")
        self.txt_log.setReadOnly(True)
        self.txt_log.setPlaceholderText("Ожидание запуска конвертации…")
        log_layout.addWidget(self.txt_log, stretch=1)

        main_layout.addWidget(log_card, stretch=1)

        # 5. Bottom Action Bar
        bottom_bar = QHBoxLayout()
        bottom_bar.setSpacing(10)

        lbl_footer = QLabel("MIT License · Локальная обработка (данные не передаются в сеть)")
        lbl_footer.setObjectName("MutedText")
        bottom_bar.addWidget(lbl_footer, stretch=1)

        self.btn_open_folder = QPushButton("Открыть папку выгрузки")
        self.btn_open_folder.setFixedHeight(38)
        self.btn_open_folder.setEnabled(False)
        self.btn_open_folder.clicked.connect(self._open_output_folder)
        bottom_bar.addWidget(self.btn_open_folder)

        self.btn_start = QPushButton("Запустить конвертацию")
        self.btn_start.setObjectName("PrimaryButton")
        self.btn_start.setFixedHeight(38)
        self.btn_start.clicked.connect(self._start_conversion)
        bottom_bar.addWidget(self.btn_start)

        main_layout.addLayout(bottom_bar)

    def _show_license_dialog(self) -> None:
        QMessageBox.information(self, "О программе и лицензии (MIT)", LICENSE_AND_DISCLAIMER_TEXT)

    def _browse_input(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Выберите папку с файлами ЕГИССО")
        if folder:
            self.txt_input.setText(folder)

    def _browse_output(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Выберите папку для сохранения результатов")
        if folder:
            self.txt_output.setText(folder)

    def _open_output_folder(self) -> None:
        out_dir = self.txt_output.text().strip()
        if out_dir and Path(out_dir).exists():
            os.startfile(out_dir)

    def _start_conversion(self) -> None:
        input_dir_str = self.txt_input.text().strip()
        output_dir_str = self.txt_output.text().strip()

        if not input_dir_str or not Path(input_dir_str).exists():
            QMessageBox.warning(self, "Ошибка ввода", "Укажите существующую исходную папку с файлами.")
            return

        if not output_dir_str:
            QMessageBox.warning(self, "Ошибка ввода", "Укажите папку для сохранения результатов.")
            return

        if not self.cb_format_csv.isChecked() and not self.cb_format_xlsx.isChecked():
            QMessageBox.warning(self, "Ошибка выбора формата", "Выберите хотя бы один формат выгрузки (CSV или Excel).")
            return

        config = ConversionConfig(
            input_path=Path(input_dir_str),
            output_dir=Path(output_dir_str),
            recursive_search=self.cb_recursive.isChecked(),
            split_by_months=self.cb_split_months.isChecked(),
            export_csv=self.cb_format_csv.isChecked(),
            export_xlsx=self.cb_format_xlsx.isChecked(),
            provider_code=self.txt_provider.text().strip() or "430746",
        )

        self.btn_start.setEnabled(False)
        self.btn_open_folder.setEnabled(False)
        self.progress_bar.setValue(0)
        self.txt_log.clear()

        self.worker = ConversionWorker(config)
        self.worker.progress_changed.connect(self._on_worker_progress)
        self.worker.log_received.connect(self._on_worker_log)
        self.worker.completed.connect(self._on_worker_completed)
        self.worker.failed.connect(self._on_worker_failed)
        self.worker.start()

    def _on_worker_progress(self, current: int, total: int, status: str) -> None:
        pct = int((current / max(total, 1)) * 100)
        self.progress_bar.setValue(pct)
        self.lbl_status.setText(status)

    def _on_worker_log(self, message: str) -> None:
        self.txt_log.append(message)

    def _on_worker_completed(self, summary: ConversionSummary) -> None:
        self.btn_start.setEnabled(True)
        self.btn_open_folder.setEnabled(True)
        self.progress_bar.setValue(100)
        self.lbl_status.setText("Конвертация завершена")

        msg = (
            f"Обработка завершена!\n\n"
            f"• Файлов обработано: {summary.scanned_files_count}\n"
            f"• Прочитано записей: {summary.parsed_records_count}\n"
            f"• Валидных решений: {summary.valid_decisions_count}\n"
            f"• Сформировано пакетов: {summary.packages_generated_count}\n"
            f"• Файлов CSV: {len(summary.csv_files_written)}\n"
            f"• Файлов XLSX: {len(summary.xlsx_files_written)}\n"
        )
        if summary.error_report_path:
            msg += f"\nЗамечания ФЛК сохранены в:\n{summary.error_report_path.name}"

        QMessageBox.information(self, "Готово", msg)

    def _on_worker_failed(self, error_message: str) -> None:
        self.btn_start.setEnabled(True)
        self.btn_open_folder.setEnabled(True)
        self.lbl_status.setText("Ошибка выполнения")
        QMessageBox.critical(self, "Ошибка выполнения", f"Произошла ошибка:\n{error_message}")

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        """Prevents window destruction while background worker thread is running."""
        if self.worker is not None and self.worker.isRunning():
            QMessageBox.warning(
                self,
                "Обработка не завершена",
                "Дождитесь завершения текущей конвертации перед закрытием окна.",
            )
            event.ignore()
            return
        event.accept()


def run_gui() -> None:
    """Entry point for GUI application."""
    if "--version" in sys.argv:
        print(f"egisso-to-ecp {APP_VERSION}")
        return
    app = QApplication.instance()
    if not isinstance(app, QApplication):
        app = QApplication(sys.argv)
    apply_studio_theme(app)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    run_gui()
