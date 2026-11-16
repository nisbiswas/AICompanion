import asyncio
from pathlib import Path
import tempfile
import unittest
from unittest.mock import AsyncMock, Mock, patch
import wave

from app.voice.profile import VoiceProfile
from app.voice.tts import TTSClient


class VoiceProfileTests(unittest.TestCase):
    def test_gentle_profile_preserves_calm_pacing_across_emotions(self):
        profile = VoiceProfile.from_env({})
        self.assertEqual((profile.voice, profile.lang, profile.speed), ("bf_emma", "en-gb", .90))
        for emotion in ("HAPPY", "ANNOYED", "SAD", "CURIOUS", "SURPRISED", "THINKING", "unknown"):
            self.assertGreaterEqual(profile.speed_for(emotion), .86)
            self.assertLessEqual(profile.speed_for(emotion), .93)

    def test_standard_profile_retains_original_voice_and_pacing(self):
        profile = VoiceProfile.from_env({"TTS_PROFILE": "standard"})
        self.assertEqual((profile.voice, profile.lang), ("af_heart", "en-us"))
        self.assertEqual(profile.speed_for("HAPPY"), 1.08)

    def test_overrides_infer_accent_and_bound_emotional_speed(self):
        profile = VoiceProfile.from_env({"TTS_VOICE": "af_heart", "TTS_SPEED": "2.0"})
        self.assertEqual(profile.lang, "en-us")
        self.assertEqual(profile.speed_for("SURPRISED"), 2.0)
        self.assertEqual(VoiceProfile.from_env({"TTS_VOICE": "bf_isabella"}).lang, "en-gb")

    def test_invalid_settings_fail_with_a_clear_error(self):
        for settings in ({"TTS_SPEED":"nan"}, {"TTS_SPEED":".1"}, {"TTS_PROFILE":"bad"}, {"TTS_LANG":"bad"}):
            with self.subTest(settings=settings), self.assertRaises(ValueError):
                VoiceProfile.from_env(settings)

    def test_client_sends_accent_and_keeps_accent_specific_cache(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.wav"
            with wave.open(str(source), "wb") as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)
                wav.setframerate(24000)
                wav.writeframes(b"\0\0" * 240)
            response = Mock()
            response.json.return_value = {"success":True, "audio":str(source)}
            http = Mock()
            http.post = AsyncMock(return_value=response)
            manager = AsyncMock()
            manager.__aenter__.return_value = http
            with patch("app.voice.tts.httpx.AsyncClient", return_value=manager), \
                    patch("app.voice.tts.run_async", side_effect=lambda fn:asyncio.run(fn())):
                client = TTSClient(Path(directory) / "clips", profile=VoiceProfile.from_env({}))
                british = client.speak("Stay a moment.", cache=True)
                self.assertEqual(http.post.call_args.kwargs["json"], {
                    "text":"Stay a moment.", "voice":"bf_emma", "speed":.90, "lang":"en-gb"})
                self.assertEqual(client.speak("Stay a moment.", cache=True), british)
                self.assertEqual(http.post.call_count, 1)
                american = client.speak("Stay a moment.", lang="en-us", cache=True)
                self.assertNotEqual(american, british)
                client.speak("Hello.", voice="af_heart")
                self.assertEqual(http.post.call_args.kwargs["json"]["lang"], "en-us")
