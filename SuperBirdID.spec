# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['SuperBirdID_GUI.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('icon.png', '.'),
        ('icon.icns', '.'),
        ('birdid2024.pt.enc', '.'),  # 加密模型（生产版本）
        ('yolo11l.pt', '.'),  # YOLO11-Large 检测模型
        ('bird_reference.sqlite', '.'),
        ('birdinfo.json', '.'),  # 保留作为备用
        ('ebird_regions.json', '.'),  # eBird 国家和地区数据
        ('offline_ebird_data', 'offline_ebird_data'),
        ('exiftool_bundle', 'exiftool_bundle'),  # 完整的 ExifTool bundle（包含所有依赖）
        ('SuperBirdID_API.py', '.'),  # API 服务器模块
        ('ebird_country_filter.py', '.'),  # eBird 过滤器模块
    ],
    hiddenimports=['SuperBirdID_API', 'ebird_country_filter'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['PySide6', 'PyQt5', 'PyQt6'],  # 排除未使用的 Qt 包
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
    target_arch=None,  # 使用当前架构（避免 cv2 兼容性问题）
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
    info_plist={
        'CFBundleShortVersionString': '3.2.1',
        'CFBundleVersion': '3.2.1',
        'NSSupportsAutomaticTermination': False,
        'NSSupportsAutomaticGraphicsSwitching': True,
        'NSAppSleepDisabled': True,
        'NSQuitAlwaysKeepsWindows': False,  # 禁用Resume功能
    },
)
