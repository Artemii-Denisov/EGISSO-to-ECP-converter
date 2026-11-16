"""Build standalone Windows portable executable (EGISSO_to_ECP.exe) via PyInstaller."""

from __future__ import annotations

import shutil
from pathlib import Path

import PyInstaller.__main__

ROOT_DIR = Path(__file__).resolve().parent.parent
ENTRY_POINT = ROOT_DIR / "src" / "egisso_to_ecp" / "presentation" / "gui" / "main.py"
DIST_DIR = ROOT_DIR / "dist"
BUILD_DIR = ROOT_DIR / "build"
LICENSE_FILE = ROOT_DIR / "LICENSE"


def build() -> Path:
    """Packages the PySide6 GUI application into a single-file Windows executable."""
    args = [
        str(ENTRY_POINT),
        "--name=EGISSO_to_ECP",
        "--onefile",
        "--windowed",
        "--clean",
        "--noconfirm",
        f"--paths={ROOT_DIR / 'src'}",
        f"--distpath={DIST_DIR}",
        f"--workpath={BUILD_DIR}",
        f"--specpath={BUILD_DIR}",
        "--collect-submodules=egisso_to_ecp",
        "--exclude-module=tkinter",
        "--exclude-module=unittest",
        "--exclude-module=pytest",
        "--exclude-module=mypy",
        "--exclude-module=ruff",
        "--exclude-module=PySide6.QtNetwork",
        "--exclude-module=PySide6.QtQml",
        "--exclude-module=PySide6.QtQuick",
        "--exclude-module=PySide6.QtSql",
        "--exclude-module=PySide6.QtOpenGL",
        "--exclude-module=PySide6.QtSvg",
    ]
    PyInstaller.__main__.run(args)

    if LICENSE_FILE.exists():
        shutil.copy2(LICENSE_FILE, DIST_DIR / "LICENSE.txt")

    exe_path = DIST_DIR / "EGISSO_to_ECP.exe"
    if not exe_path.exists():
        raise FileNotFoundError(f"Ожидаемый исполняемый файл не найден: {exe_path}")
    return exe_path


if __name__ == "__main__":
    output_exe = build()
    size_mb = output_exe.stat().st_size / (1024 * 1024)
    print(f"Сборка успешно завершена: {output_exe} ({size_mb:.1f} МБ)")
