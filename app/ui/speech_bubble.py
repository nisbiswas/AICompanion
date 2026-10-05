from PySide6.QtCore import Qt, QPoint
from PySide6.QtWidgets import (
    QWidget,
    QLabel,
    QVBoxLayout,
    QFrame,
    QGraphicsDropShadowEffect,
)


class SpeechBubble(QWidget):
    WIDTH = 560
    MIN_HEIGHT = 110
    MAX_HEIGHT = 300

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
        )

        self.setAttribute(Qt.WA_TranslucentBackground)

        # Used for dragging
        self.dragging = False
        self.drag_offset = QPoint()
        self.has_been_positioned = False

        self.container = QFrame(self)
        self.container.setObjectName("speechContainer")

        self.container.setStyleSheet("""
            QFrame#speechContainer {
                background-color: rgba(18, 18, 24, 245);
                border: 2px solid rgba(220, 220, 230, 180);
                border-radius: 18px;
            }
        """)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(28)
        shadow.setOffset(0, 6)
        shadow.setColor(Qt.black)

        self.container.setGraphicsEffect(shadow)

        self.text = QLabel()
        self.text.setWordWrap(True)
        self.text.setAlignment(
            Qt.AlignLeft | Qt.AlignVCenter
        )

        self.text.setStyleSheet("""
            QLabel {
                color: #F2F2F5;
                background: transparent;
                border: none;
                padding: 18px 22px;
                font-size: 18px;
                font-family: "Segoe UI";
            }
        """)

        self.layout = QVBoxLayout(self.container)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(self.text)

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(8, 8, 8, 8)
        outer_layout.addWidget(self.container)

        self.setFixedWidth(self.WIDTH)

        self.hide()

    # ---------------------------------------------------------
    # DISPLAY
    # ---------------------------------------------------------

    def say(self, message: str):
        self.text.setText(message)

        self.text.adjustSize()

        document_height = self.text.height() + 36

        height = max(
            self.MIN_HEIGHT,
            min(document_height, self.MAX_HEIGHT),
        )

        self.setFixedHeight(height)

        self.show()
        self.raise_()

    # ---------------------------------------------------------
    # POSITIONING
    # ---------------------------------------------------------

    def position_near(self, character_window):
        screen = character_window.screen()

        if screen is None:
            return

        available = screen.availableGeometry()

        character_rect = character_window.frameGeometry()

        # Prefer above Hornet.
        x = character_rect.center().x() - self.width() // 2
        y = character_rect.top() - self.height() - 15

        # Keep inside the screen horizontally.
        if x < available.left() + 10:
            x = available.left() + 10

        if x + self.width() > available.right() - 10:
            x = available.right() - self.width() - 10

        # If there isn't room above Hornet, put it below.
        if y < available.top() + 10:
            y = character_rect.bottom() + 15

        # Final vertical safety.
        if y + self.height() > available.bottom() - 10:
            y = available.bottom() - self.height() - 10

        self.move(x, y)

        self.has_been_positioned = True

    def say_near(self, message: str, character_window):
        self.say(message)

        # Automatically position only the first time.
        if not self.has_been_positioned:
            self.position_near(character_window)

        self.show()
        self.raise_()

    # ---------------------------------------------------------
    # DRAGGING
    # ---------------------------------------------------------

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
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
            event.accept()
            return

        super().mouseReleaseEvent(event)

    def move_within_screen(self, position: QPoint):
        screen = self.screen()

        if screen is None:
            self.move(position)
            return

        available = screen.availableGeometry()

        x = position.x()
        y = position.y()

        # Prevent dragging outside the monitor.
        x = max(
            available.left(),
            min(
                x,
                available.right() - self.width() + 1,
            ),
        )

        y = max(
            available.top(),
            min(
                y,
                available.bottom() - self.height() + 1,
            ),
        )

        self.move(x, y)

    # ---------------------------------------------------------
    # HIDE
    # ---------------------------------------------------------

    def hide_bubble(self):
        self.hide()