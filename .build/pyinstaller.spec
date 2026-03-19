# -*- mode: python ; coding: utf-8 -*-
import sys
from PyInstaller.utils.hooks import collect_data

a = Analysis(
    ["../scholartools/cli/__init__.py"],
    pathex=[".."],
    binaries=[],
    datas=collect_data("scholartools"),
    hiddenimports=[
        "pdfplumber",
        "pdfplumber.utils",
        "pdfminer",
        "pdfminer.high_level",
        "pdfminer.layout",
        "pdfminer.pdfpage",
        "pdfminer.converter",
        "cryptography",
        "Cryptodome",
        "minio",
        "urllib3",
        "certifi",
        "charset_normalizer",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

# Windows: name="scht.exe" — handled automatically by PyInstaller on Windows
# macOS: codesign manually after build or via CI with APPLE_SIGNING_IDENTITY env
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="scht",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="scht",
)
