#!/bin/bash
set -e

echo "🚀 开始构建和发布流程（PKG 版本）..."
echo ""

VERSION="1.0.2"

# 1. 清理旧文件
echo "🧹 清理旧文件..."
chmod -R +w dist build 2>/dev/null || true
rm -rf dist build
rm -f *.pkg
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
echo "🔍 验证应用签名..."
codesign -vvv --deep --strict dist/SuperBirdID.app
echo "✓ 应用签名验证通过"
echo ""

# 5. 创建 PKG
echo "💿 创建 PKG 安装包..."
./create_pkg.sh
echo "✓ PKG 创建完成"
echo ""

# 6. 签名 PKG
echo "✍️  对 PKG 进行签名..."
productsign --sign "Developer ID Installer: James Zhen Yu (JWR6FDB52H)" \
    "慧眼识鸟_v${VERSION}.pkg" \
    "慧眼识鸟_v${VERSION}-signed.pkg"

# 验证 PKG 签名
echo "🔍 验证 PKG 签名..."
pkgutil --check-signature "慧眼识鸟_v${VERSION}-signed.pkg"
echo "✓ PKG 签名完成"
echo ""

# 7. 公证 PKG（可选，需要上传到 Apple）
echo "📤 提交公证..."
echo "注意：PKG 公证需要上传到 Apple 服务器"
echo "运行以下命令进行公证："
echo "  xcrun notarytool submit 慧眼识鸟_v${VERSION}-signed.pkg \\"
echo "    --keychain-profile \"notarytool-password\" \\"
echo "    --wait"
echo ""
echo "公证完成后运行："
echo "  xcrun stapler staple 慧眼识鸟_v${VERSION}-signed.pkg"
echo ""

# 8. 显示最终文件
echo "📊 最终文件:"
ls -lh 慧眼识鸟*.pkg
echo ""

echo "🎉 构建流程完成！"
echo ""
echo "📝 测试安装:"
echo "  sudo installer -pkg 慧眼识鸟_v${VERSION}-signed.pkg -target /"
echo ""
echo "📝 卸载命令:"
echo "  sudo rm -rf /Applications/慧眼识鸟.app"
echo ""
