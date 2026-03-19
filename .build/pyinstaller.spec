# -*- mode: python ; coding: utf-8 -*-
import os
from PyInstaller.utils.hooks import collect_all, collect_data_files

datas, binaries, hiddenimports = [], [], []
for _pkg in ["pydantic", "pydantic_core", "scholartools"]:
    _d, _b, _h = collect_all(_pkg)
    datas += _d; binaries += _b; hiddenimports += _h

datas += collect_data_files("scholartools")

a = Analysis(
    [os.path.join(SPECPATH, "..", "scholartools", "cli", "__init__.py")],
    pathex=[os.path.join(SPECPATH, "..")],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports + [
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
        "httpx",
        "anyio",
        "anyio._backends._asyncio",
        "annotated_types",
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
