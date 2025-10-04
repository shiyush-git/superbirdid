#!/usr/bin/env python3
"""
SuperBirdID - 简化GUI版本
极简设计，一键识别，卡片式结果展示
"""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkinter import font as tkfont
from PIL import Image, ImageTk, ImageDraw
import threading
import os
import sys
from pathlib import Path
import queue

# 可选的拖放支持
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    DRAG_DROP_AVAILABLE = True
except ImportError:
    DRAG_DROP_AVAILABLE = False

# 导入核心识别模块
from SuperBirdId import (
    load_image, lazy_load_classifier, lazy_load_bird_info,
    lazy_load_database, extract_gps_from_exif, get_region_from_gps,
    YOLOBirdDetector, YOLO_AVAILABLE, EBIRD_FILTER_AVAILABLE,
    RAW_SUPPORT, script_dir
)

# 导入eBird过滤器
if EBIRD_FILTER_AVAILABLE:
    from ebird_country_filter import eBirdCountryFilter

# JSON导入用于读取离线数据
import json


class SuperBirdIDGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("SuperBirdID - AI 鸟类智能识别系统")

        # 获取屏幕尺寸并设置窗口大小为屏幕的80%
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        window_width = int(screen_width * 0.8)
        window_height = int(screen_height * 0.85)

        # 居中显示
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")

        self.root.resizable(True, True)
        self.root.minsize(900, 600)  # 降低最小尺寸以适应更多设备

        # 保存图标引用防止被垃圾回收
        self.window_icon = None

        # 设置窗口图标 (如果存在icon文件)
        try:
            icon_path = os.path.join(os.path.dirname(__file__), 'icon.png')
            if os.path.exists(icon_path):
                # macOS 和 Windows 支持
                icon_img = Image.open(icon_path)
                self.window_icon = ImageTk.PhotoImage(icon_img)
                self.root.iconphoto(True, self.window_icon)
        except Exception as e:
            pass  # 图标加载失败不影响程序运行

        # 现代化暗色主题配色方案
        self.colors = {
            # 背景色系 - 深色渐变
            'bg': '#0f1419',           # 主背景 - 深蓝灰
            'bg_secondary': '#1a1f2e', # 次级背景
            'card': '#1e2432',         # 卡片背景 - 略亮
            'card_hover': '#252b3b',   # 卡片悬停

            # 主色调 - 高对比度蓝色
            'primary': '#60a5fa',      # 主色 - 更亮的蓝（提高对比度）
            'primary_hover': '#3b82f6', # 悬停
            'primary_light': '#93c5fd', # 浅色

            # 功能色 - 高饱和度
            'success': '#10b981',      # 成功 - 翡翠绿
            'success_light': '#34d399', # 成功浅色
            'success_bg': '#064e3b',   # 成功背景

            'warning': '#f59e0b',      # 警告 - 琥珀色
            'warning_light': '#fbbf24',
            'warning_bg': '#78350f',

            'bronze': '#f97316',       # 铜色 - 橙色系
            'bronze_light': '#fb923c',
            'bronze_bg': '#7c2d12',

            'error': '#ef4444',        # 错误 - 红色
            'error_light': '#f87171',

            # 文字色系 - 高对比度
            'text': '#f9fafb',         # 主文字 - 几乎白色
            'text_secondary': '#9ca3af', # 次要文字 - 灰色
            'text_dim': '#6b7280',     # 暗淡文字

            # 边框和分隔
            'border': '#374151',       # 边框 - 深灰
            'border_light': '#4b5563', # 浅边框
            'divider': '#2d3748',      # 分隔线

            # 强调色
            'accent': '#6366f1',       # 强调 - 靛蓝
            'accent_light': '#818cf8',

            # 特殊
            'overlay': 'rgba(15, 20, 25, 0.8)',  # 遮罩
            'shadow': 'rgba(0, 0, 0, 0.5)',      # 阴影
        }

        self.root.configure(bg=self.colors['bg'])

        # 变量
        self.current_image_path = None
        self.current_image = None
        self.current_photo = None
        self.recognition_results = []
        self.progress_queue = queue.Queue()
        self.is_processing = False

        # 动画相关
        self.loading_animation_running = False
        self.loading_dots = 0

        # 配置变量（默认全部启用，隐藏在高级选项中）
        self.use_yolo = tk.BooleanVar(value=True)
        self.use_gps = tk.BooleanVar(value=True)
        self.use_ebird = tk.BooleanVar(value=True)
        self.show_advanced = tk.BooleanVar(value=False)

        # 国家选择
        self.selected_country = tk.StringVar(value="自动检测")
        self.country_list = self.load_available_countries()

        # 温度参数选择
        self.temperature = tk.DoubleVar(value=0.5)  # 默认0.5
        # self.show_temp_comparison = tk.BooleanVar(value=False)  # 已移除温度对比功能

        # 创建界面
        self.setup_fonts()
        self.create_main_layout()

        # 启用拖放（如果可用）
        if DRAG_DROP_AVAILABLE:
            try:
                self.root.drop_target_register(DND_FILES)
                self.root.dnd_bind('<<Drop>>', self.on_drop)
            except:
                pass

        # 绑定键盘快捷键
        self._setup_keyboard_shortcuts()

        # 启动进度检查
        self.check_progress()

        # 注册清理函数
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def _setup_keyboard_shortcuts(self):
        """设置键盘快捷键"""
        import platform
        is_macos = platform.system() == 'Darwin'

        # Ctrl+V / Cmd+V - 粘贴
        self.root.bind_all('<Control-v>', lambda e: self.paste_from_clipboard())
        if is_macos:
            self.root.bind_all('<Command-v>', lambda e: self.paste_from_clipboard())
            self.root.bind_all('<Mod1-v>', lambda e: self.paste_from_clipboard())

        # Ctrl+O / Cmd+O - 打开文件
        self.root.bind_all('<Control-o>', lambda e: self.open_image())
        if is_macos:
            self.root.bind_all('<Command-o>', lambda e: self.open_image())

        # Return/Enter - 开始识别
        self.root.bind('<Return>', lambda e: self.start_recognition() if self.current_image_path and not self.is_processing else None)
        self.root.bind('<KP_Enter>', lambda e: self.start_recognition() if self.current_image_path and not self.is_processing else None)

        # Escape - 切换高级选项
        self.root.bind('<Escape>', lambda e: self.toggle_advanced())

    def load_available_countries(self):
        """加载可用的国家列表"""
        countries = {"自动检测": None, "全球模式": None}

        try:
            offline_index_path = os.path.join(script_dir, "offline_ebird_data", "offline_index.json")
            if os.path.exists(offline_index_path):
                with open(offline_index_path, 'r', encoding='utf-8') as f:
                    offline_index = json.load(f)
                    available_countries = offline_index.get('countries', {})

                # 国家代码到中文名称的映射
                country_names = {
                    'AU': '澳大利亚', 'CN': '中国', 'US': '美国', 'CA': '加拿大',
                    'BR': '巴西', 'IN': '印度', 'ID': '印度尼西亚', 'MX': '墨西哥',
                    'CO': '哥伦比亚', 'PE': '秘鲁', 'EC': '厄瓜多尔', 'BO': '玻利维亚',
                    'VE': '委内瑞拉', 'CL': '智利', 'AR': '阿根廷', 'ZA': '南非',
                    'KE': '肯尼亚', 'TZ': '坦桑尼亚', 'MG': '马达加斯加', 'CM': '喀麦隆',
                    'GH': '加纳', 'NG': '尼日利亚', 'ET': '埃塞俄比亚', 'UG': '乌干达',
                    'CR': '哥斯达黎加', 'PA': '巴拿马', 'GT': '危地马拉', 'NI': '尼加拉瓜',
                    'HN': '洪都拉斯', 'BZ': '伯利兹', 'SV': '萨尔瓦多', 'NO': '挪威',
                    'SE': '瑞典', 'FI': '芬兰', 'GB': '英国', 'FR': '法国',
                    'ES': '西班牙', 'IT': '意大利', 'DE': '德国', 'PL': '波兰',
                    'RO': '罗马尼亚', 'TR': '土耳其', 'RU': '俄罗斯', 'JP': '日本',
                    'KR': '韩国', 'TH': '泰国', 'VN': '越南', 'PH': '菲律宾',
                    'MY': '马来西亚', 'SG': '新加坡', 'NZ': '新西兰'
                }

                # 添加所有可用国家
                for code, data in sorted(available_countries.items()):
                    cn_name = country_names.get(code, code)
                    display_name = f"{cn_name} ({code})"
                    countries[display_name] = code

        except Exception:
            pass

        return countries

    def setup_fonts(self):
        """设置字体"""
        self.fonts = {
            'title': tkfont.Font(family='SF Pro Display', size=24, weight='bold'),
            'heading': tkfont.Font(family='SF Pro Display', size=16, weight='bold'),
            'body': tkfont.Font(family='SF Pro Text', size=13),
            'small': tkfont.Font(family='SF Pro Text', size=11),
            'button': tkfont.Font(family='SF Pro Display', size=14, weight='bold'),
        }

    def _on_mousewheel(self, event):
        """处理鼠标滚轮事件"""
        if event.num == 5 or event.delta < 0:
            # 向下滚动
            self.canvas.yview_scroll(1, "units")
        elif event.num == 4 or event.delta > 0:
            # 向上滚动
            self.canvas.yview_scroll(-1, "units")

    def on_drop(self, event):
        """处理文件拖放"""
        files = self.root.tk.splitlist(event.data)
        if files:
            self.load_image(files[0])

    def paste_from_clipboard(self):
        """从剪贴板粘贴图片"""
        try:
            # 尝试从剪贴板获取图片
            from PIL import ImageGrab

            clipboard_image = ImageGrab.grabclipboard()

            if clipboard_image is None:
                # 检查是否是文件路径
                try:
                    clipboard_text = self.root.clipboard_get()
                    if clipboard_text and os.path.isfile(clipboard_text):
                        # 是文件路径，直接加载
                        self.load_image(clipboard_text)
                        return
                except (tk.TclError, OSError):
                    pass

                messagebox.showinfo("提示", "剪贴板中没有图片\n\n请先复制图片后再粘贴")
                return

            # 如果是图片，保存到临时文件
            import tempfile

            # 清理之前的临时文件（如果存在）
            if hasattr(self, '_temp_clipboard_file') and os.path.exists(self._temp_clipboard_file):
                try:
                    os.unlink(self._temp_clipboard_file)
                except OSError:
                    pass

            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
            temp_path = temp_file.name
            clipboard_image.save(temp_path, 'PNG')
            temp_file.close()

            # 保存临时文件路径用于后续清理
            self._temp_clipboard_file = temp_path

            # 加载临时图片
            self.current_image_path = temp_path
            self.current_image = clipboard_image

            # 隐藏占位符，显示图片
            self.upload_placeholder.pack_forget()
            self.image_label.pack()

            # 显示图片
            self.display_image(clipboard_image)

            # 更新信息
            img_size = clipboard_image.size
            info_text = f"✓ 来自剪贴板 · {img_size[0]}x{img_size[1]} · PNG"
            self.info_label.config(text=info_text, fg=self.colors['text_secondary'])
            self.update_status(f"✓ 已粘贴图片")

            # 清空之前的结果
            self.clear_results()

        except ImportError:
            messagebox.showerror("错误", "PIL.ImageGrab 模块不可用\n无法使用剪贴板功能")
        except OSError as e:
            messagebox.showerror("错误", f"保存临时文件失败:\n{e}")
        except Exception as e:
            messagebox.showerror("错误", f"粘贴失败:\n{e}")

    def create_main_layout(self):
        """创建主布局 - 左右分栏布局"""
        # 主滚动容器
        self.canvas = tk.Canvas(self.root, bg=self.colors['bg'], highlightthickness=0)
        scrollbar = tk.Scrollbar(self.root, orient='vertical', command=self.canvas.yview)
        scrollable_frame = tk.Frame(self.canvas, bg=self.colors['bg'])

        scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)

        # 绑定鼠标滚轮事件
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)  # Windows/macOS
        self.canvas.bind_all("<Button-4>", self._on_mousewheel)    # Linux scroll up
        self.canvas.bind_all("<Button-5>", self._on_mousewheel)    # Linux scroll down

        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # 顶部标题
        self.create_header(scrollable_frame)

        # 图片上传区域
        self.create_upload_area(scrollable_frame)

        # 操作按钮
        self.create_action_buttons(scrollable_frame)

        # 结果展示区
        self.create_results_area(scrollable_frame)

        # 高级选项（折叠）
        self.create_advanced_options(scrollable_frame)

        # 底部状态栏
        self.create_status_bar()

    def create_header(self, parent):
        """创建顶部标题"""
        header = tk.Frame(parent, bg=self.colors['bg'])
        header.pack(pady=(25, 20))

        # Logo和标题行
        title_row = tk.Frame(header, bg=self.colors['bg'])
        title_row.pack()

        # Logo图标
        try:
            icon_path = os.path.join(os.path.dirname(__file__), 'icon.png')
            if os.path.exists(icon_path):
                logo_img = Image.open(icon_path)
                logo_img = logo_img.resize((48, 48), Image.Resampling.LANCZOS)
                logo_photo = ImageTk.PhotoImage(logo_img)
                logo_label = tk.Label(title_row, image=logo_photo, bg=self.colors['bg'])
                logo_label.image = logo_photo  # 保持引用
                logo_label.pack(side=tk.LEFT, padx=(0, 12))
        except:
            pass

        # 标题和副标题容器
        title_text_frame = tk.Frame(title_row, bg=self.colors['bg'])
        title_text_frame.pack(side=tk.LEFT)

        # 主标题和数据库信息在同一行
        title_line = tk.Frame(title_text_frame, bg=self.colors['bg'])
        title_line.pack(anchor='w')

        title = tk.Label(title_line, text="SuperBirdID",
                        font=tkfont.Font(family='SF Pro Display', size=28, weight='bold'),
                        fg=self.colors['text'],
                        bg=self.colors['bg'])
        title.pack(side=tk.LEFT)

        db_info = tk.Label(title_line, text="  ·  10,964 种鸟类",
                          font=tkfont.Font(family='SF Pro Text', size=13),
                          fg=self.colors['text_secondary'],
                          bg=self.colors['bg'])
        db_info.pack(side=tk.LEFT)

        # 副标题
        subtitle = tk.Label(title_text_frame, text="AI 鸟类智能识别系统",
                           font=tkfont.Font(family='SF Pro Text', size=14),
                           fg=self.colors['text_secondary'],
                           bg=self.colors['bg'])
        subtitle.pack(anchor='w', pady=(4, 0))

    def create_upload_area(self, parent):
        """创建图片上传/显示区域"""
        card = tk.Frame(parent, bg=self.colors['card'],
                       relief='flat', bd=0)
        card.pack(padx=40, pady=20, fill=tk.BOTH, expand=True)

        # 添加边框
        card.configure(highlightbackground=self.colors['border'],
                      highlightthickness=2,
                      relief='solid',
                      borderwidth=0)

        # 图片显示区 - 自适应大小
        self.image_container = tk.Frame(card, bg=self.colors['card'])
        self.image_container.pack(padx=30, pady=30, fill=tk.BOTH, expand=True)

        # 默认占位符 - 暗色主题设计
        self.upload_placeholder = tk.Frame(self.image_container,
                                          bg=self.colors['card'],
                                          relief='solid',
                                          bd=0,
                                          height=400)  # 设置最小高度
        self.upload_placeholder.pack(fill=tk.BOTH, expand=True)
        self.upload_placeholder.configure(highlightbackground=self.colors['border_light'],
                                         highlightthickness=2,
                                         borderwidth=0)

        placeholder_content = tk.Frame(self.upload_placeholder, bg=self.colors['card'])
        placeholder_content.place(relx=0.5, rely=0.5, anchor='center')

        # 图标背景圆 - 暗色主题
        icon_bg = tk.Frame(placeholder_content, bg=self.colors['bg_secondary'],
                          width=120, height=120)
        icon_bg.pack()
        icon_bg.pack_propagate(False)

        icon = tk.Label(icon_bg, text="📸",
                       font=tkfont.Font(size=56),
                       bg=self.colors['bg_secondary'])
        icon.place(relx=0.5, rely=0.5, anchor='center')

        text1 = tk.Label(placeholder_content,
                        text="将鸟类照片拖放到这里",
                        font=tkfont.Font(family='SF Pro Display', size=18, weight='bold'),
                        fg=self.colors['text'],
                        bg=self.colors['card'])
        text1.pack(pady=(25, 8))

        text2 = tk.Label(placeholder_content,
                        text='点击"选择图片"或按 Ctrl+V 粘贴',
                        font=self.fonts['body'],
                        fg=self.colors['text_secondary'],
                        bg=self.colors['card'])
        text2.pack(pady=(0, 15))

        # 分隔线 - 暗色
        separator = tk.Frame(placeholder_content, bg=self.colors['divider'],
                            height=1, width=200)
        separator.pack(pady=10)

        formats = tk.Label(placeholder_content,
                          text="✓ 支持: JPG · PNG · TIFF · RAW · 剪贴板",
                          font=tkfont.Font(family='SF Pro Text', size=11),
                          fg=self.colors['accent_light'],
                          bg=self.colors['card'])
        formats.pack(pady=(10, 0))

        # 点击上传
        self.upload_placeholder.bind('<Button-1>', lambda e: self.open_image())

        # 添加悬停效果
        def on_ph_enter(e):
            self.upload_placeholder.configure(bg=self.colors['card_hover'],
                                             highlightbackground=self.colors['primary'])
            placeholder_content.configure(bg=self.colors['card_hover'])
            text1.configure(bg=self.colors['card_hover'])
            text2.configure(bg=self.colors['card_hover'])
            formats.configure(bg=self.colors['card_hover'])
            icon_bg.configure(bg=self.colors['bg_secondary'])
            icon.configure(bg=self.colors['bg_secondary'])

        def on_ph_leave(e):
            self.upload_placeholder.configure(bg=self.colors['card'],
                                             highlightbackground=self.colors['border'])
            placeholder_content.configure(bg=self.colors['card'])
            text1.configure(bg=self.colors['card'])
            text2.configure(bg=self.colors['card'])
            formats.configure(bg=self.colors['card'])
            icon_bg.configure(bg=self.colors['bg_secondary'])
            icon.configure(bg=self.colors['bg_secondary'])

        self.upload_placeholder.bind('<Enter>', on_ph_enter)
        self.upload_placeholder.bind('<Leave>', on_ph_leave)

        # 图片标签（初始隐藏）
        self.image_label = tk.Label(self.image_container, bg=self.colors['card'])

        # 图片信息
        self.info_label = tk.Label(card, text="",
                                   font=self.fonts['small'],
                                   fg=self.colors['text_secondary'],
                                   bg=self.colors['card'])
        self.info_label.pack(pady=(0, 20))

    def create_action_buttons(self, parent):
        """创建操作按钮"""
        button_frame = tk.Frame(parent, bg=self.colors['bg'])
        button_frame.pack(pady=20)

        # 打开图片按钮 - 白色背景+黑色文字
        self.open_btn = tk.Button(button_frame,
                                  text="📁 选择图片",
                                  font=self.fonts['button'],
                                  bg='#ffffff',
                                  fg='#000000',
                                  activebackground='#f0f0f0',
                                  activeforeground='#000000',
                                  relief='solid',
                                  bd=2,
                                  padx=30, pady=15,
                                  cursor='hand2',
                                  command=self.open_image)
        self.open_btn.pack(side=tk.LEFT, padx=10)
        self.open_btn.configure(borderwidth=2,
                               relief='solid',
                               highlightbackground='#333333')

        # 识别按钮（主要操作） - 白色背景+黑色文字
        self.recognize_btn = tk.Button(button_frame,
                                       text="🔍 开始识别",
                                       font=tkfont.Font(family='SF Pro Display',
                                                       size=16, weight='bold'),
                                       bg='#ffffff',
                                       fg='#000000',
                                       activebackground='#f0f0f0',
                                       activeforeground='#000000',
                                       relief='solid',
                                       bd=2,
                                       padx=50, pady=18,
                                       cursor='hand2',
                                       command=self.start_recognition)
        self.recognize_btn.pack(side=tk.LEFT, padx=10)
        self.recognize_btn.configure(borderwidth=2,
                                    relief='solid',
                                    highlightbackground='#333333')

        # 高级选项按钮 - 白色背景+黑色文字
        self.advanced_btn = tk.Button(button_frame,
                                     text="⚙️ 高级选项",
                                     font=self.fonts['body'],
                                     bg='#ffffff',
                                     fg='#000000',
                                     activebackground='#f0f0f0',
                                     activeforeground='#000000',
                                     relief='solid',
                                     bd=2,
                                     padx=20, pady=15,
                                     cursor='hand2',
                                     command=self.toggle_advanced)
        self.advanced_btn.pack(side=tk.LEFT, padx=10)
        self.advanced_btn.configure(borderwidth=2,
                                   relief='solid',
                                   highlightbackground='#333333')

        # 悬停效果 - 统一的按钮悬停处理函数
        def create_button_hover_handlers(button, is_primary=False):
            """创建按钮悬停效果处理器"""
            def on_enter(e):
                button.configure(bg='#e0e0e0', highlightbackground='#666666')

            def on_leave(e):
                # 主按钮在处理中时不恢复
                if is_primary and self.is_processing:
                    return
                button.configure(bg='#ffffff', highlightbackground='#333333')

            return on_enter, on_leave

        # 绑定悬停效果
        enter_primary, leave_primary = create_button_hover_handlers(self.recognize_btn, is_primary=True)
        enter_open, leave_open = create_button_hover_handlers(self.open_btn)
        enter_adv, leave_adv = create_button_hover_handlers(self.advanced_btn)

        self.recognize_btn.bind('<Enter>', enter_primary)
        self.recognize_btn.bind('<Leave>', leave_primary)
        self.open_btn.bind('<Enter>', enter_open)
        self.open_btn.bind('<Leave>', leave_open)
        self.advanced_btn.bind('<Enter>', enter_adv)
        self.advanced_btn.bind('<Leave>', leave_adv)

    def create_results_area(self, parent):
        """创建结果展示区域 - 优化的卡片式布局（横排三个一行）"""
        self.results_container = tk.Frame(parent, bg=self.colors['bg'])
        self.results_container.pack(padx=20, pady=20, fill=tk.BOTH, expand=True)

        # 结果标题（初始隐藏）
        self.results_title = tk.Label(self.results_container,
                                      text="🎯 识别结果",
                                      font=self.fonts['heading'],
                                      fg=self.colors['text'],
                                      bg=self.colors['bg'])

        # GPS信息（放在标题下方）
        self.gps_info_frame = tk.Frame(self.results_container, bg=self.colors['bg'])
        self.gps_info_label = tk.Label(self.gps_info_frame,
                                       text="",
                                       font=self.fonts['small'],
                                       fg=self.colors['accent'],
                                       bg=self.colors['bg'])

        # 结果卡片容器（横排布局）
        self.result_cards_frame = tk.Frame(self.results_container,
                                          bg=self.colors['bg'])

    def create_result_card_responsive(self, parent, rank, cn_name, en_name, confidence, ebird_match=False):
        """创建响应式结果卡片 - 返回卡片对象"""
        return self.create_result_card(parent, rank, cn_name, en_name, confidence, ebird_match)

    def create_result_card(self, parent, rank, cn_name, en_name, confidence, ebird_match=False):
        """创建单个结果卡片 - 紧凑横排设计"""
        # 根据排名选择颜色和样式 - 暗色主题
        if rank == 1:
            accent_color = self.colors['success']
            bg_color = self.colors['success_bg']
            medal = "🥇"
            rank_text = "第一名"
        elif rank == 2:
            accent_color = self.colors['primary']
            bg_color = self.colors['bg_secondary']
            medal = "🥈"
            rank_text = "第二名"
        else:
            accent_color = self.colors['bronze']
            bg_color = self.colors['bronze_bg']
            medal = "🥉"
            rank_text = "第三名"

        # 主卡片容器（不使用pack，由调用者使用grid布局）
        card = tk.Frame(parent, bg=self.colors['card'], relief='solid', bd=2)
        card.configure(highlightbackground=accent_color,
                      highlightthickness=0,
                      borderwidth=2,
                      relief='solid')

        # 顶部彩色条
        top_bar = tk.Frame(card, bg=accent_color, height=6)
        top_bar.pack(fill=tk.X)

        # 内容区域
        content = tk.Frame(card, bg=self.colors['card'])
        content.pack(fill=tk.BOTH, expand=True, padx=20, pady=18)

        # 标题行：排名和奖牌
        header = tk.Frame(content, bg=self.colors['card'])
        header.pack(fill=tk.X, pady=(0, 12))

        medal_label = tk.Label(header, text=medal,
                              font=tkfont.Font(size=28),
                              bg=self.colors['card'])
        medal_label.pack(side=tk.LEFT, padx=(0, 10))

        rank_badge = tk.Label(header, text=rank_text,
                             font=self.fonts['small'],
                             fg=accent_color,
                             bg=bg_color,
                             padx=12, pady=4)
        rank_badge.pack(side=tk.LEFT)

        # 鸟名区域
        names_frame = tk.Frame(content, bg=self.colors['card'])
        names_frame.pack(fill=tk.X, pady=(0, 15))

        # 中文名 - 更大更醒目
        cn_label = tk.Label(names_frame, text=cn_name,
                           font=tkfont.Font(family='SF Pro Display', size=20, weight='bold'),
                           fg=self.colors['text'],
                           bg=self.colors['card'],
                           anchor='w')
        cn_label.pack(fill=tk.X)

        # 英文名 - 斜体更优雅
        en_label = tk.Label(names_frame, text=en_name,
                           font=tkfont.Font(family='SF Pro Text', size=14, slant='italic'),
                           fg=self.colors['text_secondary'],
                           bg=self.colors['card'],
                           anchor='w')
        en_label.pack(fill=tk.X, pady=(5, 0))

        # eBird匹配标记
        if ebird_match:
            ebird_badge = tk.Label(names_frame,
                                  text="✓ eBird确认",
                                  font=self.fonts['small'],
                                  fg='white',
                                  bg=self.colors['success'],
                                  padx=8, pady=2)
            ebird_badge.pack(anchor='w', pady=(5, 0))

        # 置信度区域
        conf_container = tk.Frame(content, bg=self.colors['card'])
        conf_container.pack(fill=tk.X)

        # 置信度标签和百分比
        conf_header = tk.Frame(conf_container, bg=self.colors['card'])
        conf_header.pack(fill=tk.X, pady=(0, 8))

        conf_text = tk.Label(conf_header,
                            text="置信度",
                            font=self.fonts['small'],
                            fg=self.colors['text_secondary'],
                            bg=self.colors['card'])
        conf_text.pack(side=tk.LEFT)

        conf_value = tk.Label(conf_header,
                             text=f"{confidence:.2f}%",
                             font=tkfont.Font(family='SF Pro Display', size=16, weight='bold'),
                             fg=accent_color,
                             bg=self.colors['card'])
        conf_value.pack(side=tk.RIGHT)

        # 进度条 - 更精致的设计
        bar_container = tk.Frame(conf_container, bg=self.colors['bg_secondary'], height=12)
        bar_container.pack(fill=tk.X)
        bar_container.pack_propagate(False)

        # 动态计算进度条宽度
        bar_width_percent = min(confidence, 100) / 100

        # 创建渐变效果的进度条
        bar_fg = tk.Frame(bar_container, bg=accent_color, height=12)
        bar_fg.place(relx=0, rely=0, relwidth=bar_width_percent, relheight=1)

        # 添加悬停效果 - 暗色主题（优化版）
        def create_card_hover_effect():
            """创建卡片悬停效果"""
            widgets = [content, header, names_frame, conf_container, conf_header,
                      cn_label, en_label, conf_text, conf_value, medal_label]

            def on_enter(e):
                card.configure(bg=self.colors['card_hover'], highlightbackground=accent_color,
                              highlightthickness=2)
                for widget in widgets:
                    widget.configure(bg=self.colors['card_hover'])

            def on_leave(e):
                card.configure(bg=self.colors['card'], highlightthickness=0)
                for widget in widgets:
                    widget.configure(bg=self.colors['card'])

            return on_enter, on_leave

        enter_handler, leave_handler = create_card_hover_effect()
        card.bind('<Enter>', enter_handler)
        card.bind('<Leave>', leave_handler)

        # 返回卡片对象以便响应式布局使用
        return card

    def create_advanced_options(self, parent):
        """创建高级选项（可折叠）"""
        adv_frame = tk.Frame(parent, bg=self.colors['bg'])
        adv_frame.pack(padx=40, pady=(10, 20))

        # 选项容器（初始隐藏）
        self.advanced_container = tk.Frame(adv_frame, bg=self.colors['card'],
                                          relief='solid', bd=1)
        self.advanced_container.configure(highlightbackground=self.colors['border'],
                                         borderwidth=2)

        # 内容区域
        content = tk.Frame(self.advanced_container, bg=self.colors['card'])
        content.pack(padx=20, pady=15)

        option_title = tk.Label(content,
                               text="识别选项配置",
                               font=self.fonts['heading'],
                               fg=self.colors['text'],
                               bg=self.colors['card'])
        option_title.pack(anchor='w', pady=(0, 10))

        if YOLO_AVAILABLE:
            yolo_frame = tk.Frame(content, bg=self.colors['card'])
            yolo_frame.pack(fill=tk.X, pady=5)

            yolo_check = tk.Checkbutton(yolo_frame,
                                       text="✓ 启用 YOLO 智能鸟类检测",
                                       variable=self.use_yolo,
                                       font=self.fonts['body'],
                                       bg=self.colors['card'],
                                       fg=self.colors['text'],
                                       selectcolor=self.colors['card'])
            yolo_check.pack(anchor='w')

            yolo_desc = tk.Label(yolo_frame,
                               text="    自动裁剪图片中的鸟类区域，提高识别精度",
                               font=self.fonts['small'],
                               fg=self.colors['text_secondary'],
                               bg=self.colors['card'])
            yolo_desc.pack(anchor='w', pady=(2, 0))

        gps_frame = tk.Frame(content, bg=self.colors['card'])
        gps_frame.pack(fill=tk.X, pady=5)

        gps_check = tk.Checkbutton(gps_frame,
                                  text="✓ 启用 GPS 地理位置分析",
                                  variable=self.use_gps,
                                  font=self.fonts['body'],
                                  bg=self.colors['card'],
                                  fg=self.colors['text'],
                                  selectcolor=self.colors['card'])
        gps_check.pack(anchor='w')

        gps_desc = tk.Label(gps_frame,
                          text="    根据照片GPS信息优化识别结果",
                          font=self.fonts['small'],
                          fg=self.colors['text_secondary'],
                          bg=self.colors['card'])
        gps_desc.pack(anchor='w', pady=(2, 0))

        # eBird过滤选项
        if EBIRD_FILTER_AVAILABLE:
            ebird_frame = tk.Frame(content, bg=self.colors['card'])
            ebird_frame.pack(fill=tk.X, pady=10)

            ebird_check = tk.Checkbutton(ebird_frame,
                                        text="✓ 启用 eBird 地理过滤",
                                        variable=self.use_ebird,
                                        font=self.fonts['body'],
                                        bg=self.colors['card'],
                                        fg=self.colors['text'],
                                        selectcolor=self.colors['card'])
            ebird_check.pack(anchor='w')

            ebird_desc = tk.Label(ebird_frame,
                                 text="    根据国家/地区鸟类分布数据过滤结果",
                                 font=self.fonts['small'],
                                 fg=self.colors['text_secondary'],
                                 bg=self.colors['card'])
            ebird_desc.pack(anchor='w', pady=(2, 5))

            # 国家选择下拉菜单
            country_select_frame = tk.Frame(ebird_frame, bg=self.colors['card'])
            country_select_frame.pack(fill=tk.X, padx=20)

            country_label = tk.Label(country_select_frame,
                                    text="选择国家/地区:",
                                    font=self.fonts['small'],
                                    fg=self.colors['text'],
                                    bg=self.colors['card'])
            country_label.pack(side=tk.LEFT, padx=(0, 10))

            # 下拉菜单
            country_menu = ttk.Combobox(country_select_frame,
                                       textvariable=self.selected_country,
                                       values=list(self.country_list.keys()),
                                       state='readonly',
                                       width=30,
                                       font=self.fonts['small'])
            country_menu.pack(side=tk.LEFT)
            country_menu.set("自动检测")

        # 温度参数设置
        temp_frame = tk.Frame(content, bg=self.colors['card'])
        temp_frame.pack(fill=tk.X, pady=10)

        temp_label = tk.Label(temp_frame,
                             text="🌡️ 温度参数 (影响置信度分布)",
                             font=self.fonts['body'],
                             fg=self.colors['text'],
                             bg=self.colors['card'])
        temp_label.pack(anchor='w')

        temp_desc = tk.Label(temp_frame,
                            text="    较低温度=更自信的结果 | 较高温度=更保守的结果",
                            font=self.fonts['small'],
                            fg=self.colors['text_secondary'],
                            bg=self.colors['card'])
        temp_desc.pack(anchor='w', pady=(2, 5))

        # 温度选择控件
        temp_select_frame = tk.Frame(temp_frame, bg=self.colors['card'])
        temp_select_frame.pack(fill=tk.X, padx=20)

        temp_select_label = tk.Label(temp_select_frame,
                                     text="选择温度:",
                                     font=self.fonts['small'],
                                     fg=self.colors['text'],
                                     bg=self.colors['card'])
        temp_select_label.pack(side=tk.LEFT, padx=(0, 10))

        # 温度下拉菜单
        temp_options = ["0.4 (锐化)", "0.5 (推荐)", "0.6 (平衡)", "0.7 (保守)"]
        temp_values = [0.4, 0.5, 0.6, 0.7]

        temp_combo = ttk.Combobox(temp_select_frame,
                                 values=temp_options,
                                 state='readonly',
                                 width=15,
                                 font=self.fonts['small'])
        temp_combo.pack(side=tk.LEFT, padx=(0, 15))
        temp_combo.set("0.5 (推荐)")

        # 温度值改变时更新变量
        def on_temp_change(event):
            selected_idx = temp_combo.current()
            self.temperature.set(temp_values[selected_idx])

        temp_combo.bind('<<ComboboxSelected>>', on_temp_change)

        # 温度对比选项已移除，保持界面简洁

    def toggle_advanced(self):
        """切换高级选项显示"""
        if self.show_advanced.get():
            self.advanced_container.pack_forget()
            self.show_advanced.set(False)
        else:
            self.advanced_container.pack(fill=tk.X, pady=10)
            self.show_advanced.set(True)

    def create_status_bar(self):
        """创建状态栏"""
        status_frame = tk.Frame(self.root, bg=self.colors['card'], height=50,
                               relief='solid', bd=1)
        status_frame.pack(side=tk.BOTTOM, fill=tk.X)
        status_frame.pack_propagate(False)
        status_frame.configure(borderwidth=1,
                              highlightbackground=self.colors['border'],
                              highlightthickness=0)

        # 添加顶部分隔线
        top_line = tk.Frame(status_frame, bg=self.colors['border'], height=1)
        top_line.pack(side=tk.TOP, fill=tk.X)

        content = tk.Frame(status_frame, bg=self.colors['card'])
        content.pack(fill=tk.BOTH, expand=True)

        self.status_label = tk.Label(content, text="✓ 就绪",
                                     font=self.fonts['body'],
                                     fg=self.colors['text_secondary'],
                                     bg=self.colors['card'])
        self.status_label.pack(side=tk.LEFT, padx=25, pady=10)

        # 进度指示器
        self.progress_label = tk.Label(content, text="",
                                       font=self.fonts['body'],
                                       fg=self.colors['accent'],
                                       bg=self.colors['card'])
        self.progress_label.pack(side=tk.RIGHT, padx=25, pady=10)

    def open_image(self):
        """打开图片文件"""
        filetypes = [
            ("所有支持格式", "*.jpg *.jpeg *.png *.tiff *.bmp"),
            ("JPEG图片", "*.jpg *.jpeg"),
            ("PNG图片", "*.png"),
        ]

        if RAW_SUPPORT:
            filetypes.insert(0, ("RAW格式", "*.cr2 *.cr3 *.nef *.arw *.dng *.raf"))

        filename = filedialog.askopenfilename(
            title="选择图片",
            filetypes=filetypes
        )

        if filename:
            self.load_image(filename)

    def load_image(self, filepath):
        """加载并显示图片"""
        try:
            # 清理拖放路径（可能包含{}括号）
            if filepath.startswith('{') and filepath.endswith('}'):
                filepath = filepath[1:-1]

            # 验证文件存在
            if not os.path.exists(filepath):
                raise FileNotFoundError(f"文件不存在: {filepath}")

            # 验证文件可读
            if not os.access(filepath, os.R_OK):
                raise PermissionError(f"无权限读取文件: {filepath}")

            self.current_image_path = filepath

            # 使用核心加载函数
            self.current_image = load_image(filepath)

            # 验证图片加载成功
            if self.current_image is None:
                raise ValueError("图片加载失败，返回空对象")

            # 隐藏占位符，显示图片
            self.upload_placeholder.pack_forget()
            self.image_label.pack()

            # 显示在界面上
            self.display_image(self.current_image)

            # 更新信息
            file_size = os.path.getsize(filepath) / 1024 / 1024  # MB
            file_ext = os.path.splitext(filepath)[1].upper()
            info_text = f"✓ {os.path.basename(filepath)} · "
            info_text += f"{self.current_image.size[0]}x{self.current_image.size[1]} · "
            info_text += f"{file_ext[1:]} · {file_size:.2f} MB"

            self.info_label.config(text=info_text, fg=self.colors['text_secondary'])
            self.update_status(f"✓ 已加载图片")

            # 清空之前的结果
            self.clear_results()

        except FileNotFoundError as e:
            messagebox.showerror("文件错误", str(e))
        except PermissionError as e:
            messagebox.showerror("权限错误", str(e))
        except OSError as e:
            messagebox.showerror("系统错误", f"读取文件失败:\n{e}")
        except Exception as e:
            messagebox.showerror("错误", f"加载图片失败:\n{type(e).__name__}: {e}")

    def display_image(self, pil_image):
        """在界面上显示图片 - 自适应窗口大小（优化版）"""
        try:
            # 获取容器实际可用空间
            self.root.update_idletasks()  # 确保获取到正确的尺寸
            container_width = self.image_container.winfo_width()
            container_height = self.image_container.winfo_height()

            # 如果容器尺寸未初始化，使用窗口尺寸的百分比
            if container_width <= 1:
                container_width = int(self.root.winfo_width() * 0.7)
            if container_height <= 1:
                container_height = int(self.root.winfo_height() * 0.45)

            # 保持图片比例缩放（使用更高效的方法）
            img_copy = pil_image.copy()
            img_copy.thumbnail((container_width - 40, container_height - 40), Image.Resampling.LANCZOS)

            # 释放旧的PhotoImage引用
            if hasattr(self, 'current_photo') and self.current_photo:
                try:
                    del self.current_photo
                except Exception:
                    pass

            # 转换为PhotoImage
            self.current_photo = ImageTk.PhotoImage(img_copy)

            # 更新标签
            self.image_label.config(image=self.current_photo,
                                   relief='solid',
                                   bd=2,
                                   borderwidth=2)

        except Exception as e:
            # 如果显示失败，使用占位符
            self.image_label.pack_forget()
            self.upload_placeholder.pack(fill=tk.BOTH, expand=True)
            raise ValueError(f"图片显示失败: {e}")

    def clear_results(self):
        """清空结果显示"""
        self.results_title.pack_forget()
        self.gps_info_frame.pack_forget()
        self.gps_info_label.pack_forget()
        # 销毁所有结果卡片
        for widget in self.result_cards_frame.winfo_children():
            widget.destroy()
        self.result_cards_frame.pack_forget()

    def animate_loading(self):
        """加载动画效果"""
        if self.loading_animation_running:
            self.loading_dots = (self.loading_dots + 1) % 4
            dots = "." * self.loading_dots
            spaces = " " * (3 - self.loading_dots)
            self.recognize_btn.config(text=f"🔍 识别中{dots}{spaces}")
            self.root.after(400, self.animate_loading)

    def start_recognition(self):
        """开始识别（异步）"""
        if not self.current_image_path:
            messagebox.showwarning("提示", "请先选择一张鸟类照片")
            return

        if self.is_processing:
            return

        # 禁用按钮并启动动画
        self.is_processing = True
        self.loading_animation_running = True
        self.loading_dots = 0
        self.recognize_btn.config(state='disabled')
        self.open_btn.config(state='disabled')
        self.animate_loading()  # 启动加载动画

        # 清空结果
        self.clear_results()

        # 在后台线程运行识别
        thread = threading.Thread(target=self.run_recognition, daemon=True)
        thread.start()

    def run_recognition(self):
        """运行识别（后台线程）"""
        try:
            self.progress_queue.put(("progress", "🚀 启动AI识别引擎..."))

            # 加载组件
            model = lazy_load_classifier()
            bird_info = lazy_load_bird_info()
            db_manager = lazy_load_database()

            self.progress_queue.put(("progress", "🔬 智能分析图片特征..."))

            # GPS提取和eBird过滤准备
            lat, lon = None, None
            country_code = None
            ebird_species_set = None

            if self.use_gps.get():
                lat, lon, info = extract_gps_from_exif(self.current_image_path)
                if lat and lon:
                    region, country_code, region_info = get_region_from_gps(lat, lon)
                    self.progress_queue.put(("gps", region_info))

            # eBird过滤设置
            if self.use_ebird.get() and EBIRD_FILTER_AVAILABLE:
                try:
                    # 获取用户选择的国家
                    selected = self.selected_country.get()

                    # 如果是"自动检测"且有GPS，使用GPS国家代码
                    if selected == "自动检测":
                        if country_code:
                            pass  # 使用GPS检测到的country_code
                        else:
                            country_code = None  # 没有GPS，不使用过滤
                    # 如果是"全球模式"，不使用过滤
                    elif selected == "全球模式":
                        country_code = None
                    # 否则使用用户选择的国家
                    else:
                        country_code = self.country_list.get(selected)

                    # 如果有国家代码，加载eBird数据
                    if country_code:
                        self.progress_queue.put(("progress", f"🌍 加载 {country_code} 地区鸟类数据库..."))

                        EBIRD_API_KEY = "60nan25sogpo"
                        ebird_filter = eBirdCountryFilter(EBIRD_API_KEY, offline_dir="offline_ebird_data")
                        ebird_species_set = ebird_filter.get_country_species_list(country_code)

                        if ebird_species_set:
                            self.progress_queue.put(("progress", f"✅ 数据库加载完成 ({len(ebird_species_set)} 种鸟类)"))
                except Exception as e:
                    self.progress_queue.put(("progress", f"⚠️ 地区数据加载失败，使用全球数据库"))

            # YOLO检测
            processed_image = self.current_image

            if self.use_yolo.get() and YOLO_AVAILABLE:
                width, height = self.current_image.size
                if max(width, height) > 640:
                    self.progress_queue.put(("progress", "🎯 智能定位鸟类位置..."))

                    detector = YOLOBirdDetector()
                    # 传入PIL Image对象而不是文件路径，支持RAW格式
                    cropped, msg = detector.detect_and_crop_bird(self.current_image)

                    if cropped:
                        processed_image = cropped
                        # 发送裁剪后的图片到界面显示
                        self.progress_queue.put(("cropped_image", cropped, msg))

            # 识别
            self.progress_queue.put(("progress", "🧠 AI深度识别中，请稍候..."))

            # 简化版识别（直接使用温度锐化）
            import torch
            import numpy as np
            import cv2

            # 预处理
            resized = processed_image.resize((256, 256), Image.Resampling.LANCZOS)
            cropped = resized.crop((16, 16, 240, 240))

            arr = np.array(cropped)
            bgr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
            normalized = (bgr / 255.0 - np.array([0.406, 0.456, 0.485])) / np.array([0.225, 0.224, 0.229])
            tensor = torch.from_numpy(normalized).permute(2, 0, 1).unsqueeze(0).float()

            # 推理
            with torch.no_grad():
                output = model(tensor)[0]

            # 多温度对比功能已移除，保持界面简洁
            # if self.show_temp_comparison.get():
            #     self.progress_queue.put(("progress", "🌡️ 计算多温度对比..."))
            #     ... (代码已注释)

            # 使用用户选择的温度进行识别
            TEMPERATURE = self.temperature.get()
            probabilities = torch.nn.functional.softmax(output / TEMPERATURE, dim=0)

            # 获取更多候选结果用于eBird过滤
            top_k = 100 if ebird_species_set else 10
            top_probs, top_indices = torch.topk(probabilities, min(top_k, len(probabilities)))

            # 格式化结果并应用eBird过滤
            results = []
            rank = 1

            for i in range(len(top_indices)):
                idx = top_indices[i].item()
                conf = top_probs[i].item() * 100

                if conf < 5.0:  # 跳过置信度过低的结果
                    continue

                if idx < len(bird_info) and len(bird_info[idx]) >= 2:
                    cn_name = bird_info[idx][0]
                    en_name = bird_info[idx][1]

                    # eBird过滤
                    ebird_match = False
                    if ebird_species_set:
                        # 获取eBird代码
                        ebird_code = None
                        if db_manager:
                            ebird_code = db_manager.get_ebird_code_by_english_name(en_name)

                        # 只显示在eBird列表中的鸟类
                        if not ebird_code or ebird_code not in ebird_species_set:
                            continue  # 跳过不在列表中的
                        else:
                            ebird_match = True

                    results.append({
                        'rank': rank,
                        'cn_name': cn_name,
                        'en_name': en_name,
                        'confidence': conf,
                        'ebird_match': ebird_match
                    })

                    rank += 1

                    # 只保留前10个结果
                    if rank > 10:
                        break

            # 发送结果
            self.progress_queue.put(("results", results))
            self.progress_queue.put(("status", f"✓ 识别完成 (温度 T={TEMPERATURE})"))

        except Exception as e:
            self.progress_queue.put(("error", str(e)))
        finally:
            self.progress_queue.put(("done", None))

    def check_progress(self):
        """检查进度队列"""
        try:
            while True:
                msg_type, data, *extra = self.progress_queue.get_nowait()

                if msg_type == "status":
                    self.update_status(data)

                elif msg_type == "progress":
                    self.progress_label.config(text=data)

                elif msg_type == "gps":
                    self.gps_info_label.config(text=f"📍 拍摄地点: {data}")
                    self.gps_info_label.pack(padx=10, pady=8)
                    self.gps_info_frame.pack(pady=(10, 5))

                elif msg_type == "cropped_image":
                    # 显示YOLO裁剪后的图片
                    cropped_img = data
                    msg = extra[0] if extra else "YOLO裁剪"
                    self.display_image(cropped_img)
                    # 更新图片信息，显示裁剪提示（使用更醒目的颜色）
                    current_text = self.info_label.cget("text")
                    # 如果已经有YOLO信息，先移除
                    if "🔍 YOLO" in current_text:
                        current_text = current_text.split('\n🔍')[0]
                    self.info_label.config(
                        text=f"{current_text}\n🔍 {msg}",
                        fg=self.colors['accent']  # 使用蓝色高亮显示YOLO信息
                    )

                # elif msg_type == "temp_comparison":  # 已移除温度对比功能
                #     self.display_temp_comparison(data)

                elif msg_type == "results":
                    self.display_results(data)

                elif msg_type == "error":
                    messagebox.showerror("识别错误", data)

                elif msg_type == "done":
                    self.is_processing = False
                    self.loading_animation_running = False  # 停止动画
                    self.recognize_btn.config(state='normal', text="🔍 开始识别")
                    self.open_btn.config(state='normal')
                    self.progress_label.config(text="")

        except queue.Empty:
            pass

        # 继续检查
        self.root.after(100, self.check_progress)

    def display_results(self, results):
        """显示识别结果 - 响应式卡片布局"""
        # 显示标题
        self.results_title.pack(pady=(20, 10))

        # 清空旧的卡片
        for widget in self.result_cards_frame.winfo_children():
            widget.destroy()

        # 创建卡片容器（使用grid实现响应式）
        for i, r in enumerate(results[:3]):
            card = self.create_result_card_responsive(
                self.result_cards_frame,
                r['rank'],
                r['cn_name'],
                r['en_name'],
                r['confidence'],
                r.get('ebird_match', False)
            )
            # 初始放在一行，窗口变化时自动调整
            card.grid(row=0, column=i, sticky='nsew', padx=8, pady=8)

        # 配置列权重，使卡片等宽
        for i in range(3):
            self.result_cards_frame.grid_columnconfigure(i, weight=1, uniform='card')

        self.result_cards_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 20), padx=20)

        # 绑定窗口大小变化事件
        self.root.bind('<Configure>', lambda e: self.adjust_card_layout())

    def adjust_card_layout(self):
        """根据窗口宽度调整卡片布局"""
        try:
            window_width = self.root.winfo_width()

            # 获取所有卡片
            cards = self.result_cards_frame.winfo_children()
            if not cards:
                return

            # 根据窗口宽度决定布局
            if window_width < 1200:  # 小屏幕：垂直排列
                for i, card in enumerate(cards):
                    card.grid(row=i, column=0, sticky='ew', padx=20, pady=8)
                self.result_cards_frame.grid_columnconfigure(0, weight=1)
                for i in range(1, 3):
                    self.result_cards_frame.grid_columnconfigure(i, weight=0)
            else:  # 大屏幕：横向排列
                for i, card in enumerate(cards):
                    card.grid(row=0, column=i, sticky='nsew', padx=8, pady=8)
                for i in range(3):
                    self.result_cards_frame.grid_columnconfigure(i, weight=1, uniform='card')
        except:
            pass

    def display_temp_comparison(self, temp_results):
        """显示温度对比结果"""
        # 创建对比表格
        comparison_frame = tk.Frame(self.results_container, bg=self.colors['card'],
                                   relief='solid', bd=2)
        comparison_frame.pack(fill=tk.X, padx=40, pady=(10, 20))
        comparison_frame.configure(highlightbackground=self.colors['border'],
                                  highlightthickness=2,
                                  borderwidth=0)

        # 标题
        title = tk.Label(comparison_frame,
                        text="🌡️ 温度参数对比 (仅供参考，以上方结果为准)",
                        font=self.fonts['heading'],
                        fg=self.colors['text'],
                        bg=self.colors['card'])
        title.pack(pady=(15, 10))

        # 对比表格
        table_frame = tk.Frame(comparison_frame, bg=self.colors['card'])
        table_frame.pack(padx=20, pady=(0, 15))

        # 表头
        headers = ["温度", "Top-1 鸟类", "置信度", "Top-2 鸟类", "置信度", "Top-3 鸟类", "置信度"]
        for col, header in enumerate(headers):
            label = tk.Label(table_frame,
                           text=header,
                           font=tkfont.Font(family='SF Pro Display', size=11, weight='bold'),
                           fg=self.colors['text'],
                           bg=self.colors['bg_secondary'],
                           padx=10, pady=8,
                           relief='solid', bd=1)
            label.grid(row=0, column=col, sticky='nsew')

        # 数据行
        for row_idx, (temp, results) in enumerate(sorted(temp_results.items()), start=1):
            # 温度列
            temp_label = tk.Label(table_frame,
                                text=f"T={temp}",
                                font=self.fonts['small'],
                                fg=self.colors['text'],
                                bg=self.colors['card'],
                                padx=10, pady=6,
                                relief='solid', bd=1)
            temp_label.grid(row=row_idx, column=0, sticky='nsew')

            # Top 3 结果
            for i in range(3):
                if i < len(results):
                    name = results[i]['cn_name']
                    conf = results[i]['confidence']

                    name_label = tk.Label(table_frame,
                                        text=name,
                                        font=self.fonts['small'],
                                        fg=self.colors['text'],
                                        bg=self.colors['card'],
                                        padx=8, pady=6,
                                        relief='solid', bd=1)
                    name_label.grid(row=row_idx, column=i*2+1, sticky='nsew')

                    conf_label = tk.Label(table_frame,
                                        text=f"{conf:.1f}%",
                                        font=self.fonts['small'],
                                        fg=self.colors['accent'] if i == 0 else self.colors['text_secondary'],
                                        bg=self.colors['card'],
                                        padx=8, pady=6,
                                        relief='solid', bd=1)
                    conf_label.grid(row=row_idx, column=i*2+2, sticky='nsew')
                else:
                    # 空单元格
                    for j in range(2):
                        empty = tk.Label(table_frame,
                                       text="-",
                                       font=self.fonts['small'],
                                       fg=self.colors['text_secondary'],
                                       bg=self.colors['card'],
                                       padx=8, pady=6,
                                       relief='solid', bd=1)
                        empty.grid(row=row_idx, column=i*2+1+j, sticky='nsew')

    def update_status(self, text):
        """更新状态栏"""
        self.status_label.config(text=text)

    def on_closing(self):
        """关闭窗口时的清理操作"""
        try:
            # 清理临时剪贴板文件
            if hasattr(self, '_temp_clipboard_file') and os.path.exists(self._temp_clipboard_file):
                try:
                    os.unlink(self._temp_clipboard_file)
                except OSError:
                    pass

            # 如果正在处理，警告用户
            if self.is_processing:
                if messagebox.askokcancel("确认退出", "识别正在进行中，确定要退出吗？"):
                    self.root.destroy()
            else:
                self.root.destroy()

        except Exception:
            # 即使清理失败也要退出
            self.root.destroy()


def main():
    """主函数"""
    # 尝试使用TkinterDnD，回退到标准Tk
    if DRAG_DROP_AVAILABLE:
        try:
            root = TkinterDnD.Tk()
        except:
            root = tk.Tk()
    else:
        root = tk.Tk()

    # 设置macOS原生外观
    try:
        root.tk.call('tk', 'scaling', 1.5)  # Retina显示支持
    except:
        pass

    app = SuperBirdIDGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
