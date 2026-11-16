"""Modern Windows 11 styled Desktop GUI for egisso-to-ecp."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
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

WIN11_STYLESHEET = """
QMainWindow {
    background-color: #F3F3F3;
    font-family: 'Segoe UI', sans-serif;
}

QWidget {
    font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
    font-size: 13px;
    color: #1F1F1F;
}

QGroupBox {
    font-weight: 600;
    border: 1px solid #E0E0E0;
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 18px;
    background-color: #FFFFFF;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    padding: 0 4px;
    color: #0067C0;
}

QLineEdit {
    background-color: #FFFFFF;
    border: 1px solid #D1D1D1;
    border-bottom: 2px solid #0067C0;
    border-radius: 4px;
    padding: 6px 10px;
    font-size: 13px;
    selection-background-color: #0067C0;
}

QLineEdit:focus {
    border: 1px solid #0067C0;
    border-bottom: 2px solid #0067C0;
    background-color: #FBFCFD;
}

QPushButton {
    background-color: #FDFDFD;
    border: 1px solid #CECECE;
    border-radius: 5px;
    padding: 7px 16px;
    font-weight: 500;
    font-size: 13px;
}

QPushButton:hover {
    background-color: #F6F6F6;
    border-color: #BCBCBC;
}

QPushButton:pressed {
    background-color: #EDEDED;
}

QPushButton#PrimaryButton {
    background-color: #0067C0;
    color: #FFFFFF;
    border: 1px solid #005A9E;
    font-weight: 600;
    font-size: 14px;
    padding: 10px 24px;
    border-radius: 6px;
}

QPushButton#PrimaryButton:hover {
    background-color: #1975C5;
}

QPushButton#PrimaryButton:pressed {
    background-color: #005A9E;
}

QPushButton#PrimaryButton:disabled {
    background-color: #CCCCCC;
    border-color: #BDBDBD;
    color: #888888;
}

QCheckBox {
    spacing: 8px;
    font-size: 13px;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 1px solid #8A8A8A;
    background-color: #FFFFFF;
}

QCheckBox::indicator:hover {
    border-color: #0067C0;
}

QCheckBox::indicator:checked {
    background-color: #0067C0;
    border-color: #0067C0;
    image: url("");
}

QProgressBar {
    border: 1px solid #D5D5D5;
    border-radius: 5px;
    text-align: center;
    background-color: #E6E6E6;
    height: 14px;
    font-size: 11px;
}

QProgressBar::chunk {
    background-color: #0067C0;
    border-radius: 4px;
}

