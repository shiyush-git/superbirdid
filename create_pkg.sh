#!/bin/bash
set -e

APP_NAME="慧眼识鸟"
APP_PATH="dist/SuperBirdID.app"
VERSION="1.0.2"
PKG_NAME="${APP_NAME}_v${VERSION}.pkg"
IDENTIFIER="com.superbirdid.app"
INSTALL_LOCATION="/Applications"

echo "📦 创建 PKG 安装包..."
echo ""

# 检查应用是否已构建
if [ ! -d "${APP_PATH}" ]; then
    echo "❌ 错误: 找不到应用 ${APP_PATH}"
    echo "请先运行 PyInstaller 构建应用"
    exit 1
fi

# 清理旧文件
echo "🧹 清理旧文件..."
rm -f "${PKG_NAME}"
rm -rf pkg_root pkg_scripts
echo "✓ 清理完成"
echo ""

# 创建安装目录结构
echo "📁 创建安装目录结构..."
mkdir -p pkg_root/Applications
mkdir -p pkg_scripts

# 复制应用到安装根目录
echo "📦 复制应用文件..."
ditto "${APP_PATH}" "pkg_root/Applications/${APP_NAME}.app"
echo "✓ 应用文件复制完成"
echo ""

# 创建安装后脚本
echo "📝 创建安装脚本..."
cat > pkg_scripts/postinstall << 'EOF'
#!/bin/bash

echo "正在配置慧眼识鸟..."

# 确保应用有正确的权限
chmod -R 755 "/Applications/慧眼识鸟.app"

# 特别设置 exiftool 可执行权限（关键）
EXIFTOOL_PATH="/Applications/慧眼识鸟.app/Contents/Frameworks/exiftool_bundle/exiftool"
if [ -f "$EXIFTOOL_PATH" ]; then
    chmod +x "$EXIFTOOL_PATH"
    echo "✓ ExifTool 权限已设置"
fi

# 设置 exiftool lib 目录权限
LIB_DIR="/Applications/慧眼识鸟.app/Contents/Frameworks/exiftool_bundle/lib"
if [ -d "$LIB_DIR" ]; then
    chmod -R 755 "$LIB_DIR"
    echo "✓ ExifTool 库目录权限已设置"
fi

# 清除扩展属性（移除隔离标记）
xattr -cr "/Applications/慧眼识鸟.app" 2>/dev/null || true
echo "✓ 已移除隔离标记"

echo "✅ 慧眼识鸟 安装完成"
exit 0
EOF

chmod +x pkg_scripts/postinstall
echo "✓ 安装脚本创建完成"
echo ""

# 使用 pkgbuild 创建组件包
echo "🔨 构建组件包..."
pkgbuild --root pkg_root \
    --scripts pkg_scripts \
    --identifier "${IDENTIFIER}" \
    --version "${VERSION}" \
    --install-location "/" \
    "${APP_NAME}-component.pkg"
echo "✓ 组件包构建完成"
echo ""

# 创建 Distribution XML（用于自定义安装体验）
echo "📄 创建 Distribution 配置..."
cat > distribution.xml << EOF
<?xml version="1.0" encoding="utf-8"?>
<installer-gui-script minSpecVersion="1">
    <title>慧眼识鸟</title>
    <organization>com.superbirdid</organization>
    <domains enable_localSystem="true"/>
    <options customize="never" require-scripts="false" hostArchitectures="arm64,x86_64"/>

    <!-- 自定义界面样式 -->

    <!-- 定义背景和欢迎信息 -->
    <background file="icon.png" mime-type="image/png" alignment="bottomleft" scaling="none"/>
    <welcome file="welcome.html" mime-type="text/html"/>
    <license file="LICENSE.txt" mime-type="text/plain"/>
    <conclusion file="conclusion.html" mime-type="text/html"/>

    <!-- 选择项 -->
    <choices-outline>
        <line choice="default">
            <line choice="${IDENTIFIER}"/>
        </line>
    </choices-outline>

    <choice id="default"/>
    <choice id="${IDENTIFIER}" visible="false">
        <pkg-ref id="${IDENTIFIER}"/>
    </choice>

    <pkg-ref id="${IDENTIFIER}" version="${VERSION}" onConclusion="none">
        ${APP_NAME}-component.pkg
    </pkg-ref>
</installer-gui-script>
EOF
echo "✓ Distribution 配置创建完成"
echo ""

