import tempfile
import os

import sounddevice as sd
import soundfile as sf
from faster_whisper import WhisperModel


class SpeechToText:

    SAMPLE_RATE = 16000

    def __init__(self):
        print("Loading Whisper model...")

        self.model = WhisperModel(
            "small",
            device="cpu",
            compute_type="int8",
        )

        print("Whisper model loaded.")

    def record(self, seconds: float = 5.0):

        print("Listening...")

        audio = sd.rec(
            int(seconds * self.SAMPLE_RATE),
            samplerate=self.SAMPLE_RATE,
            channels=1,
            dtype="float32",
        )

        sd.wait()

        print("Recording finished.")

        return audio

    def transcribe(self, audio):

        with tempfile.NamedTemporaryFile(
            suffix=".wav",
            delete=False,
        ) as temp_file:

            temp_path = temp_file.name

        try:

            sf.write(
                temp_path,
                audio,
                self.SAMPLE_RATE,
            )

            segments, _ = self.model.transcribe(
                temp_path,
                language="en",
                vad_filter=True,
            )

            text = " ".join(
                segment.text.strip()
                for segment in segments
            ).strip()

            return text

        finally:

            if os.path.exists(temp_path):
                os.remove(temp_path)

    def listen_and_transcribe(
        self,
        seconds: float = 5.0,
    ):

        audio = self.record(seconds)

        return self.transcribe(audio)