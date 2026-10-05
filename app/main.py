import sys

from PySide6.QtWidgets import QApplication

from app.character.controller import CharacterController
from app.ui.character_window import CharacterWindow


def main():

    # ---------------------------------------------------------
    # Qt application
    # ---------------------------------------------------------

    app = QApplication(sys.argv)

    # ---------------------------------------------------------
    # Character controller
    # ---------------------------------------------------------

    controller = CharacterController()

    # ---------------------------------------------------------
    # Character window
    # ---------------------------------------------------------

    window = CharacterWindow(
        controller
    )

    window.show()

    # ---------------------------------------------------------
    # Start application
    # ---------------------------------------------------------

    sys.exit(
        app.exec()
    )


if __name__ == "__main__":
    main()