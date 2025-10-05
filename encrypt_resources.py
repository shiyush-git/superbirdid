#!/usr/bin/env python3
"""
资源文件加密工具
加密模型和数据库文件，防止被轻易提取
"""
import os
import sys
from cryptography.fernet import Fernet
import base64
import hashlib

# 生成密钥（基于应用特征，不要硬编码）
def generate_key():
    """基于应用标识生成加密密钥"""
    # 使用应用bundle ID和版本号生成密钥
    seed = "com.superbirdid.app.v1.0.0.secret"
    key = hashlib.sha256(seed.encode()).digest()
    return base64.urlsafe_b64encode(key)

def encrypt_file(input_path, output_path, key):
    """加密单个文件"""
    fernet = Fernet(key)

    with open(input_path, 'rb') as f:
        data = f.read()

    encrypted = fernet.encrypt(data)

    with open(output_path, 'wb') as f:
        f.write(encrypted)

    print(f"✓ 已加密: {os.path.basename(input_path)} -> {os.path.basename(output_path)}")

def decrypt_file(input_path, output_path, key):
    """解密单个文件"""
    fernet = Fernet(key)

    with open(input_path, 'rb') as f:
        encrypted = f.read()

    decrypted = fernet.decrypt(encrypted)

    with open(output_path, 'wb') as f:
        f.write(decrypted)

def main():
    # 需要加密的文件
    files_to_encrypt = [
        'birdid2024.pt',
        'yolo11x.pt',
        'bird_reference.sqlite'
    ]

    key = generate_key()

    # 创建加密文件目录
    os.makedirs('encrypted_resources', exist_ok=True)

    for filename in files_to_encrypt:
        if os.path.exists(filename):
            output = os.path.join('encrypted_resources', filename + '.enc')
            encrypt_file(filename, output, key)
        else:
            print(f"⚠️ 文件不存在: {filename}")

    # 保存密钥信息（用于运行时解密）
    with open('resource_key.py', 'w') as f:
        f.write(f'''# 自动生成的资源密钥
# 不要修改此文件

import base64
import hashlib

def get_resource_key():
    """获取资源解密密钥"""
    seed = "com.superbirdid.app.v1.0.0.secret"
    key = hashlib.sha256(seed.encode()).digest()
    return base64.urlsafe_b64encode(key)
''')

    print("\n✅ 加密完成！")
    print("加密文件位于: encrypted_resources/")
    print("密钥模块: resource_key.py")

if __name__ == '__main__':
    main()
