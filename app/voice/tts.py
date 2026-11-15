import httpx
import hashlib
from pathlib import Path
from uuid import uuid4
from app.ai.cancellation import run_async


TTS_URL = "http://127.0.0.1:8765/speak"


class TTSClient:
    def __init__(self, audio_dir=None):
        self.url = TTS_URL
        self.audio_dir = Path(audio_dir) if audio_dir else Path(__file__).resolve().parents[2] / "data/voice"
        self.owned = set()
        self.cached = set()

    def speak(
        self,
        text: str,
        voice: str = "af_heart",
        speed: float = 1.0,
        cache: bool = False,
    ):
        text = text.strip()

        if not text:
            return None
        self.audio_dir.mkdir(parents=True, exist_ok=True)
        key = hashlib.sha256(f"v1|{voice}|{speed}|{text}".encode()).hexdigest()
        destination = self.audio_dir / (f"cached_{key}.wav" if cache else f"speech_{uuid4().hex}.wav")
        if cache and destination.is_file():
            self.cached.add(str(destination))
            return str(destination)

        async def send():
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(self.url, json={"text": text, "voice": voice, "speed": speed})
                response.raise_for_status()
                return response.json()
        data = run_async(send)

        if not data.get("success"):
            raise RuntimeError(
                data.get("error", "TTS failed")
            )

        # Snapshot the WAV before another request can overwrite a legacy
        # server's shared output.wav. The player always receives its own file.
        source = Path(data["audio"])
        payload = source.read_bytes()
        if len(payload) < 12 or payload[:4] != b"RIFF" or payload[8:12] != b"WAVE":
            raise RuntimeError("TTS returned an invalid WAV file.")
        temporary = destination.with_name(f".{destination.name}.{uuid4().hex}.tmp")
        temporary.write_bytes(payload)
        temporary.replace(destination)
        (self.cached if cache else self.owned).add(str(destination))
        return str(destination)

    def release(self, audio_path):
        if str(audio_path) in self.owned:
            Path(audio_path).unlink(missing_ok=True)
            self.owned.discard(str(audio_path))
