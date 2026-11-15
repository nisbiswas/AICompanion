from pathlib import Path
import time
import tempfile
import winsound
from app.ai.cancellation import check_cancelled
from app.voice.audio import prepare_audio


class AudioPlayer:
    def stop(self):
        winsound.PlaySound(None, 0)

    def play(self, audio_path, *, on_started=None, on_level=None):
        path = Path(audio_path)
        if not path.is_file():
            raise FileNotFoundError(path)
        audio = prepare_audio(path)
        if not audio.samples or max(audio.levels, default=0) == 0:
            raise RuntimeError("TTS produced a silent audio clip.")
        with tempfile.TemporaryDirectory(prefix="hornet_playback_") as folder:
            prepared = Path(folder) / "speech.wav"
            audio.save(prepared)
            check_cancelled()
            winsound.PlaySound(str(prepared), winsound.SND_FILENAME | winsound.SND_ASYNC)
            started = time.monotonic()
            try:
                if on_started:
                    on_started()
                while time.monotonic() - started < audio.duration:
                    check_cancelled()
                    index = int((time.monotonic() - started) / audio.frame_seconds)
                    if on_level:
                        on_level(audio.levels[min(index, len(audio.levels)-1)] if audio.levels else 0.0)
                    time.sleep(0.02)
            finally:
                self.stop()
                if on_level:
                    on_level(0.0)
