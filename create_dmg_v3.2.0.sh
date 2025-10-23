#!/bin/bash
set -e

# 版本信息
VERSION="3.2.0"
APP_NAME="SuperBirdID"
APP_PATH="dist/${APP_NAME}.app"
DMG_NAME="${APP_NAME}-v${VERSION}.dmg"
VOL_NAME="SuperBirdID v${VERSION}"
TEMP_DMG="temp.dmg"

echo "🔨 创建 SuperBirdID v${VERSION} DMG 镜像..."

# 检查必需文件
if [ ! -d "${APP_PATH}" ]; then
    echo "❌ 错误: 未找到主应用 ${APP_PATH}"
    echo "请先运行打包命令生成应用"
    exit 1
fi

if [ ! -d "SuperBirdIDPlugin.lrplugin" ]; then
    echo "❌ 错误: 未找到 Lightroom 插件"
    exit 1
fi

# 清理旧文件
echo "🧹 清理旧文件..."
rm -f "${DMG_NAME}" "${TEMP_DMG}"

# 创建临时 DMG（3GB，足够大以容纳所有文件）
echo "📦 创建临时 DMG..."
hdiutil create -size 3g -fs HFS+ -volname "${VOL_NAME}" "${TEMP_DMG}"

# 挂载临时 DMG
echo "💿 挂载临时 DMG..."
MOUNT_OUTPUT=$(hdiutil attach -readwrite -noverify -noautoopen "${TEMP_DMG}")
MOUNT_DIR=$(echo "${MOUNT_OUTPUT}" | grep "/Volumes/" | sed 's/^.*\/Volumes/\/Volumes/' | sed 's/[[:space:]]*$//')

echo "✓ 临时 DMG 已挂载到: ${MOUNT_DIR}"

# 复制主应用到 DMG
echo "📦 复制主应用..."
cp -R "${APP_PATH}" "${MOUNT_DIR}/${APP_NAME}.app"

# 复制 Lightroom 插件
echo "🔌 复制 Lightroom 插件..."
if [ -d "${MOUNT_DIR}/SuperBirdIDPlugin.lrplugin" ]; then
    rm -rf "${MOUNT_DIR}/SuperBirdIDPlugin.lrplugin"
fi
cp -R SuperBirdIDPlugin.lrplugin "${MOUNT_DIR}/"

# 创建文档目录
echo "📚 创建文档目录..."
mkdir -p "${MOUNT_DIR}/Documentation"

# 复制文档
echo "📖 复制安装说明..."
cp INSTALL_GUIDE.md "${MOUNT_DIR}/Documentation/INSTALL_GUIDE.md" 2>/dev/null || true
cp CODE_REVIEW_v3.1.0.md "${MOUNT_DIR}/Documentation/CHANGELOG_v3.2.0.md" 2>/dev/null || true

# 创建快速开始指南
echo "📝 创建快速开始指南..."
cat > "${MOUNT_DIR}/QuickStart.txt" <<DOCEOF
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║             慧眼识鸟 v${VERSION} - 快速开始                   ║
║              SuperBirdID - Quick Start                        ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝

🚀 安装步骤（3 分钟）：

第一步：安装主程序
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. 将 "${APP_NAME}.app" 拖到 "Applications" 文件夹
2. 首次启动：右键点击 → "打开"（绕过安全提示）
3. 在程序中选择您的常用拍摄国家/地区

第二步：安装 Lightroom 插件（可选）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. 打开 Lightroom Classic
2. 菜单 → 文件 → 增效工具管理器
3. 点击"添加"，选择 "SuperBirdIDPlugin.lrplugin"
4. 确认插件已启用

✅ 完成！

🎯 v${VERSION} 新特性：
- ✅ GPS 地理定位更精确（返回实际国家代码）
- ✅ 修复国家列表显示问题
- ✅ 离线地理数据库，无需网络

📖 详细说明：请查看 "Documentation" 文件夹

⚠️ 重要提示：
- 主程序和 Lightroom 插件都需要安装
- 使用 Lightroom 插件前，必须先启动主程序
- 首次使用请在主程序中设置国家/地区

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
版本: v${VERSION}
更新日期: $(date '+%Y-%m-%d')
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DOCEOF

# 创建快捷方式
echo "🔗 创建 Applications 快捷方式..."
ln -s /Applications "${MOUNT_DIR}/Applications"

echo "🔗 创建 Lightroom 插件目录快捷方式..."
ln -s "$HOME/Library/Application Support/Adobe/Lightroom/Modules" "${MOUNT_DIR}/Lightroom_Plugins"

# 设置窗口样式
echo "🎨 设置 DMG 窗口样式..."
sleep 2

osascript <<'APPLESCRIPT'
tell application "Finder"
    tell disk "SuperBirdID v3.2.0"
        open
        set current view of container window to icon view
        set toolbar visible of container window to false
        set statusbar visible of container window to false
        set the bounds of container window to {300, 100, 1100, 600}
        set viewOptions to the icon view options of container window
        set arrangement of viewOptions to not arranged
        set icon size of viewOptions to 72
        set text size of viewOptions to 12

        set position of item "SuperBirdID.app" of container window to {120, 120}
        set position of item "Applications" of container window to {120, 320}
        set position of item "SuperBirdIDPlugin.lrplugin" of container window to {360, 120}

        -- Try to set Lightroom_Plugins position (may fail if not visible)
        try
            set position of item "Lightroom_Plugins" of container window to {600, 120}
        end try

        set position of item "Documentation" of container window to {360, 240}
        set position of item "QuickStart.txt" of container window to {360, 360}

        update without registering applications
        delay 3
        close
    end tell
end tell
APPLESCRIPT

echo "💾 同步文件系统..."
sync
sleep 2

# 卸载临时 DMG
echo "📤 卸载临时 DMG..."
hdiutil detach "${MOUNT_DIR}" || {
    echo "⚠️ 自动卸载失败，请手动卸载后重试"
    exit 1
}

# 转换为压缩的 DMG
echo "🗜️  压缩 DMG（可能需要几分钟）..."
hdiutil convert "${TEMP_DMG}" -format UDZO -o "${DMG_NAME}"

# 清理临时文件
echo "🧹 清理临时文件..."
rm -f "${TEMP_DMG}"

# 获取文件大小
DMG_SIZE=$(du -h "${DMG_NAME}" | cut -f1)

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ DMG 创建完成！"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📦 文件: ${DMG_NAME}"
echo "📏 大小: ${DMG_SIZE}"
echo ""
echo "🔍 验证 DMG："
echo "  hdiutil verify \"${DMG_NAME}\""
echo ""
echo "🚀 下一步："
echo "  1. 验证 DMG 可以正常打开"
echo "  2. 测试安装流程"
echo "  3. 准备发布"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
