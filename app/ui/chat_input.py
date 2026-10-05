from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QLineEdit


class ChatInput(QLineEdit):
    submitted = Signal(str)
    cancelled = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setPlaceholderText("Talk to Hornet...")
        self.setFixedWidth(280)
        self.setFixedHeight(38)

        self.setStyleSheet("""
            QLineEdit {
                background-color: rgba(30, 30, 30, 245);
                color: white;
                border: 2px solid white;
                border-radius: 10px;
                padding: 6px 12px;
                font-size: 15px;
            }

            QLineEdit:focus {
                border: 2px solid #cccccc;
            }
        """)

        self.returnPressed.connect(self.submit)

    def submit(self):
        text = self.text().strip()

        if not text:
            return

        self.submitted.emit(text)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.cancelled.emit()
            self.clear()
            self.hide()
            return

        super().keyPressEvent(event)