"""Build standalone Windows portable executable (EGISSO_to_ECP.exe) via PyInstaller."""

from __future__ import annotations

import ctypes
import os
import shutil
import sys
from ctypes import wintypes
from pathlib import Path

import PyInstaller.__main__

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "src"))

from egisso_to_ecp.presentation.gui.icon import write_ico_file  # noqa: E402

ENTRY_POINT = ROOT_DIR / "src" / "egisso_to_ecp" / "presentation" / "gui" / "main.py"
DIST_DIR = ROOT_DIR / "dist"
BUILD_DIR = ROOT_DIR / "build"
LICENSE_FILE = ROOT_DIR / "LICENSE"
ICON_FILE = ROOT_DIR / "assets" / "app_icon.ico"


def build() -> Path:
    """Packages the PySide6 GUI application into a single-file Windows executable."""
    write_ico_file(ICON_FILE)

    args = [
        str(ENTRY_POINT),
        "--name=EGISSO_to_ECP",
        "--onefile",
        "--windowed",
        "--clean",
        "--noconfirm",
        f"--icon={ICON_FILE}",
        f"--add-data={ICON_FILE};assets",
        f"--paths={ROOT_DIR / 'src'}",
        f"--distpath={DIST_DIR}",
        f"--workpath={BUILD_DIR}",
        f"--specpath={BUILD_DIR}",
        "--collect-submodules=egisso_to_ecp",
        "--collect-all=python_calamine",
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

    alias_exe = DIST_DIR / "Конвертер_ЕГИССО_ЕЦП.exe"
    try:
        shutil.copy2(exe_path, alias_exe)
    except PermissionError:
        pass

    _refresh_windows_icon_cache(exe_path)
    _refresh_windows_icon_cache(alias_exe)
    return exe_path


class _SHFILEINFOW(ctypes.Structure):
    _fields_ = [
        ("hIcon", wintypes.HICON),
        ("iIcon", ctypes.c_int),
        ("dwAttributes", wintypes.DWORD),
        ("szDisplayName", wintypes.WCHAR * 260),
        ("szTypeName", wintypes.WCHAR * 80),
    ]


def _refresh_windows_icon_cache(exe_path: Path) -> None:
    """Evicts stale Explorer icon cache entries for `exe_path` (non-blocking)."""
    if sys.platform != "win32":
        return
    try:
        shell32 = ctypes.windll.shell32
        shell32.SHChangeNotify.argtypes = [
            wintypes.LONG,
            wintypes.UINT,
            ctypes.c_void_p,
            ctypes.c_void_p,
        ]

        sfi = _SHFILEINFOW()
        if shell32.SHGetFileInfoW(str(exe_path), 0, ctypes.byref(sfi), ctypes.sizeof(sfi), 0x4000):
            shell32.SHUpdateImageW.argtypes = [
                wintypes.LPCWSTR,
                ctypes.c_int,
                wintypes.UINT,
                ctypes.c_int,
            ]
            shell32.SHUpdateImageW(str(exe_path), 0, 0, sfi.iIcon)

        path_ptr = ctypes.c_wchar_p(str(exe_path))
        # Notify Explorer as delete + create + item update + system image update (all FLUSHNOWAIT)
        shell32.SHChangeNotify(0x00000004, 0x2005, path_ptr, None)  # SHCNE_DELETE
        shell32.SHChangeNotify(0x00000002, 0x2005, path_ptr, None)  # SHCNE_CREATE
        shell32.SHChangeNotify(0x00002000, 0x2005, path_ptr, None)  # SHCNE_UPDATEITEM
        shell32.SHChangeNotify(0x00008000, 0x2003, ctypes.c_void_p(-1), None)  # SHCNE_UPDATEIMAGE

        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            legacy_cache = Path(local_app_data) / "IconCache.db"
            if legacy_cache.exists():
                legacy_cache.unlink(missing_ok=True)
    except (AttributeError, OSError):
        pass


if __name__ == "__main__":
    output_exe = build()
    size_mb = output_exe.stat().st_size / (1024 * 1024)
    print(f"Сборка успешно завершена: {output_exe} ({size_mb:.1f} МБ)")
