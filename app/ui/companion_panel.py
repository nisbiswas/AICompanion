"""A fixed desktop stage with expressive pose animation and natural idle motion."""
import math
from pathlib import Path
import time

from PySide6.QtCore import Qt, QTimer, Signal, QRectF
from PySide6.QtGui import QColor, QFont, QPainter, QPixmap
from PySide6.QtWidgets import QApplication, QPushButton, QWidget


class CompanionPanel(QWidget):
    clicked = Signal()
    stop_requested = Signal()
    POSES = {
        "NEUTRAL": [0], "THINKING": [2, 3], "CURIOUS": [3, 2],
        "EXPLAINING": [4, 5, 6, 7], "PRESENTING": [6, 7],
        "HAPPY": [8, 9], "PLAYFUL": [8, 9], "ANNOYED": [10, 11],
        "SHY": [12, 13], "SAD": [14], "SURPRISED": [15],
    }

    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(300, 340)
        self.atlas = QPixmap(str(Path(__file__).resolve().parents[2] / "assets/character/companion/expressions-v1.png"))
        if self.atlas.isNull():
            raise RuntimeError("Companion sprite atlas is missing.")
        self.frames = []
        for i in range(16):
            column, row = i % 4, i // 4
            left, right = round(column * self.atlas.width() / 4), round((column + 1) * self.atlas.width() / 4)
            top, bottom = round(row * self.atlas.height() / 4), round((row + 1) * self.atlas.height() / 4)
            self.frames.append(self.atlas.copy(left, top, right - left, bottom - top))
        self.state, self.speaking, self.changed_at = "NEUTRAL", False, time.monotonic()
        self.voice_level = 0.0
        self.speech_elapsed = 0.0
        self.last_voice_tick = time.monotonic()
        self.caption = "Here with you"
        self.stop_button = QPushButton("Stop", self)
        self.stop_button.setGeometry(232, 22, 54, 25)
        self.stop_button.setStyleSheet("QPushButton {color:#eee; background:#41404e; border:none; border-radius:6px;}")
        self.stop_button.clicked.connect(self.stop_requested.emit)
        self.stop_button.hide()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update)
        self.timer.start(33)
        screen = QApplication.primaryScreen()
        screen.availableGeometryChanged.connect(self.anchor)
        self.anchor()

    def anchor(self, *_):
        screen = self.screen() or QApplication.primaryScreen()
        area = screen.availableGeometry()
        self.move(area.right() - self.width() - 12, area.bottom() - self.height() - 8)

    def set_state(self, state, caption=None):
        if state != self.state:
            self.changed_at = time.monotonic()
        self.state = state if state in self.POSES else "NEUTRAL"
        if caption:
            self.caption = caption
        self.update()

    def set_speaking(self, speaking):
        if speaking and not self.speaking:
            self.speech_elapsed = 0.0
            self.last_voice_tick = time.monotonic()
        self.speaking = speaking
        if not speaking:
            self.voice_level = 0.0
        self.update()

    def set_voice_level(self, level):
        now = time.monotonic()
        if self.speaking and level > 0.08:
            self.speech_elapsed += min(0.1, max(0, now - self.last_voice_tick))
        self.last_voice_tick = now
        self.voice_level = max(0.0, min(1.0, level))
        self.update()

    def current_pose(self):
        elapsed = time.monotonic() - self.changed_at
        state = self.state
        if elapsed > 8 and state != "THINKING" and not self.speaking:
            state = "NEUTRAL"
        poses = self.POSES[state]
        if self.speaking:
            if state == "EXPLAINING":
                # The two explanation frames include a closed/open-mouth pair.
                # Actual audible amplitude, rather than TTS synthesis time,
                # selects that frame; pauses hold the gesture clock still.
                if int(self.speech_elapsed / 2.4) % 2 == 0:
                    return 5 if self.voice_level > 0.16 else 4
                return poses[2 + int(self.speech_elapsed / 0.8) % 2]
            return poses[int(self.speech_elapsed / 0.8) % len(poses)]
        # Before speech starts, an emotional pose is still. Only thinking and
        # normal idle breathing/blinking animate during synthesis.
        frame = poses[int(elapsed / 1.15) % len(poses)] if state == "THINKING" else poses[0]
        if state == "NEUTRAL" and elapsed % 4.6 > 4.42:
            frame = 1
        return frame

    def set_busy(self, busy):
        self.stop_button.setVisible(busy)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(18, 18, 27, 230))
        painter.drawRoundedRect(QRectF(3, 14, self.width() - 6, self.height() - 17), 22, 22)
        frame = self.current_pose()
        bob = math.sin(time.monotonic() * 1.8) * 1.8
        painter.drawPixmap(QRectF(0, 20 + bob, 300, 300), self.frames[frame], QRectF(self.frames[frame].rect()))
        painter.setPen(QColor("#ded5c3"))
        painter.setFont(QFont("Segoe UI", 10))
        painter.drawText(QRectF(12, 312, 276, 22), Qt.AlignCenter, self.caption)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
