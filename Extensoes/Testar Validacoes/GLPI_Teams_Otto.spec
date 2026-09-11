# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['C:\\Automacoes\\GLPI_Teams\\main.py'],
    pathex=['C:\\Automacoes\\GLPI_Teams'],
    binaries=[],
    datas=[('config', 'config'), ('.env', '.')],
    hiddenimports=['main'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='GLPI_Teams_Otto',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
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
    name='GLPI_Teams_Otto',
)
