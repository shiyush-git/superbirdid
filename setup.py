"""
py2app setup script for SuperBirdID
macOS 应用打包配置
"""
from setuptools import setup

APP = ['SuperBirdID_GUI.py']
DATA_FILES = [
    'bird_class_index.txt',
    'SuperBirdID_classifier.pth',
    'ebird_taxonomy.db',
    'icon.icns',
    'icon.png'
]

OPTIONS = {
    'argv_emulation': False,
    'iconfile': 'icon.icns',
    'plist': {
        'CFBundleName': 'SuperBirdID',
        'CFBundleDisplayName': 'SuperBirdID',
        'CFBundleGetInfoString': "AI 鸟类智能识别系统",
        'CFBundleIdentifier': "com.superbirdid.app",
        'CFBundleVersion': "1.0.0",
        'CFBundleShortVersionString': "1.0.0",
        'NSHumanReadableCopyright': "© 2025 SuperBirdID",
        'NSHighResolutionCapable': True,
    },
    'packages': ['PIL', 'torch', 'torchvision', 'cv2', 'numpy', 'sqlite3'],
    'includes': ['tkinter'],
    'excludes': ['matplotlib', 'scipy', 'pandas'],
    'optimize': 2,
}

setup(
    name='SuperBirdID',
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
