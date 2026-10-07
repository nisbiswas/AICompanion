from PySide6.QtCore import QObject, Signal, Slot

from app.voice.stt import SpeechToText


class STTWorker(QObject):
    finished = Signal(str)
    error = Signal(str)

    def __init__(self):
        super().__init__()

        self.stt = None

    @Slot()
    def listen(self):
        try:

            if self.stt is None:
                self.stt = SpeechToText()

            text = self.stt.listen_and_transcribe(
                seconds=5
            )

            self.finished.emit(
                text.strip()
            )

        except Exception as exc:

            self.error.emit(
                str(exc)
            )