"""Antigravity / Codex inspired Desktop GUI for egisso-to-ecp."""

from __future__ import annotations

import ctypes
import os
import sys
from pathlib import Path
from string import Template

from PySide6.QtCore import QSettings, Qt
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
from egisso_to_ecp.presentation.gui.icon import create_app_icon
from egisso_to_ecp.presentation.gui.worker import ConversionWorker

APP_VERSION = "0.1.1"

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

THEME_TOKENS: dict[str, dict[str, str]] = {
    "dark": {
        "bg_canvas": "#0D0F13",
        "text_primary": "#E5E7EB",
        "text_strong": "#F3F4F6",
        "text_field_label": "#C7CDD9",
        "text_muted": "#7C8599",
        "text_subtitle": "#8B93A6",
        "bg_card": "#151821",
        "border_card": "#242934",
        "divider": "#232833",
        "badge_bg": "#1B2436",
        "badge_text": "#60A5FA",
        "badge_border": "#2A3A57",
        "input_bg": "#0A0C10",
        "input_focus_bg": "#0C0F14",
        "input_border": "#282E3A",
        "input_hover_border": "#363E4F",
        "input_focus_border": "#3B82F6",
        "btn_bg": "#1C202B",
        "btn_hover_bg": "#242A38",
        "btn_pressed_bg": "#171B24",
        "btn_border": "#2D3342",
        "btn_hover_border": "#3E4659",
        "btn_disabled_bg": "#14171F",
        "btn_disabled_text": "#555D6E",
        "btn_disabled_border": "#202530",
        "subtle_bg": "#151821",
        "subtle_text": "#9CA3AF",
        "subtle_border": "#272C38",
        "subtle_hover_bg": "#1D222E",
        "subtle_hover_border": "#363D4E",
        "primary_bg": "#2563EB",
        "primary_hover_bg": "#1D4ED8",
        "primary_pressed_bg": "#1E40AF",
        "primary_border": "#3B82F6",
        "primary_disabled_bg": "#1C273F",
        "primary_disabled_text": "#64748B",
        "primary_disabled_border": "#23314F",
        "cb_text": "#E2E6EE",
        "cb_unchecked_bg": "#1C202B",
        "cb_unchecked_border": "#3A4252",
        "pb_track": "#1E232E",
        "pb_chunk": "#3B82F6",
        "console_bg": "#090B0E",
        "console_text": "#A6B1C4",
        "console_border": "#202530",
        "qpal_base": "#1C202B",
        "qpal_placeholder": "#646D80",
    },
    "light": {
        "bg_canvas": "#F6F8FA",
        "text_primary": "#1E293B",
        "text_strong": "#0F172A",
        "text_field_label": "#334155",
        "text_muted": "#64748B",
        "text_subtitle": "#64748B",
        "bg_card": "#FFFFFF",
        "border_card": "#E2E6EE",
        "divider": "#E6E9F0",
        "badge_bg": "#EFF6FF",
        "badge_text": "#2563EB",
        "badge_border": "#BFDBFE",
        "input_bg": "#FFFFFF",
        "input_focus_bg": "#FFFFFF",
        "input_border": "#CBD5E1",
        "input_hover_border": "#94A3B8",
        "input_focus_border": "#2563EB",
        "btn_bg": "#FFFFFF",
        "btn_hover_bg": "#F8FAFC",
        "btn_pressed_bg": "#EEF2F7",
        "btn_border": "#CBD5E1",
        "btn_hover_border": "#94A3B8",
        "btn_disabled_bg": "#F8FAFC",
        "btn_disabled_text": "#94A3B8",
        "btn_disabled_border": "#E2E8F0",
        "subtle_bg": "#FFFFFF",
        "subtle_text": "#475569",
        "subtle_border": "#DCE2EC",
        "subtle_hover_bg": "#F1F5F9",
        "subtle_hover_border": "#CBD5E1",
        "primary_bg": "#2563EB",
        "primary_hover_bg": "#1D4ED8",
        "primary_pressed_bg": "#1E40AF",
        "primary_border": "#1D4ED8",
        "primary_disabled_bg": "#CBD5E1",
        "primary_disabled_text": "#FFFFFF",
        "primary_disabled_border": "#CBD5E1",
        "cb_text": "#1E293B",
        "cb_unchecked_bg": "#FFFFFF",
        "cb_unchecked_border": "#94A3B8",
        "pb_track": "#E2E8F0",
        "pb_chunk": "#2563EB",
        "console_bg": "#F8FAFC",
        "console_text": "#1E293B",
        "console_border": "#E2E8F0",
        "qpal_base": "#FFFFFF",
        "qpal_placeholder": "#94A3B8",
    },
}

