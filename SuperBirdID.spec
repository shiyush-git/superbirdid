# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['SuperBirdID_GUI.py'],
    pathex=[],
    binaries=[
        ('exiftool', 'exiftool'),  # ExifTool二进制文件
    ],
    datas=[
        ('icon.png', '.'),
        ('icon.icns', '.'),
        ('birdid2024.pt.enc', '.'),  # 加密模型
        ('birdid2024.pt', '.'),  # 未加密模型（用于测试）
        ('yolo11x.pt', '.'),
        ('bird_reference.sqlite', '.'),
        ('birdinfo.json', '.'),  # 保留作为备用
        ('labelmap.csv', '.'),
        ('scmapping.json', '.'),
        ('offline_ebird_data', 'offline_ebird_data'),
        ('SuperBirdIDPlugin.lrplugin', 'Plugins/SuperBirdIDPlugin.lrplugin'),  # Lightroom插件
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
    target_arch='arm64',  # Apple Silicon (Intel 用户可通过 Rosetta 2 运行)
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
