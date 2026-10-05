from PySide6.QtCore import QObject, Signal, Slot

from app.character.controller import CharacterController


class AIWorker(QObject):

    finished = Signal(object)
    error = Signal(str)

    def __init__(self):
        super().__init__()

        self.controller = CharacterController()

    @Slot(str)
    def process(self, message: str):

        try:
            response = self.controller.respond_to_user(
                message
            )

            self.finished.emit(response)

        except Exception as exc:
            self.error.emit(str(exc))