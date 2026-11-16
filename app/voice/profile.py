"""Local voice identity and restrained pacing, configurable through .env."""
from dataclasses import dataclass
import math
import os


STANDARD_SPEEDS = {
    "NEUTRAL": 1.0, "HAPPY": 1.08, "SHY": .95, "ANNOYED": 1.05,
    "SAD": .88, "CURIOUS": 1.02, "SURPRISED": 1.12, "THINKING": .92,
}
GENTLE_SPEEDS = {
    "NEUTRAL": 1.0, "HAPPY": 1.02, "SHY": .97, "ANNOYED": 1.0,
    "SAD": .96, "CURIOUS": 1.01, "SURPRISED": 1.03, "THINKING": .98,
}


def language_for_voice(voice):
    return "en-gb" if voice.startswith("b") else "en-us"


@dataclass(frozen=True)
class VoiceProfile:
    name: str
    voice: str
    speed: float
    lang: str

    def speed_for(self, emotion):
        speeds = GENTLE_SPEEDS if self.name == "gentle" else STANDARD_SPEEDS
        return round(max(.5, min(2.0, self.speed * speeds.get(emotion.upper(), 1.0))), 3)

    @classmethod
    def from_env(cls, env=None):
        env = os.environ if env is None else env
        name = env.get("TTS_PROFILE", "gentle").strip().lower()
        if name not in {"gentle", "standard"}:
            raise ValueError("TTS_PROFILE must be gentle or standard.")
        voice = env.get("TTS_VOICE", "bf_emma" if name == "gentle" else "af_heart").strip()
        speed = float(env.get("TTS_SPEED", ".90" if name == "gentle" else "1.0"))
        if not voice or not math.isfinite(speed) or not .5 <= speed <= 2.0:
            raise ValueError("TTS_VOICE must be set and TTS_SPEED must be between 0.5 and 2.0.")
        lang = env.get("TTS_LANG", language_for_voice(voice)).strip().lower()
        if lang not in {"en-us", "en-gb"}:
            raise ValueError("TTS_LANG must be en-us or en-gb for the English companion.")
        return cls(name, voice, speed, lang)
