from PySide6.QtCore import QObject, Signal, Slot

from app.voice.player import AudioPlayer
from app.voice.tts import TTSClient


class VoiceWorker(QObject):
    finished = Signal()
    error = Signal(str)

    def __init__(self):
        super().__init__()

        self.tts = TTSClient()
        self.player = AudioPlayer()

    @Slot(str, str)
    def speak(self, text: str, emotion: str):
        try:
            text = text.strip()

            if not text:
                self.finished.emit()
                return

            speed = self.get_speed(emotion)

            audio_path = self.tts.speak(
                text,
                speed=speed,
            )

            if audio_path:
                self.player.play(audio_path)

            self.finished.emit()

        except Exception as exc:
            self.error.emit(str(exc))

    def get_speed(self, emotion: str) -> float:
        emotion = emotion.upper()

        speeds = {
            "NEUTRAL": 1.0,
            "HAPPY": 1.08,
            "SHY": 0.95,
            "ANNOYED": 1.05,
            "SAD": 0.88,
            "CURIOUS": 1.02,
            "SURPRISED": 1.12,
            "THINKING": 0.92,
        }

        return speeds.get(
            emotion,
            1.0,
        )