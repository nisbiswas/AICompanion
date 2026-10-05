from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel


class SpeechBubble(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
        )

        self.setAttribute(Qt.WA_TranslucentBackground)

        self.setStyleSheet("""
            QLabel {
                background-color: rgba(30, 30, 30, 235);
                color: white;
                border: 2px solid white;
                border-radius: 12px;
                padding: 10px 14px;
                font-size: 16px;
            }
        """)

        self.setAlignment(Qt.AlignCenter)
        self.setWordWrap(True)

    def say(self, text: str):
        self.setText(text)
        self.adjustSize()
        self.show()