from PySide6.QtCore import Qt, QPoint, Signal
from PySide6.QtWidgets import QLineEdit


class ChatInput(QLineEdit):
    submitted = Signal(str)
    cancelled = Signal()

    WIDTH = 420
    HEIGHT = 48

    def __init__(self, parent=None):
        super().__init__(parent)

        self.dragging = False
        self.drag_offset = QPoint()

        self.setFixedSize(self.WIDTH, self.HEIGHT)

        self.setPlaceholderText("Speak to Hornet...")
        self.setClearButtonEnabled(True)

        self.setStyleSheet("""
            QLineEdit {
                background-color: rgba(18, 18, 24, 245);
                color: #F2F2F5;

                border: 2px solid rgba(220, 220, 230, 170);
                border-radius: 14px;

                padding-left: 16px;
                padding-right: 42px;

                font-family: "Segoe UI";
                font-size: 17px;
                selection-background-color: rgba(160, 160, 180, 120);
            }

            QLineEdit:hover {
                border: 2px solid rgba(235, 235, 245, 210);
            }

            QLineEdit:focus {
                border: 2px solid rgba(245, 245, 250, 230);
            }
        """)

        self.returnPressed.connect(self.submit)

    # ---------------------------------------------------------
    # SUBMIT
    # ---------------------------------------------------------

    def submit(self):
        text = self.text().strip()

        if not text:
            return

        # Clear immediately so the old message disappears.
        self.clear()

        self.submitted.emit(text)

    # ---------------------------------------------------------
    # KEYBOARD
    # ---------------------------------------------------------

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.cancelled.emit()
            self.clear()
            self.hide()
            return

        super().keyPressEvent(event)

    # ---------------------------------------------------------
    # DRAGGING
    # ---------------------------------------------------------

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:

            # Only begin dragging if the click is near the
            # top edge of the input rather than inside the text area.
            if event.position().y() <= 10:
                self.dragging = True

                self.drag_offset = (
                    event.globalPosition().toPoint()
                    - self.frameGeometry().topLeft()
                )

                self.raise_()
                event.accept()
                return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.dragging:
            new_position = (
                event.globalPosition().toPoint()
                - self.drag_offset
            )

            self.move_within_screen(new_position)

            event.accept()
            return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging = False

        super().mouseReleaseEvent(event)

    # ---------------------------------------------------------
    # SCREEN BOUNDARY
    # ---------------------------------------------------------

    def move_within_screen(self, position: QPoint):
        screen = self.screen()

        if screen is None:
            self.move(position)
            return

        available = screen.availableGeometry()

        x = max(
            available.left(),
            min(
                position.x(),
                available.right() - self.width() + 1,
            ),
        )

        y = max(
            available.top(),
            min(
                position.y(),
                available.bottom() - self.height() + 1,
            ),
        )

        self.move(x, y)