from pathlib import Path
import json

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices, QFont, QPixmap
from PySide6.QtWidgets import QDialog, QLabel, QPushButton, QTextEdit, QVBoxLayout


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
        metadata_file = Path(image_path).with_suffix(".json")
        self.metadata_text = ""
        if metadata_file.is_file():
            try:
                data = json.loads(metadata_file.read_text(encoding="utf-8"))
                self.metadata_text = json.dumps(data, indent=2, ensure_ascii=False)
                info = QLabel(f"{data['width']} × {data['height']} · Seed {data['seed']} · {data.get('elapsed_seconds', '?')}s")
                layout.addWidget(info)
                details = QPushButton("View original prompt and generation settings")
                details.clicked.connect(self.show_details)
                layout.addWidget(details)
            except (OSError, ValueError, KeyError):
                pass
        button = QPushButton("Open image folder")
        button.clicked.connect(lambda: QDesktopServices.openUrl(
            QUrl.fromLocalFile(str(Path(image_path).parent))
        ))
        layout.addWidget(button)
        self.resize(620, 760)

    def show_details(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Image prompt and settings")
        layout = QVBoxLayout(dialog)
        text = QTextEdit()
        text.setReadOnly(True)
        text.setPlainText(self.metadata_text)
        layout.addWidget(text)
        dialog.resize(700, 600)
        dialog.exec()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.label.setPixmap(self.image.scaled(
            max(1, self.width() - 40), max(1, self.height() - 190),
            Qt.KeepAspectRatio, Qt.SmoothTransformation,
        ))
