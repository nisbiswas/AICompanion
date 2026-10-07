from PySide6.QtCore import Qt, QPoint, Signal
from PySide6.QtWidgets import QWidget, QLineEdit, QPushButton


class ChatInput(QWidget):
    submitted = Signal(str)
    cancelled = Signal()
    research_changed = Signal(bool)
    microphone_requested = Signal()

    WIDTH = 420
    HEIGHT = 48

    def __init__(self, parent=None):
        super().__init__(parent)

        self.dragging = False
        self.drag_offset = QPoint()

        self.setFixedSize(
            self.WIDTH,
            self.HEIGHT,
        )

        # =====================================================
        # INPUT
        # =====================================================

        self.input = QLineEdit(self)

        self.input.setPlaceholderText(
            "Speak to Hornet..."
        )

        self.input.setClearButtonEnabled(
            True
        )

        self.input.setGeometry(
            0,
            0,
            self.WIDTH,
            self.HEIGHT,
        )

        self.input.setStyleSheet("""
            QLineEdit {
                background-color: rgba(18, 18, 24, 245);
                color: #F2F2F5;

                border: 2px solid rgba(220, 220, 230, 170);
                border-radius: 14px;

                padding-left: 16px;
                padding-right: 128px;

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

        # =====================================================
        # MICROPHONE BUTTON
        # =====================================================

        self.microphone_button = QPushButton(
            "🎙",
            self,
        )

        self.microphone_button.setFixedSize(
            32,
            32,
        )

        self.microphone_button.move(
            self.WIDTH - 136,
            8,
        )

        self.microphone_button.setToolTip(
            "Speak to Hornet"
        )

        self.microphone_button.setStyleSheet("""
            QPushButton {
                background-color: rgba(55, 55, 65, 230);
                color: #E8E8EF;

                border: 1px solid rgba(190, 190, 205, 120);
                border-radius: 10px;

                font-family: "Segoe UI";
                font-size: 16px;
                font-weight: 600;
            }

            QPushButton:hover {
                background-color: rgba(75, 75, 88, 240);
            }

            QPushButton:pressed {
                background-color: rgba(95, 125, 165, 245);
                border: 1px solid rgba(220, 230, 245, 220);
            }
        """)

        self.microphone_button.clicked.connect(
            self.microphone_requested.emit
        )

        # =====================================================
        # RESEARCH BUTTON
        # =====================================================

        self.research_button = QPushButton(
            "Research",
            self,
        )

        self.research_button.setCheckable(
            True
        )

        self.research_button.setFixedSize(
            92,
            32,
        )

        self.research_button.move(
            self.WIDTH - 102,
            8,
        )

        self.research_button.setStyleSheet("""
            QPushButton {
                background-color: rgba(55, 55, 65, 230);
                color: #D8D8E0;

                border: 1px solid rgba(190, 190, 205, 120);
                border-radius: 10px;

                font-family: "Segoe UI";
                font-size: 13px;
                font-weight: 600;
            }

            QPushButton:hover {
                background-color: rgba(75, 75, 88, 240);
            }

            QPushButton:checked {
                background-color: rgba(95, 125, 165, 245);
                color: white;

                border: 1px solid rgba(220, 230, 245, 220);
            }

            QPushButton:checked:hover {
                background-color: rgba(110, 140, 180, 250);
            }
        """)

        self.research_button.toggled.connect(
            self.research_changed.emit
        )

        self.input.returnPressed.connect(
            self.submit
        )

    # =========================================================
    # SUBMIT
    # =========================================================

    def submit(self):

        text = self.input.text().strip()

        if not text:
            return

        self.input.clear()

        self.submitted.emit(
            text
        )

    # =========================================================
    # MICROPHONE
    # =========================================================

    def set_microphone_enabled(
        self,
        enabled: bool,
    ):

        self.microphone_button.setEnabled(
            enabled
        )

    # =========================================================
    # RESEARCH
    # =========================================================

    def research_enabled(self) -> bool:
        return self.research_button.isChecked()

    def set_research_enabled(self, enabled: bool):

        self.research_button.setChecked(
            enabled
        )

    # =========================================================
    # KEYBOARD
    # =========================================================

    def keyPressEvent(self, event):

        if event.key() == Qt.Key_Escape:

            self.cancelled.emit()

            self.input.clear()

            self.hide()

            return

        super().keyPressEvent(event)

    # =========================================================
    # DRAGGING
    # =========================================================

    def mousePressEvent(self, event):

        if event.button() == Qt.LeftButton:

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

            self.move_within_screen(
                new_position
            )

            event.accept()

            return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):

        if event.button() == Qt.LeftButton:

            self.dragging = False

        super().mouseReleaseEvent(event)

    # =========================================================
    # SCREEN BOUNDARY
    # =========================================================

    def move_within_screen(
        self,
        position: QPoint,
    ):

        screen = self.screen()

        if screen is None:

            self.move(position)

            return

        available = (
            screen.availableGeometry()
        )

        x = max(
            available.left(),
            min(
                position.x(),
                available.right()
                - self.width()
                + 1,
            ),
        )

        y = max(
            available.top(),
            min(
                position.y(),
                available.bottom()
                - self.height()
                + 1,
            ),
        )

        self.move(
            x,
            y,
        )