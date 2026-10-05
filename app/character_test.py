import sys

from PySide6.QtWidgets import QApplication

from app.character.controller import CharacterController
from app.ui.character_window import CharacterWindow


def main():
    app = QApplication(sys.argv)

    controller = CharacterController()
    window = CharacterWindow(controller)

    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()