# -*- mode: python ; coding: utf-8 -*-
"""Configurazione PyInstaller per BOM Compare.

Uso:  pyinstaller --noconfirm --clean bomcompare.spec
      (variabile BOMCOMPARE_ONEFILE=1 per un unico file .exe)
"""
import os

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

ONEFILE = os.environ.get("BOMCOMPARE_ONEFILE", "0") == "1"

datas = [
    ("config.json", "."),
    ("assets/app.ico", "assets"),
    ("sample_data/*.xlsx", "sample_data"),
    ("sample_data/*.csv", "sample_data"),
]
datas += collect_data_files("qtawesome")          # font FontAwesome (offline)

hiddenimports = ["openpyxl", "xlrd", "qtawesome"]
hiddenimports += collect_submodules("reportlab.pdfbase")   # font PDF caricati dinamicamente

excludes = ["tkinter", "matplotlib", "IPython", "scipy", "PyQt5", "PySide2", "PySide6",
            "notebook", "pytest", "PyQt6.QtWebEngineCore", "PyQt6.QtWebEngineWidgets",
            "PyQt6.QtMultimedia", "PyQt6.Qt3DCore", "PyQt6.QtQuick", "PyQt6.QtQml"]

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
)
pyz = PYZ(a.pure)

common = dict(
    name="BOMCompare",
    debug=False,
    strip=False,
    upx=False,
    console=False,              # applicazione a finestre (nessuna console nera)
    icon="assets/app.ico",
)

if ONEFILE:
    exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], runtime_tmpdir=None, **common)
else:
    exe = EXE(pyz, a.scripts, [], exclude_binaries=True, **common)
    coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="BOMCompare")
