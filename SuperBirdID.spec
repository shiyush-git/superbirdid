# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['SuperBirdID_GUI.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('icon.png', '.'),
        ('icon.icns', '.'),
        ('birdid2024.pt', '.'),
        ('yolo11x.pt', '.'),
        ('bird_reference.sqlite', '.'),
        ('birdinfo.json', '.'),
        ('cindex.json', '.'),
        ('eindex.json', '.'),
        ('endemic.json', '.'),
        ('labelmap.csv', '.'),
        ('scmapping.json', '.'),
        ('offline_ebird_data', 'offline_ebird_data'),
        ('ebird_cache', 'ebird_cache'),
    ],
    hiddenimports=[],
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
    name='SuperBirdID',
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
    icon=['icon.icns'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='SuperBirdID',
)
app = BUNDLE(
    coll,
    name='SuperBirdID.app',
    icon='icon.icns',
    bundle_identifier='com.superbirdid.app',
)
