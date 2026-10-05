import httpx


TTS_URL = "http://127.0.0.1:8765/speak"


class TTSClient:
    def __init__(self):
        self.url = TTS_URL

    def speak(
        self,
        text: str,
        voice: str = "af_heart",
        speed: float = 1.0,
    ):
        text = text.strip()

        if not text:
            return None

        response = httpx.post(
            self.url,
            json={
                "text": text,
                "voice": voice,
                "speed": speed,
            },
            timeout=None,
        )

        response.raise_for_status()

        data = response.json()

        if not data.get("success"):
            raise RuntimeError(
                data.get("error", "TTS failed")
            )

        return data["audio"]