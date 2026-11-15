from PySide6.QtCore import Qt, QPoint, QEvent, Signal
from PySide6.QtGui import QTextOption
from app.ai.response import readable_reply, has_readable_text
from PySide6.QtWidgets import (
    QWidget, QTextEdit, QVBoxLayout, QHBoxLayout, QFrame, QLabel,
    QPushButton, QSizeGrip,
)


class SpeechBubble(QWidget):
    dismissed = Signal()
    stop_requested = Signal()
    WIDTH = 560
    MIN_HEIGHT = 180
    MAX_HEIGHT = 480  # Initial auto-fit cap; manual resizing is unrestricted.

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMinimumSize(360, self.MIN_HEIGHT)
        self.resize(self.WIDTH, 240)
        self.dragging = False
        self.drag_offset = QPoint()
        self.has_been_positioned = False
        self.user_resized = False
        self._automatic_resize = False
        self._restore_geometry = None
        self.header = self.title = self.resize_grip = None

        self.container = QFrame(self)
        self.container.setObjectName("speechContainer")
        self.container.setStyleSheet("""
            QFrame#speechContainer {
                background-color: rgba(18, 18, 24, 248);
                border: 2px solid rgba(220, 220, 230, 180);
                border-radius: 16px;
            }
            QLabel { color: #B7B7C7; background: transparent; border: none; }
            QPushButton { color: #eee; background: #333340; border: none;
                          border-radius: 6px; padding: 4px;
                          font-family: "Segoe UI"; font-size: 12px; }
            QPushButton:hover { background: #505065; }
        """)
        content_layout = QVBoxLayout(self.container)
        content_layout.setContentsMargins(10, 8, 10, 6)
        content_layout.setSpacing(4)

        self.header = QWidget()
        self.header.setCursor(Qt.SizeAllCursor)
        self.header.installEventFilter(self)
        header_layout = QHBoxLayout(self.header)
        header_layout.setContentsMargins(4, 0, 0, 0)
        self.title = QLabel("Hornet")
        self.title.setStyleSheet('font-family: "Segoe UI"; font-size: 12px;')
        self.title.installEventFilter(self)
        header_layout.addWidget(self.title)
        header_layout.addStretch()
        self.stop_button = QPushButton("Stop")
        self.stop_button.setToolTip("Cancel the current request (Esc)")
        self.stop_button.clicked.connect(self.stop_requested.emit)
        self.stop_button.hide()
        self.maximize_button = QPushButton("Expand")
        self.maximize_button.setFixedSize(62, 26)
        self.maximize_button.setToolTip("Maximize output (or double-click the header)")
        self.maximize_button.clicked.connect(self.toggle_maximize)
        self.close_button = QPushButton("×")
        self.close_button.setFixedSize(28, 26)
        self.close_button.setToolTip("Dismiss this response")
        self.close_button.clicked.connect(self.dismiss)
        for button in (self.stop_button, self.maximize_button, self.close_button):
            header_layout.addWidget(button)
        content_layout.addWidget(self.header)

        self.text = QTextEdit()
        self.text.setReadOnly(True)
        self.text.setUndoRedoEnabled(False)
        self.text.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
        self.text.setFocusPolicy(Qt.StrongFocus)
        self.text.setFrameStyle(QFrame.NoFrame)
        self.text.setMinimumSize(0, 0)
        self.text.setLineWrapMode(QTextEdit.WidgetWidth)
        self.text.setWordWrapMode(QTextOption.WrapAtWordBoundaryOrAnywhere)
        self.text.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.text.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.text.setStyleSheet("""
            QTextEdit {
                color: #F2F2F5; background: transparent; border: none;
                padding: 8px 10px; font-size: 18px; font-family: "Segoe UI";
            }
            QScrollBar:vertical { background: #22222e; width: 12px; }
            QScrollBar:horizontal { background: #22222e; height: 12px; }
            QScrollBar::handle { background: #85859c; border-radius: 4px; min-height: 24px; min-width: 24px; }
            QScrollBar::add-line, QScrollBar::sub-line { width: 0px; height: 0px; }
        """)
        content_layout.addWidget(self.text, 1)
        footer = QHBoxLayout()
        footer.setContentsMargins(4, 0, 0, 0)
        hint = QLabel("Drag corner to resize")
        hint.setStyleSheet('font-family: "Segoe UI"; font-size: 11px; color: #9898AB;')
        footer.addWidget(hint)
        footer.addStretch()
        self.resize_grip = QSizeGrip(self.container)
        self.resize_grip.setFixedSize(22, 22)
        self.resize_grip.setToolTip("Drag to make the output window larger or smaller")
        self.resize_grip.installEventFilter(self)
        footer.addWidget(self.resize_grip)
        content_layout.addLayout(footer)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(4, 4, 4, 4)
        outer.addWidget(self.container)
        self.hide()

    def say(self, message):
        self._automatic_resize = True
        try:
            message = readable_reply(message)
            self.text.setMarkdown(message)
            # Even a nonempty Markdown source can render without visible text
            # (for example an empty link). Preserve the source as plain text.
            if not has_readable_text(self.text.toPlainText()):
                self.text.setPlainText(message)
            self.show()
            self.layout().activate()
            self.container.layout().activate()
            if not self.user_resized and not self.isMaximized():
                # Measure a clone using the actual viewport. QTextEdit alone owns
                # the live document's width; a fixed width there breaks wrapping.
                probe = self.text.document().clone()
                probe.setTextWidth(max(1, self.text.viewport().width()))
                document_height = probe.documentLayout().documentSize().height()
                chrome_height = self.height() - self.text.viewport().height()
                screen = self.screen()
                cap = min(self.MAX_HEIGHT, screen.availableGeometry().height() - 20) if screen else self.MAX_HEIGHT
                height = max(self.MIN_HEIGHT, min(int(document_height + chrome_height + 12), cap))
                self.resize(self.width(), height)
                probe.deleteLater()
            self.keep_on_screen()
            self.text.verticalScrollBar().setValue(0)
            self.text.horizontalScrollBar().setValue(0)
            self.raise_()
        finally:
            self._automatic_resize = False

    def resizeEvent(self, event):
        if self.isVisible() and not self._automatic_resize:
            self.user_resized = True
        super().resizeEvent(event)

    def toggle_maximize(self):
        self.user_resized = True
        if self.isMaximized():
            geometry = self._restore_geometry or self.normalGeometry()
            self.showNormal()
            self.setGeometry(geometry)
            self.keep_on_screen()
        else:
            self._restore_geometry = self.geometry()
            self.showMaximized()
        self._update_maximize_control()

    def _update_maximize_control(self):
        maximized = self.isMaximized()
        self.maximize_button.setText("Restore" if maximized else "Expand")
        self.maximize_button.setToolTip("Restore output size" if maximized else "Maximize output (or double-click the header)")
        self.resize_grip.setVisible(not maximized)

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == QEvent.WindowStateChange and hasattr(self, "maximize_button"):
            self._update_maximize_control()

    def set_busy(self, busy):
        self.stop_button.setVisible(busy)

    def dismiss(self):
        self.hide()
        self.dismissed.emit()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.stop_requested.emit()
            return
        super().keyPressEvent(event)

    def position_near(self, character_window):
        if self.isMaximized():
            return
        rect = character_window.frameGeometry()
        self.move(rect.center().x() - self.width() // 2, rect.top() - self.height() - 15)
        self.keep_on_screen(character_window.screen())
        self.has_been_positioned = True

    def say_near(self, message, character_window):
        self.say(message)
        if not self.has_been_positioned:
            self.position_near(character_window)
        else:
            self.keep_on_screen()

    def keep_on_screen(self, screen=None):
        if self.isMaximized():
            return
        screen = screen or self.screen()
        if screen is None:
            return
        area = screen.availableGeometry().adjusted(8, 8, -8, -8)
        if self.width() > area.width() or self.height() > area.height():
            automatic = self._automatic_resize
            self._automatic_resize = True
            self.resize(min(self.width(), area.width()), min(self.height(), area.height()))
            self._automatic_resize = automatic
        self.move(max(area.left(), min(self.x(), area.right() - self.width() + 1)),
                  max(area.top(), min(self.y(), area.bottom() - self.height() + 1)))

    def eventFilter(self, watched, event):
        if watched is getattr(self, "resize_grip", None) and event.type() == QEvent.MouseButtonPress:
            self.user_resized = True
        if watched in (getattr(self, "header", None), getattr(self, "title", None)):
            if event.type() == QEvent.MouseButtonDblClick and event.button() == Qt.LeftButton:
                self.toggle_maximize()
                return True
            if event.type() == QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
                if not self.isMaximized():
                    self.dragging = True
                    self.drag_offset = event.globalPosition().toPoint() - self.pos()
                return True
            if event.type() == QEvent.MouseMove and self.dragging:
                self.move_within_screen(event.globalPosition().toPoint() - self.drag_offset)
                return True
            if event.type() == QEvent.MouseButtonRelease:
                self.dragging = False
        return super().eventFilter(watched, event)

    def move_within_screen(self, position: QPoint):
        self.move(position)
        self.keep_on_screen()

    def hide_bubble(self):
        self.hide()
