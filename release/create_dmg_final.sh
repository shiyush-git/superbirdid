#!/bin/bash

APP_NAME="慧眼识鸟"
VERSION="1.0.4"
DMG_NAME="${APP_NAME}-${VERSION}.dmg"
VOLUME_NAME="慧眼识鸟 ${VERSION}"
SOURCE_APP="dist/SuperBirdID.app"
TEMP_DMG="temp_dmg"

# 清理旧文件
rm -f "${DMG_NAME}"
rm -rf "${TEMP_DMG}"

# 创建临时目录
mkdir -p "${TEMP_DMG}"

# 复制应用
cp -R "${SOURCE_APP}" "${TEMP_DMG}/${APP_NAME}.app"

# 创建Applications快捷方式
ln -s /Applications "${TEMP_DMG}/Applications"

# 创建DMG
hdiutil create -volname "${VOLUME_NAME}" \
    -srcfolder "${TEMP_DMG}" \
    -ov -format UDZO \
    "${DMG_NAME}"

# 清理
rm -rf "${TEMP_DMG}"

echo "✅ DMG创建成功: ${DMG_NAME}"
