from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices, QFont, QPixmap
from PySide6.QtWidgets import QDialog, QLabel, QPushButton, QVBoxLayout


class ImagePreview(QDialog):
    def __init__(self, image_path: str, parent=None):
        super().__init__(parent)
        self.setFont(QFont("Segoe UI", 10))
        self.setWindowTitle("Hornet — Generated image")
        self.setWindowFlag(Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setMinimumSize(320, 320)
        self.image = QPixmap(image_path)
        if self.image.isNull():
            raise ValueError(f"Unable to open generated image: {image_path}")
        layout = QVBoxLayout(self)
        self.label = QLabel()
        self.label.setMinimumSize(1, 1)
        self.label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.label, 1)
        path = QLabel(image_path)
        path.setWordWrap(True)
        path.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(path)
        button = QPushButton("Open image folder")
        button.clicked.connect(lambda: QDesktopServices.openUrl(
            QUrl.fromLocalFile(str(Path(image_path).parent))
        ))
        layout.addWidget(button)
        self.resize(620, 760)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.label.setPixmap(self.image.scaled(
            max(1, self.width() - 40), max(1, self.height() - 120),
            Qt.KeepAspectRatio, Qt.SmoothTransformation,
        ))
