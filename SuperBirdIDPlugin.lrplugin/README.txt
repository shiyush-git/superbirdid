╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║        SuperBirdID Lightroom Plugin v3.1.0                    ║
║        慧眼识鸟 Lightroom 插件                                ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝

📦 安装方法一：通过 Lightroom 插件管理器（推荐）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. 打开 Adobe Lightroom Classic
2. 菜单栏 → 文件 → 增效工具管理器
3. 点击左下角"添加"按钮
4. 选择此文件夹：SuperBirdIDPlugin.lrplugin
5. 点击"添加增效工具"
6. 确认插件状态为"已启用"

✅ 完成！


📦 安装方法二：手动复制（备用）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

将整个 SuperBirdIDPlugin.lrplugin 文件夹复制到：

macOS:
~/Library/Application Support/Adobe/Lightroom/Modules/

然后重启 Lightroom Classic


📂 常见 Lightroom 插件目录
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

macOS:
  • Lightroom Classic:
    ~/Library/Application Support/Adobe/Lightroom/Modules/

  • Lightroom CC (旧版):
    ~/Library/Application Support/Adobe/Lightroom CC/Modules/

Windows:
  • Lightroom Classic:
    C:\Users\[用户名]\AppData\Roaming\Adobe\Lightroom\Modules\

  • Lightroom CC (旧版):
    C:\Users\[用户名]\AppData\Roaming\Adobe\Lightroom CC\Modules\


⚙️ 使用前准备
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚠️ 重要：使用插件前，必须先启动"慧眼识鸟"主程序！

1. 启动慧眼识鸟.app
2. 确认窗口底部显示"✅ API 已启动"
3. 在 GUI 中设置您的常用拍摄国家/地区
4. 然后在 Lightroom 中使用插件识别鸟类


🎯 使用方法
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. 在 Lightroom 中选择一张鸟类照片
2. 右键 → 导出 → 选择 "SuperBirdID"
3. 或：文件 → 导出 → 导出预设 → SuperBirdID
4. 等待识别完成
5. 查看结果，确认是否保存到 EXIF


📊 插件设置（推荐配置）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

在 Lightroom 导出对话框中：

  • API 地址: http://127.0.0.1:5156
  • 返回结果数: 3
  • ✅ 启用 YOLO 检测
  • ✅ 启用 GPS 定位
  • ✅ 自动写入 EXIF


✨ v3.1.0 新特性
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎯 智能地理筛选
  • 有 GPS 的照片：自动使用拍摄地 25km 范围内的鸟类列表
  • 无 GPS 的照片：使用主程序中设置的国家/地区
  • 识别结果更准确，减少误报

🔄 结果一致性
  • Lightroom 插件识别结果现在与 GUI 完全一致
  • 不再显示不可能在当地出现的鸟类


🐛 常见问题
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Q: 提示"无法连接到 API"？
A: 请确保慧眼识鸟主程序已启动，API 状态为"已启动"

Q: 识别结果为空？
A: 可能所有结果都被地理筛选过滤了，请尝试：
   1. 检查主程序中的国家/地区设置
   2. 关闭"启用 eBird 地理筛选"
   3. 切换到"全球模式"

Q: 插件安装后 Lightroom 看不到？
A: 1. 确认插件目录正确
   2. 重启 Lightroom Classic
   3. 检查插件管理器中是否已启用

Q: 识别速度慢？
A: 首次识别需要加载 AI 模型（约 10-20 秒），之后会很快


📞 技术支持
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

GitHub Issues: https://github.com/yourusername/SuperBirdID/issues
详细文档: 查看 DMG 中的"安装说明"文件夹


📄 文件说明
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SuperBirdIDPlugin.lrplugin/
  ├── Info.lua                              # 插件信息
  ├── PluginInit.lua                        # 插件初始化
  ├── SuperBirdIDExportServiceProvider.lua  # 导出服务
  └── README.txt                            # 本文件


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
版本: v3.1.0
更新日期: 2025-01-XX
兼容: Lightroom Classic CC 2015+
许可: MIT License
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

祝您识鸟愉快！🐦
