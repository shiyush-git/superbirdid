# -*- coding: utf-8 -*-
"""
Windows 截图工具
"""
import sys
import os

# UTF-8 设置（兼容 PyInstaller noconsole 模式）
if sys.stdout is not None:
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    elif hasattr(sys.stdout, 'buffer'):
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

if sys.stderr is not None:
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8')
    elif hasattr(sys.stderr, 'buffer'):
        import io
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

os.environ['PYTHONIOENCODING'] = 'utf-8'

# 禁用 DPI 缩放
os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "0"
os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "0"
os.environ["QT_SCALE_FACTOR"] = "1"

from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtCore import Qt, QPoint, QRect
from PyQt6.QtGui import QPainter, QColor, QPen

# Windows API 导入
try:
    import win32gui
    import win32ui
    import win32con
    import win32api
    from PIL import Image
    WINDOWS_API_AVAILABLE = True
except ImportError:
    WINDOWS_API_AVAILABLE = False
    print("警告: win32 API 不可用，使用 Qt 截图")


class SnipWidget(QWidget):
    def __init__(self, output_path):
        super().__init__()
        self.output_path = output_path
        self.initUI()

    def get_monitors_info_windows(self):
        """Windows 获取显示器信息"""
        if not WINDOWS_API_AVAILABLE:
            return self.get_monitors_info_qt()
        
        try:
            monitors = []
            monitor_handles = win32api.EnumDisplayMonitors(None, None)
            for handle, _, rect in monitor_handles:
                monitor_info = win32api.GetMonitorInfo(handle)
                monitors.append({
                    'handle': handle,
                    'monitor': monitor_info['Monitor'],
                    'work_area': monitor_info['Work'],
                    'is_primary': monitor_info['Flags'] == 0x1
                })
            return monitors
        except Exception:
            return self.get_monitors_info_qt()

    def get_monitors_info_qt(self):
        """Qt 方式获取显示器信息（备用）"""
        app = QApplication.instance()
        screens = app.screens()
        
        monitors = []
        for screen in screens:
            geom = screen.geometry()
            monitors.append({
                'monitor': (geom.x(), geom.y(), geom.x() + geom.width(), geom.y() + geom.height()),
                'is_primary': screen == app.primaryScreen()
            })
        return monitors

    def initUI(self):
        self.monitors = self.get_monitors_info_windows()
        self.min_x = min(m['monitor'][0] for m in self.monitors)
        self.min_y = min(m['monitor'][1] for m in self.monitors)
        self.max_x = max(m['monitor'][2] for m in self.monitors)
        self.max_y = max(m['monitor'][3] for m in self.monitors)
        
        self.total_width = self.max_x - self.min_x
        self.total_height = self.max_y - self.min_y
        
        self.setGeometry(self.min_x, self.min_y, self.total_width, self.total_height)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self.begin = QPoint()
        self.end = QPoint()
        self.is_drawing = False
        
        self.show()
        self.activateWindow()
        self.raise_()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        painter.fillRect(self.rect(), QColor(0, 0, 0, 128))
        
        if not self.is_drawing:
            return
        
        rect = QRect(self.begin, self.end).normalized()
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
        painter.fillRect(rect, Qt.GlobalColor.transparent)
        
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
        pen = QPen(QColor(0, 120, 215), 2)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(rect)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.begin = event.pos()
            self.end = self.begin
            self.is_drawing = True

    def mouseMoveEvent(self, event):
        if self.is_drawing:
            self.end = event.pos()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.is_drawing:
            self.end = event.pos()
            self.capture_screen()
            self.close()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            print("CANCELLED")
            self.close()

    def capture_screen(self):
        """截图并保存"""
        if self.begin and self.end:
            x1, x2 = sorted([self.begin.x(), self.end.x()])
            y1, y2 = sorted([self.begin.y(), self.end.y()])
            
            # 转换为屏幕绝对坐标
            x1 += self.min_x
            x2 += self.min_x
            y1 += self.min_y
            y2 += self.min_y
            
            try:
                # 优先使用 win32 API（更快）
                if WINDOWS_API_AVAILABLE:
                    self.capture_windows(x1, y1, x2, y2)
                else:
                    # 备用 Qt 方式
                    self.capture_qt(x1, y1, x2, y2)
                    
            except Exception as e:
                print(f"ERROR:{e}")
                import traceback
                traceback.print_exc()

    def capture_windows(self, x1, y1, x2, y2):
        """Windows 截图（win32 API）"""
        try:
            hwin = win32gui.GetDesktopWindow()
            screen_dc = win32gui.GetWindowDC(hwin)
            dc = win32ui.CreateDCFromHandle(screen_dc)
            mem_dc = dc.CreateCompatibleDC()

            left, right = min(x1, x2), max(x1, x2)
            top, bottom = min(y1, y2), max(y1, y2)
            width = right - left
            height = bottom - top

            bitmap = win32ui.CreateBitmap()
            bitmap.CreateCompatibleBitmap(dc, width, height)
            mem_dc.SelectObject(bitmap)
            mem_dc.BitBlt((0, 0), (width, height), dc, (left, top), win32con.SRCCOPY)

            bitmap_info = bitmap.GetInfo()
            bitmap_bits = bitmap.GetBitmapBits(True)
            image = Image.frombuffer(
                'RGB',
                (bitmap_info['bmWidth'], bitmap_info['bmHeight']),
                bitmap_bits, 'raw', 'BGRX', 0, 1)

            mem_dc.DeleteDC()
            win32gui.DeleteObject(bitmap.GetHandle())
            dc.DeleteDC()
            win32gui.ReleaseDC(hwin, screen_dc)

            # 保存
            image.save(self.output_path)
            print(f"SUCCESS:{self.output_path}")
            
        except Exception as e:
            print(f"Windows API 截图失败: {e}")
            # 回退到 Qt 方式
            self.capture_qt(x1, y1, x2, y2)

    def capture_qt(self, x1, y1, x2, y2):
        """Qt 截图（备用方式）"""
        app = QApplication.instance()
        screens = app.screens()
        target_screen = None
        
        # 找到包含截图区域的屏幕
        for screen in screens:
            geom = screen.geometry()
            if geom.contains(x1, y1):
                target_screen = screen
                break
        
        if target_screen is None:
            target_screen = app.primaryScreen()
        
        width = x2 - x1
        height = y2 - y1
        
        # 截取屏幕
        pixmap = target_screen.grabWindow(
            0,
            x1 - target_screen.geometry().x(),
            y1 - target_screen.geometry().y(),
            width,
            height
        )
        
        # 保存
        success = pixmap.save(self.output_path, "PNG", quality=100)
        
        if success:
            print(f"SUCCESS:{self.output_path}")
        else:
            print(f"ERROR:Failed to save screenshot")


def main():
    if len(sys.argv) > 1:
        output_path = sys.argv[1]
    else:
        output_path = "screenshot_temp.png"
    
    app = QApplication(sys.argv)
    ex = SnipWidget(output_path)
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
