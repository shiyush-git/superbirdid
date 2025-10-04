#!/usr/bin/env python3
"""
测试可执行文件是否正常工作
"""

import subprocess
import os
import time

def test_executable():
    """测试可执行文件"""

    exe_path = "./dist/SuperBirdID"

    if not os.path.exists(exe_path):
        print("❌ 可执行文件不存在")
        return False

    print("🧪 测试可执行文件启动...")

    try:
        # 启动程序
        process = subprocess.Popen(
            [exe_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        # 等待程序启动
        time.sleep(2)

        # 检查程序是否还在运行
        if process.poll() is None:
            print("✅ 程序正常启动，正在等待输入")

            # 发送退出信号
            process.terminate()
            process.wait(timeout=5)

            return True
        else:
            # 程序已退出，检查错误
            stdout, stderr = process.communicate()
            print(f"❌ 程序异常退出")
            print(f"返回码: {process.returncode}")
            if stdout:
                print(f"标准输出: {stdout}")
            if stderr:
                print(f"错误输出: {stderr}")
            return False

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False

if __name__ == "__main__":
    test_executable()