_STUDIO_QSS_TEMPLATE = Template("""
QMainWindow, QWidget#CentralCanvas {
    background-color: $bg_canvas;
    color: $text_primary;
    font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif;
    font-size: 13px;
}

QFrame#SurfaceCard {
    background-color: $bg_card;
    border: 1px solid $border_card;
    border-radius: 10px;
}

QFrame#Divider {
    background-color: $divider;
    max-height: 1px;
    min-height: 1px;
    border: none;
}

QLabel#HeaderTitle {
    color: $text_strong;
    font-size: 17px;
    font-weight: 600;
}

QLabel#VersionBadge {
    background-color: $badge_bg;
    color: $badge_text;
    border: 1px solid $badge_border;
    border-radius: 5px;
    padding: 2px 8px;
    font-size: 11px;
    font-weight: 600;
}

QLabel#HeaderSubtitle {
    color: $text_subtitle;
    font-size: 12px;
}

QLabel#SectionTitle {
    color: $text_muted;
    font-size: 11px;
    font-weight: 600;
}

QLabel#FieldLabel {
    color: $text_field_label;
    font-size: 13px;
}

QLabel#MutedText {
    color: $text_muted;
    font-size: 12px;
}

QLineEdit {
    background-color: $input_bg;
    color: $text_strong;
    border: 1px solid $input_border;
    border-radius: 6px;
    padding: 0px 12px;
    font-size: 13px;
    selection-background-color: #2563EB;
    selection-color: #FFFFFF;
}

QLineEdit:hover {
    border-color: $input_hover_border;
}

QLineEdit:focus {
    border-color: $input_focus_border;
    background-color: $input_focus_bg;
}

QPushButton {
    background-color: $btn_bg;
    color: $text_primary;
    border: 1px solid $btn_border;
    border-radius: 6px;
    padding: 0px 16px;
    font-size: 13px;
    font-weight: 500;
}

QPushButton:hover {
    background-color: $btn_hover_bg;
    border-color: $btn_hover_border;
}

QPushButton:pressed {
    background-color: $btn_pressed_bg;
}

QPushButton:disabled {
    background-color: $btn_disabled_bg;
    color: $btn_disabled_text;
    border-color: $btn_disabled_border;
}

QPushButton#SubtleButton {
    background-color: $subtle_bg;
    color: $subtle_text;
    border: 1px solid $subtle_border;
    padding: 0px 12px;
    font-size: 12px;
}

QPushButton#SubtleButton:hover {
    background-color: $subtle_hover_bg;
    color: $text_strong;
    border-color: $subtle_hover_border;
}

QPushButton#PrimaryButton {
    background-color: $primary_bg;
    color: #FFFFFF;
    border: 1px solid $primary_border;
    font-weight: 600;
    padding: 0px 20px;
}

QPushButton#PrimaryButton:hover {
    background-color: $primary_hover_bg;
    border-color: #60A5FA;
}

QPushButton#PrimaryButton:pressed {
    background-color: $primary_pressed_bg;
}

QPushButton#PrimaryButton:disabled {
    background-color: $primary_disabled_bg;
    color: $primary_disabled_text;
    border-color: $primary_disabled_border;
}

QCheckBox {
    color: $cb_text;
    spacing: 8px;
    font-size: 13px;
}

QCheckBox::indicator {
    width: 16px;
    height: 16px;
}

QCheckBox::indicator:unchecked {
    background-color: $cb_unchecked_bg;
    border: 1px solid $cb_unchecked_border;
    border-radius: 3px;
}

QProgressBar {
    background-color: $pb_track;
    border: none;
    border-radius: 3px;
}

QProgressBar::chunk {
    background-color: $pb_chunk;
    border-radius: 3px;
}

QTextEdit#ConsoleLog {
    background-color: $console_bg;
    color: $console_text;
    border: 1px solid $console_border;
    border-radius: 8px;
    font-family: 'Cascadia Code', 'Consolas', 'Courier New', monospace;
    font-size: 12px;
    padding: 8px 10px;
}
""")


