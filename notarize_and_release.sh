#!/bin/bash
set -e

DMG_FILE="SuperBirdID.dmg"
APPLE_ID="james@jamesphotography.com.au"
TEAM_ID="JWR6FDB52H"
APP_PASSWORD="vfmy-vjcb-injx-guid"

echo "📤 提交 DMG 到苹果公证服务..."
echo "   这可能需要几分钟时间，请耐心等待..."
echo ""

# 提交公证（直接使用凭证，不需要 keychain profile）
SUBMISSION_OUTPUT=$(xcrun notarytool submit "${DMG_FILE}" \
    --apple-id "${APPLE_ID}" \
    --team-id "${TEAM_ID}" \
    --password "${APP_PASSWORD}" \
    --wait 2>&1)

echo "${SUBMISSION_OUTPUT}"

# 检查公证是否成功
if echo "${SUBMISSION_OUTPUT}" | grep -q "status: Accepted"; then
    echo ""
    echo "✅ 公证成功！"

    # 装订公证票据
    echo "📎 装订公证票据到 DMG..."
    xcrun stapler staple "${DMG_FILE}"

    # 验证装订
    echo "🔍 验证公证票据..."
    xcrun stapler validate "${DMG_FILE}"

    # 移动到 release 目录
    echo "📦 移动到 release 目录..."
    mkdir -p release
    mv "${DMG_FILE}" "release/${DMG_FILE}"

    # 计算校验和
    echo "🔐 计算 SHA-256 校验和..."
    cd release
    shasum -a 256 "${DMG_FILE}" > "${DMG_FILE}.sha256"

    echo ""
    echo "🎉 全部完成！"
    echo ""
    echo "发布文件位于: release/${DMG_FILE}"
    echo "SHA-256: $(cat ${DMG_FILE}.sha256)"
    echo ""
else
    echo ""
    echo "❌ 公证失败"
    echo ""
    echo "请检查上面的错误信息，常见原因："
    echo "  - 代码签名问题"
    echo "  - 缺少 hardened runtime"
    echo "  - 包含未签名的二进制文件"
    echo ""

    # 尝试获取详细日志
    SUBMISSION_ID=$(echo "${SUBMISSION_OUTPUT}" | grep "id:" | head -1 | awk '{print $2}')
    if [ -n "${SUBMISSION_ID}" ]; then
        echo "获取详细日志..."
        xcrun notarytool log "${SUBMISSION_ID}" \
            --apple-id "${APPLE_ID}" \
            --team-id "${TEAM_ID}" \
            --password "${APP_PASSWORD}"
    fi

    exit 1
fi
