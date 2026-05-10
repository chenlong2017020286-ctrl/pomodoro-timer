#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
番茄钟 - Pomodoro Timer
PySide6 桌面应用，功能等价于 pomodoro.html
"""

import sys
import json
import os
import winsound
import threading
import time

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QSpinBox, QLabel, QSizePolicy,
)
from PySide6.QtCore import Qt, QTimer, QRectF
from PySide6.QtGui import QPainter, QPen, QColor, QFont, QFontMetrics

DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pomodoro_data.json")


def load_data():
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {"sessions": 0, "work": 25, "shortBreak": 5, "longBreak": 15}


def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)


def play_notification():
    def _play():
        try:
            winsound.Beep(880, 150)
            time.sleep(0.2)
            winsound.Beep(1100, 150)
            time.sleep(0.2)
            winsound.Beep(1320, 300)
        except Exception:
            pass
    threading.Thread(target=_play, daemon=True).start()


class TimerRing(QWidget):
    """圆形进度环 + 中央时间显示"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._progress = 1.0
        self._is_break = False
        self._time_text = "25:00"
        self.setMinimumSize(200, 200)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def set_progress(self, value):
        self._progress = max(0.0, min(1.0, value))
        self.update()

    def set_break_mode(self, is_break):
        self._is_break = is_break
        self.update()

    def set_time_text(self, text):
        self._time_text = text
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        side = min(w, h)
        cx, cy = w / 2, h / 2
        margin = 10
        pen_width = 6
        ring_radius = (side - 2 * margin - pen_width) / 2

        if ring_radius <= 0:
            painter.end()
            return

        rect = QRectF(cx - ring_radius, cy - ring_radius,
                      ring_radius * 2, ring_radius * 2)

        # 背景环
        pen = QPen(QColor(255, 255, 255, 15), pen_width)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.drawArc(rect, 0, 360 * 16)

        # 进度环
        if self._progress > 0:
            color = QColor(74, 158, 255) if self._is_break else QColor(226, 85, 85)
            pen = QPen(color, pen_width)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            start_angle = 90 * 16
            span_angle = -int(360 * 16 * self._progress)
            painter.drawArc(rect, start_angle, span_angle)

        # 时间文本
        font_size = max(24, int(ring_radius * 0.38))
        font = QFont("Segoe UI", font_size, QFont.Weight.Bold)
        painter.setFont(font)
        painter.setPen(QColor(238, 238, 238))
        fm = QFontMetrics(font)
        text_rect = fm.boundingRect(self._time_text)
        painter.drawText(int(cx - text_rect.width() / 2),
                         int(cy + text_rect.height() / 3),
                         self._time_text)

        painter.end()


class PomodoroApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("番茄钟")
        self.setFixedSize(420, 540)

        # 数据
        self.data = load_data()
        self.session_count = self.data.get("sessions", 0)

        self.mode_durations = {
            "work": self.data.get("work", 25),
            "shortBreak": self.data.get("shortBreak", 5),
            "longBreak": self.data.get("longBreak", 15),
        }

        self.current_mode = "work"
        self.total_seconds = self.mode_durations["work"] * 60
        self.remaining = self.total_seconds
        self.is_running = False

        # UI
        self._setup_ui()
        self._setup_shortcuts()

        # 定时器
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)

        # 初始化
        self._update_tab_styles()
        self._update_main_btn_style()
        self._update_ring_display()
        self._update_ui_state()

    # ---- UI 构建 ----

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        root_style = """
            QMainWindow { background: #1a1a2e; }
            QWidget#central { background: #1a1a2e; }
        """
        central.setObjectName("central")
        central.setStyleSheet(root_style)

        layout = QVBoxLayout(central)
        layout.setContentsMargins(40, 24, 40, 24)
        layout.setSpacing(0)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 标题
        title = QLabel("番茄钟")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 18px; font-weight: 600; color: #aaa; letter-spacing: 2px; background: transparent;")
        title.setFixedHeight(28)
        layout.addWidget(title)

        # 空行
        layout.addSpacing(16)

        # 标签页
        tab_widget = QWidget()
        tab_widget.setStyleSheet("background: transparent;")
        tab_layout = QHBoxLayout(tab_widget)
        tab_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tab_layout.setSpacing(8)
        tab_layout.setContentsMargins(0, 0, 0, 0)

        self.tab_work = self._make_tab("专注")
        self.tab_short = self._make_tab("短休")
        self.tab_long = self._make_tab("长休")
        for tab, mode in [(self.tab_work, "work"),
                          (self.tab_short, "shortBreak"),
                          (self.tab_long, "longBreak")]:
            tab.clicked.connect(lambda checked, m=mode: self._load_mode(m))
            tab_layout.addWidget(tab)

        layout.addWidget(tab_widget)
        layout.addSpacing(20)

        # 计时环
        self.ring = TimerRing()
        self.ring.setFixedSize(260, 260)
        layout.addWidget(self.ring, alignment=Qt.AlignmentFlag.AlignCenter)

        # 状态标签
        self.status_label = QLabel("开始专注吧")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("font-size: 13px; color: #888; background: transparent;")
        self.status_label.setFixedHeight(24)
        layout.addWidget(self.status_label)

        layout.addSpacing(8)

        # 控制按钮
        ctrl_widget = QWidget()
        ctrl_widget.setStyleSheet("background: transparent;")
        ctrl_layout = QHBoxLayout(ctrl_widget)
        ctrl_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ctrl_layout.setSpacing(12)
        ctrl_layout.setContentsMargins(0, 0, 0, 0)

        self.btn_main = QPushButton("开始")
        self.btn_main.setFixedSize(120, 44)
        self.btn_main.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_main.clicked.connect(self._toggle_timer)
        ctrl_layout.addWidget(self.btn_main)

        self.btn_reset = QPushButton("重置")
        self.btn_reset.setFixedSize(80, 44)
        self.btn_reset.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_reset.clicked.connect(self._reset_timer)
        self.btn_reset.setStyleSheet("""
            QPushButton {
                background: rgba(255,255,255,0.06); color: #888;
                border: none; border-radius: 10px;
                font-size: 14px; font-weight: 600;
            }
            QPushButton:hover { background: rgba(255,255,255,0.1); color: #aaa; }
        """)
        ctrl_layout.addWidget(self.btn_reset)

        layout.addWidget(ctrl_widget)
        layout.addSpacing(16)

        # 设置
        settings_widget = QWidget()
        settings_widget.setStyleSheet("background: transparent;")
        settings_layout = QHBoxLayout(settings_widget)
        settings_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        settings_layout.setSpacing(16)
        settings_layout.setContentsMargins(0, 0, 0, 0)

        self.spin_work = self._make_spin("work", "专注")
        self.spin_short = self._make_spin("shortBreak", "短休")
        self.spin_long = self._make_spin("longBreak", "长休")

        settings_layout.addLayout(self.spin_work)
        settings_layout.addLayout(self.spin_short)
        settings_layout.addLayout(self.spin_long)

        layout.addWidget(settings_widget)
        layout.addSpacing(8)

        # 统计
        self.stats_label = QLabel(f"已完成 {self.session_count} 个番茄")
        self.stats_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.stats_label.setStyleSheet("font-size: 13px; color: #555; background: transparent;")
        self.stats_label.setFixedHeight(20)
        layout.addWidget(self.stats_label)

        # 连接设置变更
        for spin, mode in [(self.spin_work_inner, "work"),
                           (self.spin_shortBreak_inner, "shortBreak"),
                           (self.spin_longBreak_inner, "longBreak")]:
            spin.valueChanged.connect(lambda val, m=mode: self._on_setting_change(m, val))

    def _make_tab(self, text):
        btn = QPushButton(text)
        btn.setFixedSize(70, 34)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet("""
            QPushButton {
                background: rgba(255,255,255,0.06); color: #777;
                border: none; border-radius: 17px;
                font-size: 13px; font-weight: 500;
            }
            QPushButton:hover { background: rgba(255,255,255,0.1); color: #aaa; }
        """)
        return btn

    def _make_spin(self, mode_key, label_text):
        layout = QHBoxLayout()
        layout.setSpacing(6)
        layout.setContentsMargins(0, 0, 0, 0)

        label = QLabel(label_text)
        label.setStyleSheet("font-size: 13px; color: #666; background: transparent;")

        spin = QSpinBox()
        spin.setFixedSize(52, 28)
        spin.setRange(1, 120 if mode_key != "shortBreak" else 60)
        spin.setValue(self.mode_durations[mode_key])
        spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
        spin.setStyleSheet("""
            QSpinBox {
                background: rgba(255,255,255,0.06); color: #ccc;
                border: none; border-radius: 6px;
                font-size: 13px; padding: 0 2px;
            }
            QSpinBox:focus { selection-background-color: rgba(255,255,255,0.15); }
            QSpinBox::up-button, QSpinBox::down-button { width: 0; border: none; background: transparent; }
        """)

        setattr(self, f"spin_{mode_key}_inner", spin)
        layout.addWidget(label)
        layout.addWidget(spin)
        return layout

    def _setup_shortcuts(self):
        pass  # 通过 keyPressEvent 处理

    # ---- 样式更新 ----

    def _update_tab_styles(self):
        is_break = self.current_mode != "work"
        for tab, mode in [(self.tab_work, "work"),
                          (self.tab_short, "shortBreak"),
                          (self.tab_long, "longBreak")]:
            active = mode == self.current_mode
            if active:
                if is_break:
                    tab.setStyleSheet("""
                        QPushButton {
                            background: #4a9eff; color: #fff;
                            border: none; border-radius: 17px;
                            font-size: 13px; font-weight: 500;
                        }
                    """)
                else:
                    tab.setStyleSheet("""
                        QPushButton {
                            background: #e25555; color: #fff;
                            border: none; border-radius: 17px;
                            font-size: 13px; font-weight: 500;
                        }
                    """)
            else:
                tab.setStyleSheet("""
                    QPushButton {
                        background: rgba(255,255,255,0.06); color: #777;
                        border: none; border-radius: 17px;
                        font-size: 13px; font-weight: 500;
                    }
                    QPushButton:hover { background: rgba(255,255,255,0.1); color: #aaa; }
                """)

    def _update_main_btn_style(self):
        is_break = self.current_mode != "work"
        if is_break:
            self.btn_main.setStyleSheet("""
                QPushButton {
                    background: #4a9eff; color: #fff;
                    border: none; border-radius: 10px;
                    font-size: 15px; font-weight: 600;
                }
                QPushButton:hover { filter: brightness(1.1); }
            """)
        else:
            self.btn_main.setStyleSheet("""
                QPushButton {
                    background: #e25555; color: #fff;
                    border: none; border-radius: 10px;
                    font-size: 15px; font-weight: 600;
                }
                QPushButton:hover { filter: brightness(1.1); }
            """)

    # ---- 核心逻辑 ----

    def _update_ring_display(self):
        m = self.remaining // 60
        s = self.remaining % 60
        text = f"{m:02d}:{s:02d}"
        self.ring.set_time_text(text)
        progress = self.remaining / self.total_seconds if self.total_seconds > 0 else 0
        self.ring.set_progress(progress)

    def _update_ui_state(self):
        is_break = self.current_mode != "work"
        self.ring.set_break_mode(is_break)
        self.status_label.setText({
            "work": "专注时间",
            "shortBreak": "短休时间",
            "longBreak": "长休时间",
        }[self.current_mode])
        self.stats_label.setText(f"已完成 {self.session_count} 个番茄")
        self._update_tab_styles()
        self._update_main_btn_style()

    def _load_mode(self, mode):
        if self.is_running:
            return
        self.current_mode = mode
        d = self.mode_durations[mode]
        self.total_seconds = d * 60
        self.remaining = self.total_seconds
        self._stop_timer()
        self._update_ring_display()
        self._update_ui_state()
        self.btn_main.setText("开始")
        self.is_running = False

    def _tick(self):
        if self.remaining <= 0:
            self._stop_timer()
            self.is_running = False
            if self.current_mode == "work":
                self.session_count += 1
                self.data["sessions"] = self.session_count
                save_data(self.data)
                self.stats_label.setText(f"已完成 {self.session_count} 个番茄")
                next_mode = "longBreak" if self.session_count % 4 == 0 else "shortBreak"
                self.current_mode = next_mode
                d = self.mode_durations[next_mode]
                self.total_seconds = d * 60
                self.remaining = self.total_seconds
                self._update_ring_display()
                self._update_ui_state()
                self.btn_main.setText("开始")
                play_notification()
            else:
                self.current_mode = "work"
                d = self.mode_durations["work"]
                self.total_seconds = d * 60
                self.remaining = self.total_seconds
                self._update_ring_display()
                self._update_ui_state()
                self.btn_main.setText("开始")
                play_notification()
            return

        self.remaining -= 1
        self._update_ring_display()

    def _stop_timer(self):
        if self.timer.isActive():
            self.timer.stop()

    def _toggle_timer(self):
        if self.is_running:
            self._stop_timer()
            self.btn_main.setText("继续")
            self.is_running = False
            return

        if self.remaining <= 0:
            self._load_mode(self.current_mode)
            return

        self.timer.start(1000)
        self.btn_main.setText("暂停")
        self.is_running = True

    def _reset_timer(self):
        self._stop_timer()
        d = self.mode_durations[self.current_mode]
        self.total_seconds = d * 60
        self.remaining = self.total_seconds
        self._update_ring_display()
        self.btn_main.setText("开始")
        self.is_running = False

    def _on_setting_change(self, mode, value):
        self.mode_durations[mode] = value
        self.data[mode] = value
        save_data(self.data)
        if not self.is_running and mode == self.current_mode:
            self.total_seconds = value * 60
            self.remaining = self.total_seconds
            self._update_ring_display()

    # ---- 快捷键 ----

    def keyPressEvent(self, event):
        if event.isAutoRepeat():
            super().keyPressEvent(event)
            return
        # 如果焦点在 SpinBox 内，忽略快捷键
        if isinstance(self.focusWidget(), QSpinBox):
            super().keyPressEvent(event)
            return
        if event.key() == Qt.Key.Key_Space:
            self._toggle_timer()
        elif event.key() == Qt.Key.Key_R:
            self._reset_timer()
        else:
            super().keyPressEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PomodoroApp()
    window.show()
    sys.exit(app.exec())
