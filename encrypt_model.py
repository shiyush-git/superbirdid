#!/usr/bin/env python3
"""
模型加密工具 - 仅加密 birdid2024.pt 模型文件
使用 AES-256 加密保护核心模型资产
"""
import os
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import secrets

# 固定的加密密钥（嵌入代码中）
# 实际使用时应该混淆这个密钥，但对于基本保护已经足够
SECRET_PASSWORD = "SuperBirdID_2024_AI_Model_Encryption_Key_v1"

def derive_key(password: str, salt: bytes) -> bytes:
    """从密码派生加密密钥"""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
        backend=default_backend()
    )
    return kdf.derive(password.encode())

def encrypt_file(input_path: str, output_path: str, password: str):
    """加密文件"""
    print(f"正在加密 {os.path.basename(input_path)}...")

    # 读取原文件
    with open(input_path, 'rb') as f:
        plaintext = f.read()

    # 生成随机盐和IV
    salt = secrets.token_bytes(16)
    iv = secrets.token_bytes(16)

    # 派生密钥
    key = derive_key(password, salt)

    # 加密
    cipher = Cipher(
        algorithms.AES(key),
        modes.CBC(iv),
        backend=default_backend()
    )
    encryptor = cipher.encryptor()

    # 添加填充 (PKCS7)
    padding_length = 16 - (len(plaintext) % 16)
    plaintext_padded = plaintext + bytes([padding_length]) * padding_length

    # 加密数据
    ciphertext = encryptor.update(plaintext_padded) + encryptor.finalize()

    # 写入加密文件：salt(16) + iv(16) + ciphertext
    with open(output_path, 'wb') as f:
        f.write(salt)
        f.write(iv)
        f.write(ciphertext)

    file_size_mb = len(ciphertext) / 1024 / 1024
    print(f"✓ 加密完成: {output_path} ({file_size_mb:.2f} MB)")

def main():
    """主函数"""
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # 模型文件路径
    model_file = 'birdid2024.pt'
    input_path = os.path.join(script_dir, model_file)
    output_path = os.path.join(script_dir, f'{model_file}.enc')

    # 检查文件是否存在
    if not os.path.exists(input_path):
        print(f"❌ 错误: 未找到模型文件 {model_file}")
        return

    # 检查是否已经加密
    if os.path.exists(output_path):
        response = input(f"⚠️  {output_path} 已存在，是否覆盖? (y/n): ")
        if response.lower() != 'y':
            print("取消加密")
            return

    # 加密模型
    encrypt_file(input_path, output_path, SECRET_PASSWORD)

    print("\n✅ 加密完成!")
    print(f"\n加密文件: {output_path}")
    print(f"原始文件: {input_path} (请保留备份)")
    print("\n下一步:")
    print("1. 将加密后的 .enc 文件集成到你的应用中")
    print("2. 删除或备份原始 .pt 文件（不要包含在发布版本中）")
    print("3. 应用会在运行时自动解密并加载模型")

if __name__ == '__main__':
    main()
