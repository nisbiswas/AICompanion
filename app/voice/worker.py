from PySide6.QtCore import QObject, Signal, Slot

from app.voice.player import AudioPlayer
from app.voice.tts import TTSClient
from app.ai.cancellation import request_scope, RequestCancelled
from app.ai.cancellation import CancellationToken
import time


class VoiceWorker(QObject):
    finished = Signal()
    error = Signal(str)

    def __init__(self):
        super().__init__()

        self.tts = TTSClient()
        self.player = AudioPlayer()

    started = Signal(str)
    ended = Signal(str)
    level = Signal(str, float)

    @Slot()
    def prepare_acknowledgements(self):
        token = CancellationToken(deadline=time.monotonic() + 3)
        try:
            with request_scope(token):
                for text in ("Hmm... taking a look.", "Let me picture that for a moment."):
                    try:
                        self.tts.speak(text, speed=self.get_speed("THINKING"), cache=True)
                    except Exception as exc:
                        print(f"Acknowledgement cache not ready: {exc}")
        except RequestCancelled:
            pass  # Never hold up the first real utterance for a slow warm-up.

    @Slot(object)
    def speak_item(self, item):
        audio_path = None
        try:
            with request_scope(item["token"]):
                audio_path = self.tts.speak(item["text"], speed=self.get_speed(item["emotion"]),
                                           cache=item.get("kind") == "ack")
                item["token"].check()
                if audio_path:
                    def on_started():
                        item["token"].check()
                        # Expiry guards synthesis/queued speech. Once playback
                        # starts, only an explicit cancellation should cut it off.
                        item["token"].deadline = None
                        self.started.emit(item["id"])
                    self.player.play(audio_path, on_started=on_started,
                                     on_level=lambda level: self.level.emit(item["id"], level))
            self.finished.emit()
        except RequestCancelled:
            pass
        except Exception as exc:
            if not item["token"].cancelled:
                self.error.emit(str(exc))
        finally:
            if audio_path:
                self.tts.release(audio_path)
            self.ended.emit(item["id"])

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
