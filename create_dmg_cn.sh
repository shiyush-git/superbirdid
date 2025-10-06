#!/bin/bash

APP_NAME="慧眼识鸟"
VERSION="1.0.0"
DMG_NAME="${APP_NAME}-${VERSION}.dmg"
VOLUME_NAME="慧眼识鸟"
SOURCE_APP="${APP_NAME}.app"

echo "=== 创建 ${APP_NAME} DMG 安装包 ==="
echo ""

# 1. 创建临时目录
echo "步骤 1/6: 准备文件..."
rm -rf dmg_temp
mkdir -p dmg_temp
cp -R "$SOURCE_APP" dmg_temp/

# 2. 创建 Applications 文件夹的符号链接
echo "步骤 2/6: 创建 Applications 快捷方式..."
ln -s /Applications dmg_temp/Applications

# 3. 创建背景图片文件夹（隐藏）
echo "步骤 3/6: 设置 DMG 外观..."
mkdir -p dmg_temp/.background

# 4. 创建一个简单的安装说明文本文件
cat > dmg_temp/.DS_Store_instructions.txt << 'EOF'
请将 慧眼识鸟.app 拖动到 Applications 文件夹
EOF

# 5. 创建 DMG
echo "步骤 4/6: 创建 DMG..."
rm -f "$DMG_NAME"

hdiutil create -volname "$VOLUME_NAME" \
    -srcfolder dmg_temp \
    -ov -format UDZO \
    -fs HFS+ \
    "$DMG_NAME"

if [ $? -ne 0 ]; then
    echo "❌ DMG 创建失败"
    exit 1
fi

echo "✓ DMG 创建成功"

# 6. 签名 DMG
echo ""
echo "步骤 5/6: 签名 DMG..."
codesign --force --sign "Developer ID Application: James Zhen Yu (JWR6FDB52H)" "$DMG_NAME"

if [ $? -ne 0 ]; then
    echo "❌ DMG 签名失败"
    exit 1
fi

# 验证签名
codesign --verify --verbose=2 "$DMG_NAME"
echo "✓ DMG 签名成功"

# 7. 清理
echo ""
echo "步骤 6/6: 清理临时文件..."
rm -rf dmg_temp

echo ""
echo "=== DMG 创建完成！==="
echo "✓ 文件: $DMG_NAME"
ls -lh "$DMG_NAME"

echo ""
echo "使用说明："
echo "1. 双击 DMG 文件打开"
echo "2. 将 ${APP_NAME}.app 拖动到 Applications 文件夹"
echo "3. 完成安装"
