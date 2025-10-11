#!/bin/bash
set -e

APP_NAME="SuperBirdID"
APP_PATH="dist/${APP_NAME}.app"
DMG_NAME="${APP_NAME}.dmg"
VOL_NAME="SuperBirdID"
TEMP_DMG="temp.dmg"

echo "🔨 创建 DMG 镜像..."

# 清理旧文件
rm -f "${DMG_NAME}" "${TEMP_DMG}"

# 创建临时 DMG
hdiutil create -size 2g -fs HFS+ -volname "${VOL_NAME}" "${TEMP_DMG}"

# 挂载临时 DMG
MOUNT_OUTPUT=$(hdiutil attach -readwrite -noverify -noautoopen "${TEMP_DMG}")
MOUNT_DIR=$(echo "${MOUNT_OUTPUT}" | tail -n 1 | awk '{print $3}')

echo "✓ 临时 DMG 已挂载到: ${MOUNT_DIR}"

# 复制应用到 DMG（使用 ditto 更可靠）
echo "📦 复制主应用..."
ditto "${APP_PATH}" "${MOUNT_DIR}/${APP_NAME}.app"

# 复制 Lightroom 插件
echo "🔌 复制 Lightroom 插件..."
cp -R SuperBirdIDPlugin.lrplugin "${MOUNT_DIR}/"

# 复制使用说明
echo "📖 复制使用说明..."
cp "使用说明.md" "${MOUNT_DIR}/"

# 创建 Applications 快捷方式
ln -s /Applications "${MOUNT_DIR}/Applications"

# 设置图标位置和窗口样式（使用 AppleScript）
echo "🎨 设置 DMG 窗口样式..."
osascript <<EOF
tell application "Finder"
    tell disk "${VOL_NAME}"
        open
        set current view of container window to icon view
        set toolbar visible of container window to false
        set statusbar visible of container window to false
        set the bounds of container window to {400, 100, 1000, 550}
        set viewOptions to the icon view options of container window
        set arrangement of viewOptions to not arranged
        set icon size of viewOptions to 80
        set position of item "${APP_NAME}.app" of container window to {120, 120}
        set position of item "Applications" of container window to {120, 280}
        set position of item "SuperBirdIDPlugin.lrplugin" of container window to {300, 120}
        set position of item "使用说明.md" of container window to {300, 280}
        update without registering applications
        delay 2
        close
    end tell
end tell
EOF

# 卸载临时 DMG
hdiutil detach "${MOUNT_DIR}"

# 转换为压缩的、只读的 DMG
echo "📦 压缩 DMG..."
hdiutil convert "${TEMP_DMG}" -format UDZO -o "${DMG_NAME}"

# 清理临时文件
rm -f "${TEMP_DMG}"

echo "✅ DMG 创建完成: ${DMG_NAME}"