QTextEdit {
    background-color: #FFFFFF;
    border: 1px solid #E0E0E0;
    border-radius: 6px;
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: 12px;
    padding: 6px;
}
"""


class MainWindow(QMainWindow):
    """Main application window for EGISSO -> ECP migration tool."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Миграция данных ЕГИССО -> ГИС ЕЦП (ЛК РСМСЗ)")
        self.resize(780, 720)
        self.setMinimumSize(640, 580)
        self.setStyleSheet(WIN11_STYLESHEET)

        self.worker: ConversionWorker | None = None
        self._init_ui()

    def _init_ui(self) -> None:
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(14)

        # 1. Header Card
        header_frame = QFrame()
        header_frame.setStyleSheet("background-color: #FFFFFF; border-radius: 8px; border: 1px solid #E0E0E0; padding: 12px;")
        header_layout = QVBoxLayout(header_frame)
        title_label = QLabel("Конвертер исторических данных ЕГИССО в ГИС ЕЦП")
        title_font = QFont("Segoe UI", 16, QFont.Weight.Bold)
        title_label.setFont(title_font)
        title_label.setStyleSheet("color: #0067C0; border: none;")

        subtitle_label = QLabel(
            "Формирование пакетов сведений о решениях (107 столбцов, ФЛК, кодировки UTF-8-BOM / XLSX)"
        )
        subtitle_label.setStyleSheet("color: #616161; border: none; font-size: 12px;")
        header_layout.addWidget(title_label)
        header_layout.addWidget(subtitle_label)
        main_layout.addWidget(header_frame)

        # 2. File Selection Group
        files_group = QGroupBox("Каталоги и файлы")
        files_layout = QGridLayout(files_group)
        files_layout.setContentsMargins(16, 20, 16, 16)
        files_layout.setSpacing(10)

        # Input path
        files_layout.addWidget(QLabel("Исходная папка:"), 0, 0)
        self.txt_input = QLineEdit()
        self.txt_input.setPlaceholderText("Выберите папку с файлами ЕГИССО (.xlsx)")
        files_layout.addWidget(self.txt_input, 0, 1)
        btn_browse_input = QPushButton("Обзор...")
        btn_browse_input.clicked.connect(self._browse_input)
        files_layout.addWidget(btn_browse_input, 0, 2)

        # Output path
        files_layout.addWidget(QLabel("Папка сохранения:"), 1, 0)
        self.txt_output = QLineEdit()
        self.txt_output.setPlaceholderText("Выберите папку для сохранения готовых пакетов")
        default_out = str(Path.cwd() / "output")
        self.txt_output.setText(default_out)
        files_layout.addWidget(self.txt_output, 1, 1)
        btn_browse_output = QPushButton("Обзор...")
        btn_browse_output.clicked.connect(self._browse_output)
        files_layout.addWidget(btn_browse_output, 1, 2)

        main_layout.addWidget(files_group)

        # 3. Parameters Group (Checkboxes requested by user)
        options_group = QGroupBox("Параметры конвертации")
        options_layout = QGridLayout(options_group)
        options_layout.setContentsMargins(16, 20, 16, 16)
        options_layout.setSpacing(10)

        # Checkbox 1: Recursive Search (Default: ON)
        self.cb_recursive = QCheckBox("Рекурсивный поиск в подпапках")
        self.cb_recursive.setChecked(True)
        self.cb_recursive.setToolTip("Искать файлы Excel во всех вложенных подкаталогах")
        options_layout.addWidget(self.cb_recursive, 0, 0)

        # Checkbox 2: Split by Months (Default: ON)
        self.cb_split_months = QCheckBox("Разбивать по месяцам (отдельный пакет на каждый месяц)")
        self.cb_split_months.setChecked(True)
        self.cb_split_months.setToolTip("Группировать решения по календарным месяцам (2023 - 2026)")
        options_layout.addWidget(self.cb_split_months, 0, 1)

        # Checkbox 3: CSV format (Default: ON)
        self.cb_format_csv = QCheckBox("Выгружать в формате CSV (ГИС ЕЦП)")
        self.cb_format_csv.setChecked(True)
        self.cb_format_csv.setToolTip("Сохранять пакеты CSV в отдельную папку /csv/")
        options_layout.addWidget(self.cb_format_csv, 1, 0)

        # Checkbox 4: Excel format (Default: OFF)
        self.cb_format_xlsx = QCheckBox("Выгружать в формате Excel (.xlsx)")
        self.cb_format_xlsx.setChecked(False)
        self.cb_format_xlsx.setToolTip("Сохранять пакеты XLSX в отдельную папку /xlsx/")
        options_layout.addWidget(self.cb_format_xlsx, 1, 1)

        # Provider Code
        options_layout.addWidget(QLabel("Код поставщика (ПоставщикИнформации):"), 2, 0)
        self.txt_provider = QLineEdit("PFR001")
        self.txt_provider.setToolTip("Идентификатор поставщика информации из реестра РУВ")
        options_layout.addWidget(self.txt_provider, 2, 1)

        main_layout.addWidget(options_group)

        # 4. Action Button & Progress
        action_layout = QHBoxLayout()
        self.btn_start = QPushButton("Начать конвертацию")
        self.btn_start.setObjectName("PrimaryButton")
        self.btn_start.clicked.connect(self._start_conversion)
        action_layout.addWidget(self.btn_start)

        self.btn_open_folder = QPushButton("Открыть папку с результатами")
        self.btn_open_folder.clicked.connect(self._open_output_folder)
        self.btn_open_folder.setEnabled(False)
        action_layout.addWidget(self.btn_open_folder)

        main_layout.addLayout(action_layout)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        main_layout.addWidget(self.progress_bar)

        self.lbl_status = QLabel("Готов к работе")
        self.lbl_status.setStyleSheet("color: #616161; font-style: italic;")
        main_layout.addWidget(self.lbl_status)

        # 5. Live Log Area
        main_layout.addWidget(QLabel("Журнал операций:"))
        self.txt_log = QTextEdit()
        self.txt_log.setReadOnly(True)
        main_layout.addWidget(self.txt_log, stretch=1)

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
            provider_code=self.txt_provider.text().strip() or "PFR001",
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
        self.lbl_status.setText("Конвертация успешно завершена!")

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

        QMessageBox.information(self, "Успех", msg)

    def _on_worker_failed(self, error_message: str) -> None:
        self.btn_start.setEnabled(True)
        self.btn_open_folder.setEnabled(True)
        self.lbl_status.setText("Произошла ошибка при выполнении")
        QMessageBox.critical(self, "Ошибка выполнения", f"Произошла ошибка:\n{error_message}")


def run_gui() -> None:
    """Entry point for GUI application."""
    app = QApplication.instance() or QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    run_gui()