# 创建欢迎和结束页面
echo "📝 创建安装界面文本..."
cat > welcome.html << 'EOF'
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
            padding: 20px;
            line-height: 1.6;
            background-color: #ffffff;
            color: #000000;
        }
        h1 { color: #2c3e50; }
        h2 { color: #34495e; }
        h3 { color: #34495e; }
        .version { color: #7f8c8d; font-size: 0.9em; }
        ul { padding-left: 20px; }
        li { margin: 8px 0; color: #000000; }
        p { color: #000000; }
        .highlight { color: #3498db; font-weight: bold; }
    </style>
</head>
<body>
    <h1>欢迎安装慧眼识鸟 SuperBirdID</h1>
    <p class="version">版本 1.0.2</p>

    <p>本安装程序将在您的计算机上安装 <strong>慧眼识鸟 SuperBirdID</strong>。</p>

    <h2>关于慧眼识鸟</h2>
    <p><strong>慧眼识鸟 SuperBirdID</strong> 是一款基于人工智能的专业鸟类识别软件，为摄影爱好者和鸟类观察者提供强大的自动识别功能。</p>

    <h3>主要功能：</h3>
    <ul>
        <li><span class="highlight">AI 智能识别</span> - 采用 YOLO11 深度学习模型，准确检测和识别鸟类</li>
        <li><span class="highlight">RAW 格式支持</span> - 支持主流相机 RAW 格式（NEF、CR2、ARW、DNG 等）</li>
        <li><span class="highlight">EXIF 元数据</span> - 自动写入鸟类名称和关键词到照片元数据</li>
        <li><span class="highlight">eBird 集成</span> - 基于 GPS 位置查询当地鸟类观察记录</li>
        <li><span class="highlight">批量处理</span> - 支持拖拽多张照片批量识别</li>
    </ul>

    <h3>系统要求：</h3>
    <ul>
        <li>macOS 11.0 或更高版本</li>
        <li>支持 Apple Silicon (M1/M2/M3/M4) 和 Intel 处理器</li>
        <li>至少 4GB 可用磁盘空间</li>
        <li>建议 8GB 或以上内存</li>
    </ul>

    <p>点击"继续"开始安装过程。</p>
</body>
</html>
EOF

cat > conclusion.html << 'EOF'
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
            padding: 20px;
            line-height: 1.6;
            background-color: #ffffff;
            color: #000000;
        }
        h1 { color: #27ae60; }
        h2 { color: #34495e; }
        p { color: #000000; }
        strong { color: #000000; }
        ul { color: #000000; }
        li { color: #000000; }
        .success {
            background-color: #d4edda;
            border: 1px solid #c3e6cb;
            padding: 15px;
            border-radius: 5px;
            margin: 20px 0;
            color: #155724;
        }
        .success strong {
            color: #155724;
        }
        .info-box {
            background-color: #f8f9fa;
            border-left: 4px solid #3498db;
            padding: 15px;
            margin: 15px 0;
            color: #000000;
        }
        .info-box p {
            color: #000000;
        }
        .info-box strong {
            color: #000000;
        }
        .warning {
            background-color: #fff3cd;
            border-left: 4px solid #ffc107;
            padding: 15px;
            margin: 15px 0;
            color: #856404;
        }
        .warning p {
            color: #856404;
        }
        .warning strong {
            color: #856404;
        }
        a { color: #3498db; text-decoration: none; }
        a:hover { text-decoration: underline; }
    </style>
</head>
<body>
    <h1>✓ 安装成功</h1>

    <div class="success">
        <strong>慧眼识鸟 SuperBirdID v1.0.2</strong> 已成功安装到您的应用程序文件夹。
    </div>

    <h2>开始使用</h2>
    <div class="info-box">
        <p><strong>启动应用：</strong></p>
        <ul>
            <li>从"启动台"中找到并点击"慧眼识鸟"图标</li>
            <li>或者前往"应用程序"文件夹双击启动</li>
        </ul>

        <p><strong>首次启动：</strong></p>
        <ul>
            <li>macOS 可能会显示安全提示，请点击"打开"确认</li>
            <li>如果无法打开，请前往"系统偏好设置 > 安全性与隐私"允许运行</li>
        </ul>
    </div>

    <div class="warning">
        <p><strong>⚠️ 重要提示：</strong></p>
        <ul>
            <li>首次运行时，AI 模型加载可能需要 10-30 秒，请耐心等待</li>
            <li>识别功能需要网络连接以获取 eBird 数据（可选）</li>
            <li>建议使用带 GPS 信息的照片以获得更准确的识别结果</li>
        </ul>
    </div>

    <h2>获取帮助</h2>
    <p>如需帮助或报告问题，请访问：</p>
    <ul>
        <li>项目主页：<a href="https://github.com/jameszhenyu/SuperBirdID">https://github.com/jameszhenyu/SuperBirdID</a></li>
        <li>问题反馈：<a href="https://github.com/jameszhenyu/SuperBirdID/issues">GitHub Issues</a></li>
    </ul>

    <p style="margin-top: 30px; color: #7f8c8d; font-size: 0.9em;">
        感谢使用慧眼识鸟 SuperBirdID！祝您拍摄愉快！🐦
    </p>
</body>
</html>
EOF

# 创建详细的许可证文件
cat > LICENSE.txt << 'EOF'
慧眼识鸟 SuperBirdID 软件许可协议
Software License Agreement

版本 1.0.2
最后更新：2025年10月

重要提示：请在安装或使用本软件之前仔细阅读本协议。

========================================
1. 许可授予
========================================

慧眼识鸟 SuperBirdID（以下简称"本软件"）是一款免费软件。在遵守本协议条款的前提下，
版权所有者授予您非排他性、不可转让的免费许可，允许您：

• 在个人或商业用途中使用本软件
• 在任意数量的设备上安装和运行本软件
• 制作本软件的备份副本

========================================
2. 免责声明
========================================

本软件按"原样"提供，不附带任何明示或暗示的保证，包括但不限于：

• 适销性保证
• 特定用途适用性保证
• 不侵权保证
• 准确性或可靠性保证

版权所有者和贡献者明确声明：

1) 识别结果：本软件提供的鸟类识别结果仅供参考，不保证其准确性。
   用户应当结合专业知识和其他资料进行验证。

2) 数据安全：本软件会处理您的照片文件，但不会上传或共享您的照片。
   eBird 数据查询需要网络连接，但仅传输 GPS 坐标信息。

3) 文件损坏：虽然本软件在设计时已考虑文件安全，但版权所有者不对
   因使用本软件导致的任何文件损坏或数据丢失负责。

4) 系统影响：版权所有者不对本软件对您的计算机系统可能造成的任何
   影响负责。

========================================
3. 责任限制
========================================

在任何情况下，版权所有者或贡献者均不对以下情况承担责任：

• 任何直接、间接、偶然、特殊、惩罚性或后果性损害
• 利润损失、数据丢失或业务中断
• 因使用或无法使用本软件而产生的任何损害

即使已被告知此类损害的可能性，上述免责条款仍然适用。

某些司法管辖区不允许排除或限制附带或后果性损害的责任，
因此上述限制可能不适用于您。

========================================
4. 知识产权
========================================

本软件及其所有副本的版权归版权所有者所有。本软件受版权法和
国际条约保护。

本软件使用的第三方库和模型：
• PyTorch - BSD License
• Ultralytics YOLO - AGPL-3.0 License
• eBird API - eBird Terms of Use
• ExifTool - Artistic License / GPL

========================================
5. 使用限制
========================================

您不得：
• 逆向工程、反编译或反汇编本软件（法律明确允许的范围除外）
• 移除或修改本软件中的任何版权声明或其他权利声明
• 将本软件用于非法目的

========================================
6. 终止
========================================

如果您违反本协议的任何条款，您使用本软件的许可将自动终止。
终止时，您必须销毁本软件的所有副本。

========================================
7. 完整协议
========================================

本协议构成您与版权所有者之间关于本软件的完整协议，
并取代所有先前或同期的口头或书面协议。

========================================
8. 法律适用
========================================

本协议受您所在司法管辖区的法律管辖。

========================================

版权所有 © 2025 慧眼识鸟 SuperBirdID Project
保留所有权利。

通过安装或使用本软件，您表示已阅读、理解并同意受本协议条款的约束。
如果您不同意本协议的任何条款，请不要安装或使用本软件。

EOF

echo "✓ 安装界面文本创建完成"
echo ""

# 使用 productbuild 创建最终的 PKG（包含自定义界面）
echo "🎁 创建最终安装包..."
productbuild --distribution distribution.xml \
    --resources . \
    --package-path . \
    "${PKG_NAME}"
echo "✓ 最终安装包创建完成"
echo ""

# 清理临时文件
echo "🧹 清理临时文件..."
rm -rf pkg_root pkg_scripts
rm -f "${APP_NAME}-component.pkg" distribution.xml welcome.html conclusion.html
echo "✓ 清理完成"
echo ""

# 显示文件信息
echo "📊 安装包信息:"
ls -lh "${PKG_NAME}"
echo ""

echo "✅ PKG 安装包创建完成: ${PKG_NAME}"
echo ""
echo "📝 下一步："
echo "1. 测试安装: sudo installer -pkg ${PKG_NAME} -target /"
echo "2. 签名（可选）: productsign --sign \"Developer ID Installer: Your Name\" ${PKG_NAME} ${PKG_NAME/.pkg/-signed.pkg}"
echo "3. 验证签名: pkgutil --check-signature ${PKG_NAME/.pkg/-signed.pkg}"
echo ""
