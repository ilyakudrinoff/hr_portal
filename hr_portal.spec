# -*- coding: utf-8 -*-
import sys
from pathlib import Path

APP_NAME = "HR Portal"
AUTHOR = "HR Portal Team"

block_cipher = None

a = Analysis(
    ["hr_portal.py"],
    pathex=[str(Path(__file__).parent)],
    binaries=[],
    datas=[],
    hiddenimports=["openpyxl", "app.database", "app.services", "app.seed",
                   "app.main_window", "app.ui.common", "app.ui.employees",
                   "app.ui.reports"],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    cipher=block_cipher,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="hr_portal",
    debug=False,
    strip=False,
    upx=True,
    console=False,          # без окна консоли — чистое десктопное приложение
    icon=None,              # при желании укажите icon="assets/app.ico"
    win_version_info={
        "CompanyName": AUTHOR,
        "FileDescription": APP_NAME + " — кадровый учёт организации",
        "ProductName": APP_NAME,
        "ProductVersion": "1.0.0",
        "FileVersion": "1.0.0",
    },
)
