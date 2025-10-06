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
import subprocess
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
    write_bird_name_to_exif, get_bird_description_from_db,
    YOLOBirdDetector, YOLO_AVAILABLE, EBIRD_FILTER_AVAILABLE,
    RAW_SUPPORT, script_dir, EXIFTOOL_AVAILABLE, EXIFTOOL_PATH
)

# 导入exiftool（用于写入EXIF）
try:
    import exiftool
except ImportError:
    exiftool = None

# 导入eBird过滤器
if EBIRD_FILTER_AVAILABLE:
    from ebird_country_filter import eBirdCountryFilter

# JSON导入用于读取离线数据和配置
import json

# 资源路径辅助函数
def get_resource_path(relative_path):
    """获取资源文件的绝对路径，支持 PyInstaller 打包环境"""
    if getattr(sys, 'frozen', False):
        # 运行在 PyInstaller 打包的环境中
        base_path = sys._MEIPASS
    else:
        # 运行在普通 Python 环境中
        base_path = os.path.dirname(__file__)
    return os.path.join(base_path, relative_path)


def get_user_data_dir():
    """获取用户数据目录，用于存储缓存等可写文件"""
    if sys.platform == 'darwin':  # macOS
        # 使用用户文档目录下的 SuperBirdID_File 文件夹
        user_data_dir = os.path.expanduser('~/Documents/SuperBirdID_File')
    elif sys.platform == 'win32':  # Windows
        user_data_dir = os.path.join(os.path.expanduser('~'), 'Documents', 'SuperBirdID_File')
    else:  # Linux
        user_data_dir = os.path.join(os.path.expanduser('~'), 'Documents', 'SuperBirdID_File')

    # 确保目录存在
    os.makedirs(user_data_dir, exist_ok=True)
    return user_data_dir


class SuperBirdIDGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("慧眼识鸟 - 离线 · 智能 · RAW · 免费")

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
        self.root.minsize(1200, 700)  # 左右分栏布局需要更大的最小宽度

        # 保存图标引用防止被垃圾回收
        self.window_icon = None

        # 设置窗口图标 (如果存在icon文件)
        try:
            icon_path = get_resource_path('icon.png')
            if os.path.exists(icon_path):
                # macOS 和 Windows 支持
                icon_img = Image.open(icon_path)
                self.window_icon = ImageTk.PhotoImage(icon_img)
                self.root.iconphoto(True, self.window_icon)
        except Exception as e:
            pass  # 图标加载失败不影响程序运行

        # 高级暗色主题配色方案 - 更精致优雅
        self.colors = {
            # 背景色系 - 深邃渐变
            'bg': '#0a0e14',           # 主背景 - 更深的蓝黑
            'bg_secondary': '#151921', # 次级背景
            'card': '#1a1f2b',         # 卡片背景 - 深蓝灰
            'card_hover': '#20253a',   # 卡片悬停

            # 排名专用渐变色系 - 奢华金属质感
            'gold': '#FFD700',         # 金色 - 第一名主色
            'gold_light': '#FFF4C4',   # 金色高光
            'gold_dark': '#B8860B',    # 金色暗部
            'gold_bg': '#2d2416',      # 金色背景

            'silver': '#C0C0C0',       # 银色 - 第二名主色
            'silver_light': '#E8E8E8', # 银色高光
            'silver_dark': '#8C8C8C',  # 银色暗部
            'silver_bg': '#1f2228',    # 银色背景

            'bronze': '#CD7F32',       # 青铜色 - 第三名主色
            'bronze_light': '#E9A860', # 青铜高光
            'bronze_dark': '#8B5A2B',  # 青铜暗部
            'bronze_bg': '#2b1f18',    # 青铜背景

            # 主色调 - 优雅蓝色
            'primary': '#5B9FED',      # 主色 - 柔和蓝
            'primary_hover': '#4A8EDB', # 悬停
            'primary_light': '#8BBEF5', # 浅色

            # 功能色 - 精致色调
            'success': '#00D9A3',      # 成功 - 青绿
            'success_light': '#5FFFDF', # 成功浅色
            'success_bg': '#0a2f26',   # 成功背景

            'warning': '#FFB020',      # 警告 - 金橙
            'warning_light': '#FFD580',
            'warning_bg': '#2f2310',

            'error': '#FF5757',        # 错误 - 柔和红
            'error_light': '#FF8787',

            # 文字色系 - 柔和对比
            'text': '#E6EDF3',         # 主文字 - 柔白
            'text_secondary': '#8B949E', # 次要文字 - 柔灰
            'text_dim': '#6E7681',     # 暗淡文字

            # 边框和分隔
            'border': '#30363D',       # 边框 - 柔和深灰
            'border_light': '#444C56', # 浅边框
            'divider': '#21262D',      # 分隔线

            # 强调色
            'accent': '#8B5CF6',       # 强调 - 紫色
            'accent_light': '#A78BFA',

            # 特殊
            'overlay': 'rgba(10, 14, 20, 0.85)',  # 遮罩
            'shadow': 'rgba(0, 0, 0, 0.6)',      # 阴影
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

        # 配置文件路径
        self.config_file = os.path.join(script_dir, 'gui_settings.json')

        # 加载保存的设置
        saved_settings = self.load_settings()

        # 配置变量（使用保存的值或默认值）
        self.use_yolo = tk.BooleanVar(value=saved_settings.get('use_yolo', True))
        self.use_gps = tk.BooleanVar(value=saved_settings.get('use_gps', True))
        self.use_ebird = tk.BooleanVar(value=saved_settings.get('use_ebird', True))

        # API服务器状态
        self.api_server_running = False
        self.api_server_thread = None
        self.api_port = 5156
        self.show_advanced = tk.BooleanVar(value=False)

        # 国家选择
        self.selected_country = tk.StringVar(value=saved_settings.get('selected_country', "自动检测"))
        self.country_list = self.load_available_countries()

        # 温度参数选择
        self.temperature = tk.DoubleVar(value=saved_settings.get('temperature', 0.5))
        # self.show_temp_comparison = tk.BooleanVar(value=False)  # 已移除温度对比功能

        # 添加变量监听，自动保存设置
        self.use_yolo.trace_add('write', lambda *args: self.save_settings())
        self.use_gps.trace_add('write', lambda *args: self.save_settings())
        self.use_ebird.trace_add('write', lambda *args: self.save_settings())
        self.selected_country.trace_add('write', lambda *args: self.save_settings())
        self.temperature.trace_add('write', lambda *args: self.save_settings())

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

        # 注册清理函数（关闭窗口时自动停止API服务）
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        # 自动启动API服务
        self.root.after(1000, self.auto_start_api_server)

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

    def load_settings(self):
        """加载保存的设置"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def save_settings(self):
        """保存当前设置"""
        settings = {
            'use_yolo': self.use_yolo.get(),
            'use_gps': self.use_gps.get(),
            'use_ebird': self.use_ebird.get(),
            'selected_country': self.selected_country.get(),
            'temperature': self.temperature.get()
        }
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(settings, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存设置失败: {e}")

    def setup_fonts(self):
        """设置字体"""
        self.fonts = {
            'title': tkfont.Font(family='SF Pro Display', size=24, weight='bold'),
            'heading': tkfont.Font(family='SF Pro Display', size=16, weight='bold'),
            'body': tkfont.Font(family='SF Pro Text', size=13),
            'small': tkfont.Font(family='SF Pro Text', size=11),
            'button': tkfont.Font(family='SF Pro Display', size=14, weight='bold'),
        }

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
        # 顶部标题（全宽）
        self.create_header(self.root)

        # 主内容区域 - 左右分栏
        content_frame = tk.Frame(self.root, bg=self.colors['bg'])
        content_frame.pack(fill=tk.BOTH, expand=True)

        # 左侧面板（固定宽度，包含图片和操作）
        left_panel = tk.Frame(content_frame, bg=self.colors['bg'], width=550)
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, padx=(20, 10), pady=10)
        left_panel.pack_propagate(False)  # 保持固定宽度

        # 右侧面板（可滚动，显示识别结果）
        right_panel = tk.Frame(content_frame, bg=self.colors['bg'])
        right_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(10, 20), pady=10)

        # 右侧滚动容器
        self.canvas = tk.Canvas(right_panel, bg=self.colors['bg'], highlightthickness=0)
        scrollbar = tk.Scrollbar(right_panel, orient='vertical', command=self.canvas.yview)
        self.results_scrollable_frame = tk.Frame(self.canvas, bg=self.colors['bg'])

        self.results_scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas.create_window((0, 0), window=self.results_scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)

        # 绑定鼠标滚轮事件（只对右侧生效）
        def _on_mousewheel_right(event):
            if event.num == 5 or event.delta < 0:
                self.canvas.yview_scroll(1, "units")
            elif event.num == 4 or event.delta > 0:
                self.canvas.yview_scroll(-1, "units")

        self.canvas.bind_all("<MouseWheel>", _on_mousewheel_right)
        self.canvas.bind_all("<Button-4>", _on_mousewheel_right)
        self.canvas.bind_all("<Button-5>", _on_mousewheel_right)

        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # 左侧面板内容
        self.create_upload_area(left_panel)
        self.create_action_buttons(left_panel)

        # 右侧面板内容（包含高级选项和结果展示区）
        self.create_advanced_options(self.results_scrollable_frame)
        self.create_results_area(self.results_scrollable_frame)

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
            icon_path = get_resource_path('icon.png')
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

        title = tk.Label(title_line, text="慧眼识鸟",
                        font=tkfont.Font(family='SF Pro Display', size=28, weight='bold'),
                        fg=self.colors['text'],
                        bg=self.colors['bg'])
        title.pack(side=tk.LEFT)

        db_info = tk.Label(title_line, text=" 可识别 10,965 种鸟",
                          font=tkfont.Font(family='SF Pro Text', size=14),
                          fg=self.colors['text_secondary'],
                          bg=self.colors['bg'])
        db_info.pack(side=tk.LEFT)

        # # 副标题
        # subtitle = tk.Label(title_text_frame, text="AI 鸟类智能识别系统",
        #                    font=tkfont.Font(family='SF Pro Text', size=14),
        #                    fg=self.colors['text_secondary'],
        #                    bg=self.colors['bg'])
        # subtitle.pack(anchor='w', pady=(4, 0))

    def create_upload_area(self, parent):
        """创建图片上传/显示区域"""
        card = tk.Frame(parent, bg=self.colors['card'],
                       relief='flat', bd=0, height=480)
        card.pack(pady=(0, 15), fill=tk.X)
        card.pack_propagate(False)  # 保持固定高度

        # 添加边框
        card.configure(highlightbackground=self.colors['border'],
                      highlightthickness=2,
                      relief='solid',
                      borderwidth=0)

        # 图片信息标签（放在顶部）
        self.info_label = tk.Label(card, text="",
                                   font=self.fonts['small'],
                                   fg=self.colors['text_secondary'],
                                   bg=self.colors['card'],
                                   anchor='w')
        self.info_label.pack(padx=20, pady=(15, 10), fill=tk.X)

        # 图片显示区 - 固定尺寸
        self.image_container = tk.Frame(card, bg=self.colors['card'], height=390)
        self.image_container.pack(padx=20, pady=(0, 20), fill=tk.BOTH)
        self.image_container.pack_propagate(False)  # 保持固定高度

        # 为容器也启用拖放支持
        if DRAG_DROP_AVAILABLE:
            try:
                self.image_container.drop_target_register(DND_FILES)
                self.image_container.dnd_bind('<<Drop>>', self.on_drop)
            except:
                pass

        # 默认占位符 - 暗色主题设计
        self.upload_placeholder = tk.Frame(self.image_container,
                                          bg=self.colors['card'],
                                          relief='solid',
                                          bd=0)
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

        icon = tk.Label(icon_bg, text="+",
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

        # 点击上传 - 绑定到所有组件
        click_handler = lambda e: self.open_image()
        self.upload_placeholder.bind('<Button-1>', click_handler)
        placeholder_content.bind('<Button-1>', click_handler)
        icon_bg.bind('<Button-1>', click_handler)
        icon.bind('<Button-1>', click_handler)
        text1.bind('<Button-1>', click_handler)
        text2.bind('<Button-1>', click_handler)
        separator.bind('<Button-1>', click_handler)
        formats.bind('<Button-1>', click_handler)

        # 添加鼠标指针样式
        for widget in [self.upload_placeholder, placeholder_content, icon_bg, icon,
                       text1, text2, separator, formats]:
            widget.configure(cursor='hand2')

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

        # 绑定悬停效果到所有组件
        for widget in [self.upload_placeholder, placeholder_content, icon_bg, icon,
                       text1, text2, separator, formats]:
            widget.bind('<Enter>', on_ph_enter)
            widget.bind('<Leave>', on_ph_leave)

        # 图片标签（初始隐藏）
        self.image_label = tk.Label(self.image_container, bg=self.colors['card'])

        # 为图片标签也启用拖放支持
        if DRAG_DROP_AVAILABLE:
            try:
                self.image_label.drop_target_register(DND_FILES)
                self.image_label.dnd_bind('<<Drop>>', self.on_drop)
            except:
                pass

    def create_action_buttons(self, parent):
        """创建操作按钮"""
        button_frame = tk.Frame(parent, bg=self.colors['bg'])
        button_frame.pack(pady=(0, 15))

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
                                  padx=15, pady=15,
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
        self.results_container.pack(fill=tk.BOTH, expand=True)

        # 结果标题（初始隐藏）
        self.results_title = tk.Label(self.results_container,
                                      text="🎯 识别结果",
                                      font=self.fonts['heading'],
                                      fg=self.colors['text'],
                                      bg=self.colors['bg'])

        # GPS信息（放在图片信息区域）
        self.gps_info_frame = tk.Frame(self.results_container, bg=self.colors['bg'])
        self.gps_info_label = tk.Label(self.gps_info_frame,
                                       text="",
                                       font=self.fonts['small'],
                                       fg=self.colors['accent'],
                                       bg=self.colors['bg'])

        # 数据来源标签（显示使用了哪个策略的数据 - 独立显示在结果区域）
        self.data_source_label = tk.Label(self.results_container,
                                          text="",
                                          font=self.fonts['small'],
                                          fg=self.colors['accent'],  # 使用强调色
                                          bg=self.colors['bg'])

        # 结果卡片容器（横排布局）
        self.result_cards_frame = tk.Frame(self.results_container,
                                          bg=self.colors['bg'])

    def create_result_card_responsive(self, parent, rank, cn_name, en_name, confidence, ebird_match=False):
        """创建响应式结果卡片 - 返回卡片对象"""
        return self.create_result_card(parent, rank, cn_name, en_name, confidence, ebird_match)

    def create_result_card(self, parent, rank, cn_name, en_name, confidence, ebird_match=False):
        """创建单个结果卡片 - 奢华排名设计"""
        # 根据排名选择金属质感配色
        if rank == 1:
            accent_color = self.colors['gold']
            accent_light = self.colors['gold_light']
            accent_dark = self.colors['gold_dark']
            bg_color = self.colors['gold_bg']
            medal = "👑"  # 皇冠代表第一名
            rank_text = "冠军"
            card_bg = '#1f1e1a'  # 温暖的深色底
        elif rank == 2:
            accent_color = self.colors['silver']
            accent_light = self.colors['silver_light']
            accent_dark = self.colors['silver_dark']
            bg_color = self.colors['silver_bg']
            medal = "🥈"
            rank_text = "亚军"
            card_bg = '#1c1d20'  # 冷色调深色底
        else:
            accent_color = self.colors['bronze']
            accent_light = self.colors['bronze_light']
            accent_dark = self.colors['bronze_dark']
            bg_color = self.colors['bronze_bg']
            medal = "🥉"
            rank_text = "季军"
            card_bg = '#1e1b19'  # 略带橙的深色底

        # 主卡片容器 - 精致边框设计
        card = tk.Frame(parent, bg=card_bg, relief='flat', bd=0)
        card.configure(highlightbackground=accent_dark,
                      highlightthickness=1)

        # 渐变顶部装饰条 - 双层设计
        top_gradient = tk.Frame(card, bg=accent_color, height=4)
        top_gradient.pack(fill=tk.X)

        top_accent = tk.Frame(card, bg=accent_light, height=1)
        top_accent.pack(fill=tk.X)

        # 内容区域
        content = tk.Frame(card, bg=card_bg)
        content.pack(fill=tk.BOTH, expand=True, padx=24, pady=20)

        # 标题行：奖牌和排名徽章
        header = tk.Frame(content, bg=card_bg)
        header.pack(fill=tk.X, pady=(0, 15))

        # 奖牌 - 更大更显眼
        medal_label = tk.Label(header, text=medal,
                              font=tkfont.Font(size=32),
                              bg=card_bg)
        medal_label.pack(side=tk.LEFT, padx=(0, 12))

        # 排名徽章 - 金属质感设计
        rank_badge = tk.Label(header, text=rank_text,
                             font=tkfont.Font(family='SF Pro Display', size=11, weight='bold'),
                             fg=accent_light,
                             bg=bg_color,
                             padx=16, pady=6)
        rank_badge.pack(side=tk.LEFT)

        # 鸟名区域
        names_frame = tk.Frame(content, bg=card_bg)
        names_frame.pack(fill=tk.X, pady=(0, 18))

        # 中文名 - 更大更醒目，金属光泽
        cn_label = tk.Label(names_frame, text=cn_name,
                           font=tkfont.Font(family='SF Pro Display', size=22, weight='bold'),
                           fg=accent_light if rank == 1 else self.colors['text'],
                           bg=card_bg,
                           anchor='w')
        cn_label.pack(fill=tk.X)

        # 英文名 - 优雅斜体
        en_label = tk.Label(names_frame, text=en_name,
                           font=tkfont.Font(family='SF Pro Text', size=13, slant='italic'),
                           fg=self.colors['text_secondary'],
                           bg=card_bg,
                           anchor='w')
        en_label.pack(fill=tk.X, pady=(6, 0))

        # eBird匹配标记 - 圆角徽章
        if ebird_match:
            ebird_badge = tk.Label(names_frame,
                                  text="✓ eBird确认",
                                  font=tkfont.Font(family='SF Pro Text', size=10),
                                  fg='#ffffff',
                                  bg=self.colors['success'],
                                  padx=10, pady=3)
            ebird_badge.pack(anchor='w', pady=(8, 0))

        # 置信度区域
        conf_container = tk.Frame(content, bg=card_bg)
        conf_container.pack(fill=tk.X)

        # 置信度标签和百分比
        conf_header = tk.Frame(conf_container, bg=card_bg)
        conf_header.pack(fill=tk.X, pady=(0, 10))

        conf_text = tk.Label(conf_header,
                            text="置信度",
                            font=tkfont.Font(family='SF Pro Text', size=11),
                            fg=self.colors['text_dim'],
                            bg=card_bg)
        conf_text.pack(side=tk.LEFT)

        conf_value = tk.Label(conf_header,
                             text=f"{confidence:.2f}%",
                             font=tkfont.Font(family='SF Pro Display', size=18, weight='bold'),
                             fg=accent_color,
                             bg=card_bg)
        conf_value.pack(side=tk.RIGHT)

        # 进度条 - 精致双层设计
        bar_outer = tk.Frame(conf_container, bg=self.colors['divider'], height=10)
        bar_outer.pack(fill=tk.X)
        bar_outer.pack_propagate(False)

        # 计算进度条宽度
        bar_width_percent = min(confidence, 100) / 100

        # 内层进度条 - 带轻微内边距
        bar_inner = tk.Frame(bar_outer, bg=accent_color, height=8)
        bar_inner.place(relx=0.01, rely=0.1, relwidth=bar_width_percent * 0.98, relheight=0.8)

        # 进度条高光效果
        bar_highlight = tk.Frame(bar_inner, bg=accent_light, height=2)
        bar_highlight.pack(fill=tk.X)

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

        # 添加点击事件 - 显示鸟种详细信息
        def on_card_click(e):
            self.show_bird_detail_dialog(cn_name)

        # 绑定点击事件到卡片和所有子组件
        for widget in [card, content, header, names_frame, conf_container, conf_header,
                      cn_label, en_label, conf_text, conf_value, medal_label, rank_badge]:
            widget.bind('<Button-1>', on_card_click)
            widget.configure(cursor='hand2')  # 显示手型光标

        # 返回卡片对象以便响应式布局使用
        return card

    def create_advanced_options(self, parent):
        """创建高级选项（右侧面板显示）"""
        # 选项容器（初始隐藏，点击高级选项按钮后显示）
        self.advanced_container = tk.Frame(parent, bg=self.colors['bg'])
        # 不自动pack，由toggle_advanced控制

        # 标题卡片
        title_card = tk.Frame(self.advanced_container, bg=self.colors['card'],
                             relief='solid', bd=1)
        title_card.pack(fill=tk.X, padx=20, pady=(0, 20))
        title_card.configure(highlightbackground=self.colors['border'],
                            borderwidth=2)

        title_label = tk.Label(title_card,
                              text="⚙️ 高级设置",
                              font=tkfont.Font(family='SF Pro Display', size=18, weight='bold'),
                              fg=self.colors['text'],
                              bg=self.colors['card'])
        title_label.pack(padx=20, pady=15)

        # 内容卡片
        content_card = tk.Frame(self.advanced_container, bg=self.colors['card'],
                               relief='solid', bd=1)
        content_card.pack(fill=tk.BOTH, expand=True, padx=20)
        content_card.configure(highlightbackground=self.colors['border'],
                              borderwidth=2)

        # 内容区域
        content = tk.Frame(content_card, bg=self.colors['card'])
        content.pack(padx=25, pady=20, fill=tk.BOTH, expand=True)

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

        # 根据保存的温度值设置下拉菜单
        current_temp = self.temperature.get()
        if current_temp in temp_values:
            temp_combo.set(temp_options[temp_values.index(current_temp)])
        else:
            temp_combo.set("0.5 (推荐)")

        # 温度值改变时更新变量
        def on_temp_change(event):
            selected_idx = temp_combo.current()
            self.temperature.set(temp_values[selected_idx])

        temp_combo.bind('<<ComboboxSelected>>', on_temp_change)

        # 温度对比选项已移除，保持界面简洁

        # API服务器控制
        api_frame = tk.Frame(content, bg=self.colors['card'])
        api_frame.pack(fill=tk.X, pady=15)

        api_title = tk.Label(api_frame,
                            text="🌐 API后台服务",
                            font=self.fonts['body'],
                            fg=self.colors['text'],
                            bg=self.colors['card'])
        api_title.pack(anchor='w')

        api_desc = tk.Label(api_frame,
                           text="    启动HTTP API服务，允许外部程序（如Lightroom）调用识别功能",
                           font=self.fonts['small'],
                           fg=self.colors['text_secondary'],
                           bg=self.colors['card'])
        api_desc.pack(anchor='w', pady=(2, 8))

        # Lightroom插件说明按钮
        lr_plugin_btn = tk.Button(api_frame,
                                  text="📸 Lightroom插件安装说明",
                                  font=self.fonts['small'],
                                  bg=self.colors['card'],
                                  fg=self.colors['accent'],
                                  activebackground=self.colors['card_hover'],
                                  activeforeground=self.colors['accent_light'],
                                  relief='flat',
                                  cursor='hand2',
                                  command=self.show_lr_plugin_guide)
        lr_plugin_btn.pack(anchor='w', padx=20, pady=(0, 10))

        # API控制按钮区域
        api_control_frame = tk.Frame(api_frame, bg=self.colors['card'])
        api_control_frame.pack(fill=tk.X, padx=20)

        # API状态指示器
        self.api_status_label = tk.Label(api_control_frame,
                                         text="● 未运行",
                                         font=self.fonts['small'],
                                         fg='#888888',
                                         bg=self.colors['card'])
        self.api_status_label.pack(side=tk.LEFT, padx=(0, 15))

        # 启动/停止按钮
        self.api_toggle_btn = tk.Button(api_control_frame,
                                        text="启动API服务",
                                        font=self.fonts['small'],
                                        bg='#ffffff',
                                        fg='#000000',
                                        activebackground='#e0e0e0',
                                        activeforeground='#000000',
                                        relief='solid',
                                        bd=2,
                                        padx=15,
                                        pady=5,
                                        cursor='hand2',
                                        command=self.toggle_api_server)
        self.api_toggle_btn.pack(side=tk.LEFT)

        # 端口号显示
        api_port_label = tk.Label(api_control_frame,
                                  text=f"端口: {self.api_port}",
                                  font=self.fonts['small'],
                                  fg=self.colors['text_secondary'],
                                  bg=self.colors['card'])
        api_port_label.pack(side=tk.LEFT, padx=(15, 0))

    def toggle_advanced(self):
        """切换高级选项显示（右侧面板）"""
        if self.show_advanced.get():
            # 隐藏高级选项，显示结果区域
            self.advanced_container.pack_forget()
            self.results_container.pack(fill=tk.BOTH, expand=True)
            self.show_advanced.set(False)
            self.advanced_btn.config(text="⚙️ 高级选项")
        else:
            # 隐藏结果区域，显示高级选项
            self.results_container.pack_forget()
            self.advanced_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
            self.show_advanced.set(True)
            self.advanced_btn.config(text="✖ 关闭设置")

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
        self.data_source_label.config(text="")  # 清空文本
        self.data_source_label.pack_forget()  # 隐藏数据来源标签
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

        # 如果高级设置正在显示，自动关闭并显示结果区域
        if self.show_advanced.get():
            self.advanced_container.pack_forget()
            self.results_container.pack(fill=tk.BOTH, expand=True)
            self.show_advanced.set(False)
            self.advanced_btn.config(text="⚙️ 高级选项")

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
            gps_location_species = None  # GPS精确位置的物种列表
            ebird_data_source = None  # 记录使用的数据来源

            if self.use_gps.get():
                lat, lon, info = extract_gps_from_exif(self.current_image_path)
                if lat and lon:
                    region, country_code, region_info = get_region_from_gps(lat, lon)

                    # 检查GPS位置缓存并自动获取
                    cache_status = ""
                    if EBIRD_FILTER_AVAILABLE:
                        EBIRD_API_KEY = os.environ.get('EBIRD_API_KEY', '60nan25sogpo')
                        cache_dir = os.path.join(get_user_data_dir(), 'ebird_cache')
                        offline_dir = get_resource_path("offline_ebird_data")
                        temp_filter = eBirdCountryFilter(EBIRD_API_KEY, cache_dir=cache_dir, offline_dir=offline_dir)

                        # 获取GPS位置的物种列表（内部会自动处理三级回退）
                        gps_location_species = temp_filter.get_location_species_list(lat, lon, 25)

                        # 获取缓存信息以读取data_source
                        cache_info = temp_filter.get_location_cache_info(lat, lon, 25)
                        if cache_info:
                            species_count = cache_info.get('species_count', 0)
                            ebird_data_source = cache_info.get('data_source', '')
                            cache_status = f" | ✓ {species_count} 个物种"
                        elif gps_location_species:
                            cache_status = f" | ✅ {len(gps_location_species)} 个物种"

                    # 将GPS信息和缓存状态一起显示
                    full_gps_info = region_info + cache_status
                    self.progress_queue.put(("gps", full_gps_info))

                    # data_source将在识别结果之前发送，这里不需要重复发送

            # eBird过滤设置
            if self.use_ebird.get() and EBIRD_FILTER_AVAILABLE:
                try:
                    # 优先使用GPS精确位置数据，其次使用国家数据
                    if gps_location_species:
                        # 使用GPS位置的25km范围数据（最精确）
                        ebird_species_set = gps_location_species
                        self.progress_queue.put(("progress", f"✅ 使用GPS位置数据 ({len(ebird_species_set)} 种鸟类)"))
                        # ebird_data_source 已在前面设置
                    else:
                        # 没有GPS数据，回退到国家级别数据
                        selected = self.selected_country.get()

                        # 如果是"自动检测"且有GPS，使用GPS国家代码
                        if selected == "自动检测":
                            if country_code:
                                pass  # 使用GPS检测到的country_code
                            else:
                                country_code = None  # 没有GPS，不使用过滤
                                ebird_data_source = "全球模式（未检测到GPS）"
                        # 如果是"全球模式"，不使用过滤
                        elif selected == "全球模式":
                            country_code = None
                            ebird_data_source = "全球模式"
                        # 否则使用用户选择的国家
                        else:
                            country_code = self.country_list.get(selected)

                        # 如果有国家代码，加载eBird数据
                        if country_code:
                            self.progress_queue.put(("progress", f"🌍 加载 {country_code} 国家级鸟类数据库..."))

                            # eBird API密钥（优先使用环境变量，否则使用默认值）
                            EBIRD_API_KEY = os.environ.get('EBIRD_API_KEY', '60nan25sogpo')
                            cache_dir = os.path.join(get_user_data_dir(), 'ebird_cache')
                            offline_dir = get_resource_path("offline_ebird_data")
                            ebird_filter = eBirdCountryFilter(EBIRD_API_KEY, cache_dir=cache_dir, offline_dir=offline_dir)
                            ebird_species_set = ebird_filter.get_country_species_list(country_code)

                            if ebird_species_set:
                                self.progress_queue.put(("progress", f"✅ 数据库加载完成 ({len(ebird_species_set)} 种鸟类)"))
                                ebird_data_source = f"国家{country_code}数据"
                            else:
                                ebird_data_source = "全球模式（国家数据加载失败）"
                except Exception as e:
                    self.progress_queue.put(("progress", f"⚠️ 地区数据加载失败，使用全球数据库"))
                    ebird_data_source = "全球模式（加载异常）"
            else:
                # 未启用eBird筛选
                ebird_data_source = "全球模式（未启用地理筛选）"

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
                    else:
                        # YOLO未检测到鸟类，显示消息
                        self.progress_queue.put(("progress", f"⚠️ {msg}"))
                else:
                    # 图片太小，跳过YOLO
                    self.progress_queue.put(("progress", f"ℹ️ 图片尺寸 {width}x{height}，跳过YOLO检测"))

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
            filtered_results = []  # 被过滤掉的结果
            rank = 1

            for i in range(len(top_indices)):
                idx = top_indices[i].item()
                conf = top_probs[i].item() * 100

                if conf < 5.0:  # 跳过置信度过低的结果
                    continue

                # 优先使用数据库查询
                cn_name = None
                en_name = None

                if db_manager:
                    bird_data = db_manager.get_bird_by_class_id(idx)
                    if bird_data:
                        cn_name = bird_data['chinese_simplified']
                        en_name = bird_data['english_name']

                # 如果数据库查询失败，回退到 bird_info
                if not cn_name and idx < len(bird_info) and len(bird_info[idx]) >= 2:
                    cn_name = bird_info[idx][0]
                    en_name = bird_info[idx][1]

                if cn_name and en_name:
                    # eBird过滤
                    ebird_match = False
                    filtered_by_ebird = False

                    if ebird_species_set:
                        # 获取eBird代码
                        ebird_code = None
                        if db_manager:
                            ebird_code = db_manager.get_ebird_code_by_english_name(en_name)

                        # 检查是否在eBird列表中
                        if ebird_code and ebird_code in ebird_species_set:
                            ebird_match = True
                        else:
                            filtered_by_ebird = True

                    # 只有在没有被eBird过滤的情况下才加入结果
                    if not filtered_by_ebird:
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
                    else:
                        # 保存被过滤的结果（最多5个）
                        if len(filtered_results) < 5:
                            filtered_results.append({
                                'cn_name': cn_name,
                                'en_name': en_name,
                                'confidence': conf
                            })

            # 如果eBird过滤导致结果为空，显示提示并使用原始结果
            if ebird_species_set and len(results) == 0 and len(filtered_results) > 0:
                self.progress_queue.put(("warning",
                    f"⚠️ 地理筛选过于严格，未找到匹配结果\n"
                    f"最可能的识别结果（{filtered_results[0]['cn_name']}）不在当前地区数据库中\n"
                    f"建议：关闭地理筛选或切换到\"全球模式\""))

                # 使用被过滤的前3个结果，但标记为非eBird匹配
                for i, r in enumerate(filtered_results[:3]):
                    results.append({
                        'rank': i + 1,
                        'cn_name': r['cn_name'],
                        'en_name': r['en_name'],
                        'confidence': r['confidence'],
                        'ebird_match': False
                    })

            # 如果完全没有结果（所有置信度都低于5%）
            if len(results) == 0:
                self.progress_queue.put(("warning",
                    "❌ 未能识别出鸟类\n"
                    "可能原因：\n"
                    "• 图片中没有清晰的鸟类\n"
                    "• 图片质量较低或模糊\n"
                    "• 鸟类种类不在识别范围内\n"
                    "建议：尝试使用更清晰的图片"))

            # 在显示结果之前，先显示数据来源信息（始终显示）
            if ebird_data_source:
                self.progress_queue.put(("data_source", ebird_data_source))

            # 发送结果
            self.progress_queue.put(("results", results))

            # 状态消息
            if len(results) > 0:
                self.progress_queue.put(("status", f"✓ 识别完成 (温度 T={TEMPERATURE})"))
            else:
                self.progress_queue.put(("status", "识别完成，但未找到匹配结果"))

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
                    self.gps_info_label.pack(padx=10, pady=(5, 0))
                    self.gps_info_frame.pack(pady=(10, 5))

                elif msg_type == "data_source":
                    # 显示数据来源（不同策略用不同的图标和文字）
                    # 优先检查"全球模式"，避免被"国家数据"误匹配
                    if "全球模式" in data:
                        icon = "🌐"
                        text = f"{icon} 全球模式（无地理筛选）"
                    elif "GPS位置30天数据" in data:
                        icon = "🎯"
                        text = f"{icon} 使用最精确的GPS位置数据 (30天内观测)"
                    elif "区域" in data and "年度数据" in data:
                        icon = "📍"
                        region_name = data.split("区域")[1].split("年度")[0]
                        text = f"{icon} 使用区域年度数据 ({region_name})"
                    elif "国家" in data and "离线数据" in data:
                        icon = "🌏"
                        country_name = data.split("国家")[1].split("离线")[0]
                        text = f"{icon} 使用国家离线数据 ({country_name})"
                    elif "国家" in data and "数据" in data:
                        # 国家级API数据（非离线）
                        icon = "🌍"
                        country_code = data.split("国家")[1].split("数据")[0]
                        text = f"{icon} 使用国家数据 ({country_code})"
                    else:
                        icon = "ℹ️"
                        text = f"{icon} {data}"

                    # 只设置文本，不立即pack，等display_results时统一布局
                    self.data_source_label.config(text=text)

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

                elif msg_type == "warning":
                    # 不再使用弹窗，而是在结果区域显示警告信息
                    # 解析警告信息
                    if "地理筛选过于严格" in data:
                        # 提取鸟类名称
                        lines = data.split('\n')
                        bird_name = ""
                        for line in lines:
                            if "最可能的识别结果" in line:
                                # 提取括号中的鸟类名称
                                start = line.find("（")
                                end = line.find("）")
                                if start != -1 and end != -1:
                                    bird_name = line[start+1:end]
                                break

                        # 显示在数据来源标签处
                        warning_text = f"⚠️ 地理筛选过于严格，{bird_name} 不在当前地区。已显示全球识别结果"
                        self.data_source_label.config(
                            text=warning_text,
                            fg=self.colors['warning']
                        )
                        self.data_source_label.pack(padx=10, pady=(2, 5))
                    else:
                        # 其他警告也显示在数据来源标签
                        self.data_source_label.config(
                            text=f"⚠️ {data.split(chr(10))[0]}",  # 只显示第一行
                            fg=self.colors['warning']
                        )
                        self.data_source_label.pack(padx=10, pady=(2, 5))

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

        # 数据来源信息已经通过 data_source 消息显示，这里确保它在标题下方
        # （如果已经 pack，重新 pack 会移动到正确位置）
        if self.data_source_label.cget("text"):  # 只有有内容时才显示
            self.data_source_label.pack(pady=(0, 10), padx=20)

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

        # 自动将第一名识别结果写入EXIF（仅支持JPEG和RAW格式）
        if results and self.current_image_path:
            top_result = results[0]
            bird_name = top_result['cn_name']  # 使用中文名
            success, message = write_bird_name_to_exif(self.current_image_path, bird_name)

            # 显示写入结果（仅在成功时显示，失败静默跳过PNG等格式）
            if success:
                self.update_status(message)

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

    def show_bird_detail_dialog(self, bird_cn_name):
        """显示鸟种简介对话框"""
        # 从数据库读取鸟种信息
        bird_info = get_bird_description_from_db(bird_cn_name)

        if not bird_info:
            messagebox.showinfo("信息", f"未找到 {bird_cn_name} 的详细信息")
            return

        # 创建对话框窗口（紧凑尺寸）
        dialog = tk.Toplevel(self.root)
        dialog.title(f"鸟种简介 - {bird_cn_name}")
        dialog.geometry("600x400")
        dialog.configure(bg=self.colors['bg'])

        # 设置窗口居中
        dialog.update_idletasks()
        width = dialog.winfo_width()
        height = dialog.winfo_height()
        x = (dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (dialog.winfo_screenheight() // 2) - (height // 2)
        dialog.geometry(f'{width}x{height}+{x}+{y}')

        # 主容器
        main_frame = tk.Frame(dialog, bg=self.colors['bg'])
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # 标题区域（缩小字体）
        title_frame = tk.Frame(main_frame, bg=self.colors['card'], relief='solid', bd=1)
        title_frame.pack(fill=tk.X, pady=(0, 15))

        title_container = tk.Frame(title_frame, bg=self.colors['card'])
        title_container.pack(padx=15, pady=12)

        # 中文名（缩小字体）
        cn_label = tk.Label(title_container,
                           text=bird_info['cn_name'],
                           font=tkfont.Font(family='SF Pro Display', size=20, weight='bold'),
                           fg=self.colors['text'],
                           bg=self.colors['card'])
        cn_label.pack()

        # 英文名（缩小字体）
        en_label = tk.Label(title_container,
                           text=bird_info['en_name'],
                           font=tkfont.Font(family='SF Pro Text', size=12, slant='italic'),
                           fg=self.colors['text_secondary'],
                           bg=self.colors['card'])
        en_label.pack(pady=(3, 0))

        # 学名（缩小字体）
        sci_label = tk.Label(title_container,
                            text=bird_info['scientific_name'],
                            font=tkfont.Font(family='SF Pro Text', size=11),
                            fg=self.colors['text_secondary'],
                            bg=self.colors['card'])
        sci_label.pack(pady=(3, 0))

        # 滚动文本区域 - 只显示简介（限制高度）
        text_frame = tk.Frame(main_frame, bg=self.colors['card'])
        text_frame.pack(fill=tk.X, pady=(0, 15))

        # 创建滚动条
        scrollbar = tk.Scrollbar(text_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 创建文本框（限制高度为8行）
        text_widget = tk.Text(text_frame,
                             wrap=tk.WORD,
                             height=8,
                             font=tkfont.Font(family='SF Pro Text', size=13),
                             bg=self.colors['card'],
                             fg=self.colors['text'],
                             relief='flat',
                             padx=15,
                             pady=15,
                             yscrollcommand=scrollbar.set)
        text_widget.pack(side=tk.LEFT, fill=tk.X, expand=True)
        scrollbar.config(command=text_widget.yview)

        # 只插入简短描述
        if bird_info['short_description']:
            text_widget.insert(tk.END, bird_info['short_description'])
        else:
            text_widget.insert(tk.END, "暂无简介信息")

        # 禁止编辑
        text_widget.config(state=tk.DISABLED)

        # 按钮区域
        button_frame = tk.Frame(main_frame, bg=self.colors['bg'])
        button_frame.pack(fill=tk.X)

        # 写入EXIF按钮（鸟名到Title，简介到Caption）
        write_btn = tk.Button(button_frame,
                             text="📝 写入到EXIF (Title + Caption)",
                             font=tkfont.Font(family='SF Pro Display', size=12, weight='bold'),
                             bg='#ffffff',
                             fg='#000000',
                             activebackground='#e0e0e0',
                             activeforeground='#000000',
                             relief='solid',
                             bd=2,
                             padx=20,
                             pady=12,
                             cursor='hand2',
                             command=lambda: self.write_bird_info_and_close(
                                 bird_info['cn_name'],
                                 bird_info['short_description'] or '',
                                 dialog
                             ))
        write_btn.pack(side=tk.LEFT, padx=(0, 10))

        # 关闭按钮
        close_btn = tk.Button(button_frame,
                             text="关闭",
                             font=tkfont.Font(family='SF Pro Display', size=14, weight='bold'),
                             bg='#ffffff',
                             fg='#000000',
                             activebackground='#e0e0e0',
                             activeforeground='#000000',
                             relief='solid',
                             bd=2,
                             padx=30,
                             pady=15,
                             cursor='hand2',
                             command=dialog.destroy)
        close_btn.pack(side=tk.RIGHT)

        # 悬停效果
        def add_hover_effect(button):
            def on_enter(e):
                button.configure(bg='#e0e0e0')
            def on_leave(e):
                button.configure(bg='#ffffff')
            button.bind('<Enter>', on_enter)
            button.bind('<Leave>', on_leave)

        add_hover_effect(write_btn)
        add_hover_effect(close_btn)

    def write_bird_info_and_close(self, bird_name, description, dialog):
        """写入鸟名到Title和简介到Caption并关闭对话框"""
        if not self.current_image_path:
            messagebox.showwarning("警告", "当前没有打开的图片")
            return

        # 同时写入Title和Caption
        success, message = self.write_bird_to_exif(self.current_image_path, bird_name, description)

        if success:
            messagebox.showinfo("成功", message)
            dialog.destroy()
        else:
            messagebox.showwarning("失败", message)

    def write_bird_to_exif(self, image_path, bird_name, description):
        """
        将鸟名写入Title，简介写入Caption

        Args:
            image_path: 图片路径
            bird_name: 鸟类名称（写入Title）
            description: 鸟类简介（写入Caption）

        Returns:
            (success: bool, message: str)
        """
        # 检查文件是否存在
        if not os.path.exists(image_path):
            return False, f"文件不存在: {image_path}"

        # 获取文件扩展名
        file_ext = os.path.splitext(image_path)[1].lower()

        # 支持的格式列表
        supported_formats = [
            '.jpg', '.jpeg', '.jpe', '.jfif',  # JPEG
            '.cr2', '.cr3', '.nef', '.nrw', '.arw', '.srf', '.dng',
            '.raf', '.orf', '.rw2', '.pef', '.srw', '.raw', '.rwl',
        ]

        # 跳过不支持的格式
        if file_ext not in supported_formats:
            return False, f"跳过格式 {file_ext}（仅支持JPEG和RAW格式）"

        # 必须使用ExifTool才能写入
        if not EXIFTOOL_AVAILABLE:
            return False, "ExifTool不可用，无法写入EXIF"

        try:
            with exiftool.ExifToolHelper(executable=EXIFTOOL_PATH) as et:
                # 同时写入Title和Caption字段
                tags = {
                    # Title字段
                    "XMP:Title": bird_name,
                    "IPTC:ObjectName": bird_name,
                }

                # 如果有简介，写入Caption
                if description:
                    tags.update({
                        "EXIF:ImageDescription": description,
                        "XMP:Description": description,
                        "IPTC:Caption-Abstract": description,
                    })

                et.set_tags(
                    image_path,
                    tags=tags,
                    params=["-overwrite_original"]
                )

            return True, f"✓ 已写入 Title: {bird_name}\n✓ 已写入 Caption: {description[:50]}..." if description else f"✓ 已写入 Title: {bird_name}"

        except Exception as e:
            return False, f"写入EXIF失败: {e}"

    def show_lr_plugin_guide(self):
        """显示Lightroom插件安装说明窗口"""
        dialog = tk.Toplevel(self.root)
        dialog.title("📸 Lightroom插件安装指南")
        dialog.geometry("800x650")
        dialog.configure(bg=self.colors['bg'])
        dialog.resizable(False, False)

        # 居中显示
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (800 // 2)
        y = (dialog.winfo_screenheight() // 2) - (650 // 2)
        dialog.geometry(f'800x650+{x}+{y}')

        # 主容器
        main_container = tk.Frame(dialog, bg=self.colors['card'], padx=40, pady=30)
        main_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # 标题
        title = tk.Label(main_container,
                        text="📸 Lightroom Classic 插件安装指南",
                        font=tkfont.Font(family='SF Pro Display', size=22, weight='bold'),
                        fg=self.colors['text'],
                        bg=self.colors['card'])
        title.pack(pady=(0, 25))

        # 滚动容器
        canvas = tk.Canvas(main_container, bg=self.colors['card'], highlightthickness=0, height=400)
        scrollbar = tk.Scrollbar(main_container, orient='vertical', command=canvas.yview)
        scroll_frame = tk.Frame(canvas, bg=self.colors['card'])

        scroll_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scroll_frame, anchor='nw')
        canvas.configure(yscrollcommand=scrollbar.set)

        # 步骤内容
        steps = [
            {
                "number": "1️⃣",
                "title": "获取插件文件",
                "content": "插件文件位于应用程序包内，点击下方按钮打开插件目录：",
                "button": ("📁 打开插件文件夹", self.open_plugin_folder)
            },
            {
                "number": "2️⃣",
                "title": "复制插件",
                "content": "在打开的文件夹中，找到 SuperBirdIDPlugin.lrplugin 文件夹\n将整个文件夹复制到您选择的位置（建议：文档/Lightroom插件）",
                "button": None
            },
            {
                "number": "3️⃣",
                "title": "在Lightroom中添加插件",
                "content": "• 打开 Lightroom Classic\n• 菜单栏：文件 → 增效工具管理器\n• 点击左下角 \"添加\" 按钮\n• 浏览并选择刚才复制的 SuperBirdIDPlugin.lrplugin 文件夹\n• 点击 \"添加增效工具\"",
                "button": None
            },
            {
                "number": "4️⃣",
                "title": "确认API服务运行",
                "content": "使用插件前，请确保 SuperBirdID API 服务正在运行：\n• 在高级设置中点击 \"启动API服务\"\n• 状态显示为 \"● 运行中 (端口: 5156)\"\n• 关闭GUI窗口后API服务会自动停止",
                "button": None
            },
            {
                "number": "5️⃣",
                "title": "开始使用",
                "content": "• 在Lightroom图库中选择鸟类照片\n• 文件 → 导出\n• 在导出对话框顶部选择 \"🦆 SuperBirdID 本地鸟类识别\"\n• 点击 \"导出\" 开始识别\n• 识别结果会自动写入照片的Title和Caption字段",
                "button": None
            }
        ]

        for step in steps:
            # 步骤卡片
            step_card = tk.Frame(scroll_frame, bg=self.colors['bg_secondary'],
                               relief='flat', bd=0)
            step_card.pack(fill=tk.X, pady=(0, 15), padx=5)

            # 步骤内容容器
            step_content = tk.Frame(step_card, bg=self.colors['bg_secondary'])
            step_content.pack(fill=tk.X, padx=20, pady=15)

            # 步骤标题行
            title_frame = tk.Frame(step_content, bg=self.colors['bg_secondary'])
            title_frame.pack(fill=tk.X, pady=(0, 10))

            step_number = tk.Label(title_frame,
                                  text=step["number"],
                                  font=tkfont.Font(size=20),
                                  bg=self.colors['bg_secondary'])
            step_number.pack(side=tk.LEFT, padx=(0, 10))

            step_title = tk.Label(title_frame,
                                 text=step["title"],
                                 font=tkfont.Font(family='SF Pro Display', size=16, weight='bold'),
                                 fg=self.colors['text'],
                                 bg=self.colors['bg_secondary'])
            step_title.pack(side=tk.LEFT)

            # 步骤说明
            step_desc = tk.Label(step_content,
                                text=step["content"],
                                font=tkfont.Font(family='SF Pro Text', size=12),
                                fg=self.colors['text_secondary'],
                                bg=self.colors['bg_secondary'],
                                justify='left',
                                anchor='w')
            step_desc.pack(fill=tk.X, pady=(0, 10))

            # 步骤按钮（如果有）
            if step["button"]:
                btn_text, btn_cmd = step["button"]
                step_btn = tk.Button(step_content,
                                    text=btn_text,
                                    font=self.fonts['small'],
                                    bg=self.colors['accent'],
                                    fg='#ffffff',
                                    activebackground=self.colors['accent_light'],
                                    activeforeground='#ffffff',
                                    relief='flat',
                                    bd=0,
                                    padx=20,
                                    pady=8,
                                    cursor='hand2',
                                    command=btn_cmd)
                step_btn.pack(anchor='w')

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 底部按钮
        bottom_frame = tk.Frame(main_container, bg=self.colors['card'])
        bottom_frame.pack(fill=tk.X, pady=(20, 0))

        close_btn = tk.Button(bottom_frame,
                             text="关闭",
                             font=self.fonts['body'],
                             bg=self.colors['card'],
                             fg=self.colors['text_secondary'],
                             activebackground=self.colors['card_hover'],
                             relief='flat',
                             bd=0,
                             padx=30,
                             pady=10,
                             cursor='hand2',
                             command=dialog.destroy)
        close_btn.pack(side=tk.RIGHT)

    def open_plugin_folder(self):
        """打开插件文件夹"""
        # 获取插件路径
        if getattr(sys, 'frozen', False):
            # 打包后的路径
            plugin_path = os.path.join(sys._MEIPASS, 'Plugins')
        else:
            # 开发环境路径
            plugin_path = os.path.join(os.path.dirname(__file__), 'SuperBirdIDPlugin.lrplugin')
            # 如果是直接访问插件文件夹，则打开上级目录
            if os.path.exists(plugin_path):
                plugin_path = os.path.dirname(__file__)

        # 打开文件夹
        if os.path.exists(plugin_path):
            subprocess.run(['open', plugin_path])
        else:
            messagebox.showerror("错误", f"插件文件夹不存在：{plugin_path}")

    def auto_start_api_server(self):
        """程序启动时自动启动API服务"""
        if not self.api_server_running:
            self.start_api_server()

    def toggle_api_server(self):
        """启动或停止API服务器"""
        if self.api_server_running:
            # 停止服务器
            self.stop_api_server()
        else:
            # 启动服务器
            self.start_api_server()

    def start_api_server(self):
        """启动API服务器（在线程中运行）"""
        try:
            # 导入 Flask API
            from SuperBirdID_API import app as flask_app

            # 在后台线程中运行 Flask 服务器
            def run_flask():
                flask_app.run(
                    host='127.0.0.1',
                    port=self.api_port,
                    debug=False,
                    use_reloader=False,  # 重要：禁用重载器避免重启
                    threaded=True
                )

            self.api_server_thread = threading.Thread(target=run_flask, daemon=True)
            self.api_server_thread.start()

            self.api_server_running = True

            # 更新UI
            self.api_status_label.config(text="● 运行中", fg='#4CAF50')
            self.api_toggle_btn.config(text="停止API服务")
            self.update_status(f"✓ API服务器已启动 (http://127.0.0.1:{self.api_port})")

        except Exception as e:
            messagebox.showerror("错误", f"启动API服务器失败:\n{e}")
            self.api_server_running = False

    def stop_api_server(self):
        """停止API服务器"""
        try:
            # 注意：Flask 服务器运行在 daemon 线程中，无法优雅停止
            # 当主程序退出时会自动结束
            # 这里只是更新状态标志

            self.api_server_running = False

            # 更新UI
            self.api_status_label.config(text="● 未运行", fg='#888888')
            self.api_toggle_btn.config(text="启动API服务")
            self.update_status("ℹ️ API服务器将在应用关闭时停止")

        except Exception as e:
            messagebox.showerror("错误", f"停止API服务器失败:\n{e}")

    def on_closing(self):
        """关闭窗口时的清理操作"""
        try:
            # 停止API服务器
            if self.api_server_running:
                self.stop_api_server()

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
