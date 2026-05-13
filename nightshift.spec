# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for nightshift. See cycles/cycle-03/plan.md.

a = Analysis(
    ['src/nightshift/__main__.py'],
    pathex=['src'],
    binaries=[],
    datas=[],
    hiddenimports=[
        'pystray._win32',         # tray backend
        'PIL._tkinter_finder',    # Pillow <-> Tk bridge
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'astral.geocoder',        # large city DB; we use lat/lon only
        'tkinter.test',
        'unittest',
        'pydoc_data',
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='nightshift',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/nightshift.ico',
)
