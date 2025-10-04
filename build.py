#!/usr/bin/env python3
"""
SuperBirdID 打包脚本
使用 PyInstaller 将 SuperBirdId.py 打包为单个可执行文件
"""

import os
import subprocess
import sys
import shutil

def build_executable():
    """构建可执行文件"""

    # 确保在正确的目录中
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)

    print("=== SuperBirdID 打包开始 ===")
    print(f"工作目录: {script_dir}")

    # 清理之前的构建
    if os.path.exists("build"):
        print("清理旧的 build 目录...")
        shutil.rmtree("build")
    if os.path.exists("dist"):
        print("清理旧的 dist 目录...")
        shutil.rmtree("dist")
    if os.path.exists("SuperBirdId.spec"):
        print("清理旧的 spec 文件...")
        os.remove("SuperBirdId.spec")

    # 检查必要文件
    required_files = [
        "SuperBirdId.py",
        "birdid2024.pt",
        "birdinfo.json",
        "endemic.json",
        "labelmap.csv",
        "yolo11x.pt"
    ]

    missing_files = []
    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)

    if missing_files:
        print(f"错误: 缺少必要文件: {missing_files}")
        return False

    # 检查可选文件
    optional_files = [
        "bird_database_manager.py",
        "ebird_country_filter.py",
        "bird_reference.sqlite"
    ]

    # 构建数据文件列表
    data_files = []
    for file in required_files[1:]:  # 跳过主程序文件
        data_files.append(f"--add-data={file}:.")

    for file in optional_files:
        if os.path.exists(file):
            data_files.append(f"--add-data={file}:.")
            print(f"✓ 包含可选文件: {file}")
        else:
            print(f"⚠ 跳过缺失文件: {file}")

    # 添加缓存目录（如果存在）
    if os.path.exists("ebird_cache"):
        data_files.append("--add-data=ebird_cache:ebird_cache")
        print("✓ 包含 eBird 缓存目录")

    # PyInstaller 命令
    cmd = [
        "pyinstaller",
        "--onefile",                    # 打包为单个文件
        "--console",                    # 保持控制台模式
        "--name=SuperBirdID",           # 可执行文件名
        "--clean",                      # 清理临时文件
        "--noconfirm",                  # 不询问覆盖
        *data_files,                    # 添加数据文件
        "SuperBirdId.py"                # 主程序
    ]

    print(f"执行命令: {' '.join(cmd)}")
    print("\n开始打包...")

    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("✓ 打包成功!")

        # 检查输出文件
        exe_path = os.path.join("dist", "SuperBirdID")
        if os.path.exists(exe_path):
            file_size = os.path.getsize(exe_path) / (1024 * 1024)  # MB
            print(f"✓ 可执行文件已创建: {exe_path}")
            print(f"✓ 文件大小: {file_size:.1f} MB")

            # 设置执行权限 (macOS/Linux)
            if sys.platform != "win32":
                os.chmod(exe_path, 0o755)
                print("✓ 已设置执行权限")

            print(f"\n=== 打包完成 ===")
            print(f"可执行文件路径: {exe_path}")
            print(f"运行命令: {exe_path}")
            return True
        else:
            print("✗ 打包失败: 找不到输出文件")
            return False

    except subprocess.CalledProcessError as e:
        print(f"✗ 打包失败: {e}")
        print(f"错误输出: {e.stderr}")
        return False

if __name__ == "__main__":
    success = build_executable()
    sys.exit(0 if success else 1)