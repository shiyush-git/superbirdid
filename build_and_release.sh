#!/bin/bash
set -e

echo "🚀 开始构建和发布流程..."
echo ""

# 1. 清理旧文件
echo "🧹 清理旧文件..."
rm -rf dist/SuperBirdID dist/SuperBirdID.app build
rm -f SuperBirdID.dmg temp.dmg
echo "✓ 清理完成"
echo ""

# 2. 打包应用
echo "📦 使用 PyInstaller 打包应用..."
pyinstaller SuperBirdID.spec
echo "✓ 打包完成"
echo ""

# 3. 代码签名
echo "✍️  对应用进行代码签名..."
codesign --deep --force --verify --verbose \
    --sign "Developer ID Application: James Zhen Yu (JWR6FDB52H)" \
    --options runtime \
    dist/SuperBirdID.app
echo "✓ 代码签名完成"
echo ""

# 4. 验证签名
echo "🔍 验证签名..."
codesign -vvv --deep --strict dist/SuperBirdID.app
echo "✓ 签名验证通过"
echo ""

# 5. 创建 DMG
echo "💿 创建 DMG 镜像..."
./create_dmg.sh
echo "✓ DMG 创建完成"
echo ""

# 6. 签名 DMG
echo "✍️  对 DMG 进行签名..."
codesign --sign "Developer ID Application: James Zhen Yu (JWR6FDB52H)" SuperBirdID.dmg
codesign -vvv SuperBirdID.dmg
echo "✓ DMG 签名完成"
echo ""

# 7. 公证和发布
echo "📤 提交公证并发布..."
./notarize_and_release.sh

echo ""
echo "🎉 构建和发布流程全部完成！"