def build_studio_stylesheet(theme: str) -> str:
    """Builds the studio stylesheet for the requested theme ('dark' or 'light')."""
    tokens = THEME_TOKENS["light" if theme == "light" else "dark"]
    return _STUDIO_QSS_TEMPLATE.substitute(tokens)


def _get_default_output_dir() -> Path:
    """Returns default output directory next to executable when frozen, or in cwd."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent / "output"
    return Path.cwd() / "output"


def apply_studio_theme(app: QApplication, theme: str = "dark") -> None:
    """Applies Fusion style and dark/light Antigravity/Codex palette to the application."""
    tokens = THEME_TOKENS["light" if theme == "light" else "dark"]
    app.setStyle("Fusion")
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(tokens["bg_canvas"]))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(tokens["text_primary"]))
    palette.setColor(QPalette.ColorRole.Base, QColor(tokens["qpal_base"]))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(tokens["bg_card"]))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(tokens["bg_card"]))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor(tokens["text_primary"]))
    palette.setColor(QPalette.ColorRole.Text, QColor(tokens["text_strong"]))
    palette.setColor(QPalette.ColorRole.Button, QColor(tokens["btn_bg"]))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(tokens["text_primary"]))
    palette.setColor(QPalette.ColorRole.Highlight, QColor("#2563EB"))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#FFFFFF"))
    palette.setColor(QPalette.ColorRole.PlaceholderText, QColor(tokens["qpal_placeholder"]))
    if theme == "light":
        palette.setColor(QPalette.ColorRole.Mid, QColor("#94A3B8"))
        palette.setColor(QPalette.ColorRole.Dark, QColor("#64748B"))
        palette.setColor(QPalette.ColorRole.Light, QColor("#FFFFFF"))
    else:
        palette.setColor(QPalette.ColorRole.Mid, QColor("#3A4252"))
        palette.setColor(QPalette.ColorRole.Dark, QColor("#2D3342"))
        palette.setColor(QPalette.ColorRole.Light, QColor("#242934"))
    app.setPalette(palette)


def _set_windows_titlebar_dark(window: QMainWindow, is_dark: bool) -> None:
    """Requests Windows 10/11 dark or light titlebar frame via DWM API when available."""
    if sys.platform != "win32":
        return
    try:
        hwnd = int(window.winId())
        value = ctypes.c_int(1 if is_dark else 0)
        dwmapi = ctypes.windll.dwmapi
        res = dwmapi.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(value), ctypes.sizeof(value))
        if res != 0:
            dwmapi.DwmSetWindowAttribute(hwnd, 19, ctypes.byref(value), ctypes.sizeof(value))
    except (AttributeError, OSError, ValueError):
        pass


class MainWindow(QMainWindow):
    """Main application window for EGISSO -> ECP migration tool."""

    def __init__(self, initial_theme: str | None = None) -> None:
        super().__init__()
        self.setWindowTitle("EGISSO → ГИС ЕЦП (ЛК РСМСЗ)")
        self.setWindowIcon(create_app_icon())
        self.resize(880, 840)
        self.setMinimumSize(780, 680)

        self.settings = QSettings("egisso-to-ecp", "EGISSO_to_ECP")
        saved_theme = initial_theme or str(self.settings.value("ui/theme", "dark"))
        self.current_theme = "light" if saved_theme == "light" else "dark"

        self.worker: ConversionWorker | None = None
        self._init_ui()
        self.apply_theme(self.current_theme)

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
            "Пакеты сведений ЛК РСМСЗ · 107 столбцов · ФЛК · UTF-8 BOM"
        )
        subtitle_label.setObjectName("HeaderSubtitle")

        title_block.addLayout(title_line)
        title_block.addWidget(subtitle_label)
        header_row.addLayout(title_block, stretch=1)

        self.btn_theme = QPushButton("☀ Светлая тема")
        self.btn_theme.setObjectName("SubtleButton")
        self.btn_theme.setFixedHeight(32)
        self.btn_theme.clicked.connect(self._toggle_theme)
        header_row.addWidget(self.btn_theme, alignment=Qt.AlignmentFlag.AlignVCenter)

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
        main_layout.addWidget(options_card)

        # 4. Card 3: Organization Requisites & ECP Measure Codes
        org_card = QFrame()
        org_card.setObjectName("SurfaceCard")
        org_outer = QVBoxLayout(org_card)
        org_outer.setContentsMargins(16, 14, 16, 16)
        org_outer.setSpacing(10)

        lbl_org_title = QLabel("РЕКВИЗИТЫ ОРГАНИЗАЦИИ И МЕРЫ В ГИС ЕЦП")
        lbl_org_title.setObjectName("SectionTitle")
        org_outer.addWidget(lbl_org_title)

        org_grid = QGridLayout()
        org_grid.setHorizontalSpacing(16)
        org_grid.setVerticalSpacing(8)

        # Left Column: Organization
        lbl_prov = QLabel("Поставщик информации:")
        lbl_prov.setObjectName("FieldLabel")
        saved_provider = str(self.settings.value("ui/provider_code", "1788"))
        self.txt_provider = QLineEdit(saved_provider)
        self.txt_provider.setFixedHeight(34)
        self.txt_provider.setPlaceholderText("ID поставщика в ЕЦП (напр. 1788)")
        self.txt_provider.setToolTip("Идентификатор поставщика информации из реестра участников взаимодействия ЕЦП")
        org_grid.addWidget(lbl_prov, 0, 0)
        org_grid.addWidget(self.txt_provider, 0, 1)

        lbl_inn = QLabel("ИНН организации:")
        lbl_inn.setObjectName("FieldLabel")
        saved_inn = str(self.settings.value("ui/onmsz_inn", ""))
        self.txt_inn = QLineEdit(saved_inn)
        self.txt_inn.setFixedHeight(34)
        self.txt_inn.setPlaceholderText("10 цифр (напр. 3307010131)")
        self.txt_inn.setToolTip("ИНН органа или учреждения, назначающего меру (ОНМСЗ)")
        org_grid.addWidget(lbl_inn, 1, 0)
        org_grid.addWidget(self.txt_inn, 1, 1)

        lbl_kpp = QLabel("КПП организации:")
        lbl_kpp.setObjectName("FieldLabel")
        saved_kpp = str(self.settings.value("ui/onmsz_kpp", ""))
        self.txt_kpp = QLineEdit(saved_kpp)
        self.txt_kpp.setFixedHeight(34)
        self.txt_kpp.setPlaceholderText("9 цифр (напр. 333401001)")
        self.txt_kpp.setToolTip("КПП органа или учреждения, назначающего меру (ОНМСЗ)")
        org_grid.addWidget(lbl_kpp, 2, 0)
        org_grid.addWidget(self.txt_kpp, 2, 1)

        lbl_ogrn = QLabel("ОГРН организации:")
        lbl_ogrn.setObjectName("FieldLabel")
        saved_ogrn = str(self.settings.value("ui/onmsz_ogrn", ""))
        self.txt_ogrn = QLineEdit(saved_ogrn)
        self.txt_ogrn.setFixedHeight(34)
        self.txt_ogrn.setPlaceholderText("13 цифр (напр. 1023302154226)")
        self.txt_ogrn.setToolTip("ОГРН органа или учреждения, назначающего меру (ОНМСЗ)")
        org_grid.addWidget(lbl_ogrn, 3, 0)
        org_grid.addWidget(self.txt_ogrn, 3, 1)

        # Right Column: Measure codes & Parameters
        lbl_tmsz = QLabel("Код типовой меры (ТМСЗ):")
        lbl_tmsz.setObjectName("FieldLabel")
        saved_tmsz = str(self.settings.value("ui/code_tmsz", "220119"))
        self.txt_tmsz = QLineEdit(saved_tmsz)
        self.txt_tmsz.setFixedHeight(34)
        self.txt_tmsz.setPlaceholderText("Код ТМСЗ (напр. 220119)")
        self.txt_tmsz.setToolTip("Код типовой меры по федеральному классификатору ЕЦП")
        org_grid.addWidget(lbl_tmsz, 0, 2)
        org_grid.addWidget(self.txt_tmsz, 0, 3)

        lbl_lmsz = QLabel("Код локальной меры (ЛМСЗ):")
        lbl_lmsz.setObjectName("FieldLabel")
        saved_lmsz = str(self.settings.value("ui/code_lmsz", ""))
        self.txt_lmsz = QLineEdit(saved_lmsz)
        self.txt_lmsz.setFixedHeight(34)
        self.txt_lmsz.setPlaceholderText("Числовой код (напр. 3200133300153)")
        self.txt_lmsz.setToolTip("Числовой код локальной меры (ЛМСЗ) в реестре региона")
        org_grid.addWidget(lbl_lmsz, 1, 2)
        org_grid.addWidget(self.txt_lmsz, 1, 3)

        lbl_cat = QLabel("Код категории получателя:")
        lbl_cat.setObjectName("FieldLabel")
        saved_cat = str(self.settings.value("ui/code_category", ""))
        self.txt_category = QLineEdit(saved_cat)
        self.txt_category.setFixedHeight(34)
        self.txt_category.setPlaceholderText("Числовой код (напр. 3200133300153115004)")
        self.txt_category.setToolTip("Числовой код категории получателя локальной меры по классификатору КМСЗ")
        org_grid.addWidget(lbl_cat, 2, 2)
        org_grid.addWidget(self.txt_category, 2, 3)

        lbl_fund = QLabel("Источник финансирования:")
        lbl_fund.setObjectName("FieldLabel")
        saved_fund = str(self.settings.value("ui/funding_source", "5"))
        self.txt_funding = QLineEdit(saved_fund)
        self.txt_funding.setFixedHeight(34)
        self.txt_funding.setPlaceholderText("5 = бюджет субъекта РФ")
        self.txt_funding.setToolTip("Код источника финансирования (5 - бюджет субъекта РФ, 1 - федеральный бюджет)")
        org_grid.addWidget(lbl_fund, 3, 2)
        org_grid.addWidget(self.txt_funding, 3, 3)

        org_grid.setColumnStretch(1, 1)
        org_grid.setColumnStretch(3, 1)
        org_outer.addLayout(org_grid)
        main_layout.addWidget(org_card)

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

    def apply_theme(self, theme: str) -> None:
        """Applies dark or light theme across palette, QSS, and Windows titlebar."""
        self.current_theme = "light" if theme == "light" else "dark"
        is_dark = self.current_theme == "dark"
        app = QApplication.instance()
        if isinstance(app, QApplication):
            apply_studio_theme(app, self.current_theme)
        self.setStyleSheet(build_studio_stylesheet(self.current_theme))
        _set_windows_titlebar_dark(self, is_dark)
        self.btn_theme.setText("☀ Светлая тема" if is_dark else "☾ Тёмная тема")
        self.settings.setValue("ui/theme", self.current_theme)

    def _toggle_theme(self) -> None:
        next_theme = "light" if self.current_theme == "dark" else "dark"
        self.apply_theme(next_theme)

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

        provider_val = self.txt_provider.text().strip() or "1788"
        inn_val = self.txt_inn.text().strip()
        kpp_val = self.txt_kpp.text().strip()
        ogrn_val = self.txt_ogrn.text().strip()
        tmsz_val = self.txt_tmsz.text().strip() or "220119"
        lmsz_val = self.txt_lmsz.text().strip()
        cat_val = self.txt_category.text().strip()
        fund_val = self.txt_funding.text().strip() or "5"

        self.settings.setValue("ui/provider_code", provider_val)
        self.settings.setValue("ui/onmsz_inn", inn_val)
        self.settings.setValue("ui/onmsz_kpp", kpp_val)
        self.settings.setValue("ui/onmsz_ogrn", ogrn_val)
        self.settings.setValue("ui/code_tmsz", tmsz_val)
        self.settings.setValue("ui/code_lmsz", lmsz_val)
        self.settings.setValue("ui/code_category", cat_val)
        self.settings.setValue("ui/funding_source", fund_val)

        config = ConversionConfig(
            input_path=Path(input_dir_str),
            output_dir=Path(output_dir_str),
            recursive_search=self.cb_recursive.isChecked(),
            split_by_months=self.cb_split_months.isChecked(),
            export_csv=self.cb_format_csv.isChecked(),
            export_xlsx=self.cb_format_xlsx.isChecked(),
            provider_code=provider_val,
            onmsz_inn=inn_val,
            onmsz_kpp=kpp_val,
            onmsz_ogrn=ogrn_val,
            code_tmsz=tmsz_val,
            code_lmsz_num=lmsz_val,
            code_category_num=cat_val,
            funding_source=fund_val,
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
    if sys.platform == "win32":
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("egisso.to.ecp.desktop.1")
        except (AttributeError, OSError):
            pass
    app = QApplication.instance()
    if not isinstance(app, QApplication):
        app = QApplication(sys.argv)
    app.setWindowIcon(create_app_icon())
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    run_gui()
