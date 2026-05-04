# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec pro PDF Signature Stamper
Funguje na macOS, Windows i Linux – spusť na každém OS zvlášť.
"""

import sys
import os
from pathlib import Path
import glob

block_cipher = None

# ── Najít cairosvg a cairocffi data ───────────────────────────────────────────
import cairosvg, cairocffi

cairosvg_dir  = Path(cairosvg.__file__).parent
cairocffi_dir = Path(cairocffi.__file__).parent

datas = [
    (str(cairosvg_dir),  'cairosvg'),
    (str(cairocffi_dir), 'cairocffi'),
]

# ── Na macOS přidat cairo dylibs z MacPorts nebo Homebrew ─────────────────────
binaries = []
if sys.platform == 'darwin':
    search_paths = [
        '/opt/local/lib',    # MacPorts
        '/opt/homebrew/lib', # Homebrew Apple Silicon
        '/usr/local/lib',    # Homebrew Intel
    ]
    needed = [
        'libcairo*.dylib',
        'libpixman*.dylib',
        'libfontconfig*.dylib',
        'libfreetype*.dylib',
        'libpng*.dylib',
        'libglib*.dylib',
        'libgobject*.dylib',
        'libgio*.dylib',
        'libgmodule*.dylib',
        'libgthread*.dylib',
        'libffi*.dylib',
        'libintl*.dylib',
        'libpcre*.dylib',
        'libz*.dylib',
        'libbrotli*.dylib',
        'libbz2*.dylib',
        'libexpat*.dylib',
        'liblzma*.dylib',
    ]
    for search in search_paths:
        for pattern in needed:
            for found in glob.glob(os.path.join(search, pattern)):
                binaries.append((found, '.'))

# ── Na Linuxu přidat cairo so ─────────────────────────────────────────────────
elif sys.platform.startswith('linux'):
    for pattern in ['/usr/lib/x86_64-linux-gnu/libcairo*.so*',
                    '/usr/lib/libcairo*.so*',
                    '/usr/local/lib/libcairo*.so*']:
        for found in glob.glob(pattern):
            binaries.append((found, '.'))

# ── Hlavní analýza ────────────────────────────────────────────────────────────
a = Analysis(
    ['pdfstamper.py'],
    pathex=['.'],
    binaries=binaries,
    datas=datas,
    hiddenimports=[
        'cairosvg',
        'cairocffi',
        'cssselect2',
        'tinycss2',
        'defusedxml',
        'PIL',
        'PIL.Image',
        'reportlab',
        'reportlab.pdfgen',
        'reportlab.lib',
        'reportlab.lib.colors',
        'reportlab.lib.utils',
        'pyhanko',
        'pyhanko.sign',
        'pyhanko.sign.signers',
        'pyhanko.sign.fields',
        'pyhanko.stamp',
        'pyhanko.stamp.static',
        'pyhanko.pdf_utils',
        'pyhanko.pdf_utils.incremental_writer',
        'pyhanko_certvalidator',
        'cryptography',
        'fitz',
        'lxml',
        'lxml.etree',
        'PyQt6',
        'PyQt6.QtWidgets',
        'PyQt6.QtCore',
        'PyQt6.QtGui',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'numpy', 'scipy'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# ── macOS: .app bundle ────────────────────────────────────────────────────────
if sys.platform == 'darwin':
    exe = EXE(
        pyz, a.scripts, [],
        exclude_binaries=True,
        name='PDFStamper',
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=False,
        console=False,
        disable_windowed_traceback=False,
        codesign_identity=None,
        entitlements_file=None,
    )
    coll = COLLECT(
        exe, a.binaries, a.zipfiles, a.datas,
        strip=False,
        upx=False,
        upx_exclude=[],
        name='PDFStamper',
    )
    app = BUNDLE(
        coll,
        name='PDFStamper.app',
        icon=None,
        bundle_identifier='cz.zcu.pdfstamper',
        info_plist={
            'NSPrincipalClass': 'NSApplication',
            'NSHighResolutionCapable': True,
            'CFBundleShortVersionString': '1.0.0',
            'CFBundleName': 'PDF Signature Stamper',
        },
    )

# ── Windows / Linux: jeden exe/binary ─────────────────────────────────────────
else:
    exe = EXE(
        pyz, a.scripts, a.binaries, a.zipfiles, a.datas, [],
        name='PDFStamper',
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        upx_exclude=[],
        runtime_tmpdir=None,
        console=False,
        disable_windowed_traceback=False,
        codesign_identity=None,
        entitlements_file=None,
    )
