import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from array import array
from contextlib import contextmanager
import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch
import wave
from threading import Event
import time

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QObject, QThread, Slot
from PySide6.QtTest import QTest
from app.ai.cancellation import CancellationToken
from app.ai.response import AgentResponse, AgentState, AgentIntent
from app.browser.context import BrowserContext
from app.ui.character_window import CharacterWindow
from app.voice.audio import prepare_audio
from app.voice.player import AudioPlayer
from app.voice.queue import SpeechQueue
from app.voice.tts import TTSClient
from app.voice.worker import VoiceWorker


def make_wav(path, *, amplitude=800, seconds=.18, padding=0):
    rate = 24000
    samples = array("h", [0] * int(padding * rate))
    samples.extend(round(amplitude * math.sin(i * 2 * math.pi * 180 / rate)) for i in range(int(seconds * rate)))
    samples.extend([0] * int(padding * rate))
    with wave.open(str(path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(rate)
        output.writeframes(samples.tobytes())


class SpeechSequenceTests(unittest.TestCase):
    def test_ack_finishes_before_result_and_progress_never_interrupts(self):
        queue = SpeechQueue()
        ack = queue.enqueue("Taking a look", "THINKING", kind="ack")
        self.assertIsNone(queue.enqueue("Loading", "THINKING", kind="progress"))
        self.assertIsNone(queue.enqueue("The result", "HAPPY", kind="result"))
        self.assertIs(queue.active, ack)
        self.assertFalse(ack["token"].cancelled)
        result = queue.finish(ack["id"])
        self.assertEqual(result["text"], "The result")
        self.assertGreater(result["token"].deadline, 0)

    def test_cancel_removes_ack_and_pending_result(self):
        queue = SpeechQueue()
        ack = queue.enqueue("Taking a look", "THINKING", kind="ack")
        queue.enqueue("Answer", "HAPPY", kind="result")
        answer = queue.pending
        queue.cancel()
        self.assertTrue(ack["token"].cancelled)
        self.assertTrue(answer["token"].cancelled)
        self.assertIsNone(queue.finish(ack["id"]))

    def test_background_voice_cannot_interrupt_an_answer(self):
        queue = SpeechQueue()
        answer = queue.enqueue("Answer", "NEUTRAL")
        self.assertIsNone(queue.enqueue("Page observation", "CURIOUS", kind="context"))
        self.assertIs(queue.active, answer)
        self.assertFalse(answer["token"].cancelled)


class AudioTests(unittest.TestCase):
    def test_quiet_audio_is_boosted_without_clipping(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "quiet.wav"
            make_wav(path)
            audio = prepare_audio(path)
            self.assertGreater(audio.gain, 1)
            self.assertLessEqual(max(abs(x) for x in audio.samples), int(.951 * 32768))

    def test_loud_audio_keeps_peak_headroom(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "loud.wav"
            make_wav(path, amplitude=32700)
            audio = prepare_audio(path)
            self.assertLess(audio.gain, 1)
            self.assertLessEqual(max(abs(x) for x in audio.samples), int(.951 * 32768))

    def test_synthesis_padding_is_trimmed_and_pause_envelope_is_zero(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "padded.wav"
            make_wav(path, seconds=.3, padding=.4)
            audio = prepare_audio(path)
            self.assertLess(audio.duration, .5)
            self.assertIn(0.0, audio.levels)
            self.assertGreater(max(audio.levels), .9)

    def test_playback_start_signal_follows_the_actual_audio_call(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "voice.wav"
            make_wav(path, seconds=.06)
            events, clock = [], [10.0]
            def sound(filename, flags):
                events.append("play" if filename else "stop")
            def advance(seconds):
                clock[0] += seconds
            with patch("app.voice.player.winsound.PlaySound", side_effect=sound), \
                    patch("app.voice.player.time.monotonic", side_effect=lambda:clock[0]), \
                    patch("app.voice.player.time.sleep", side_effect=advance):
                AudioPlayer().play(path, on_started=lambda:events.append("started"),
                                   on_level=lambda value:events.append(value))
            self.assertLess(events.index("play"), events.index("started"))
            self.assertIn("stop", events)
            self.assertEqual(events[-1], 0.0)

    def test_tts_snapshots_legacy_shared_file_and_cache_is_reused(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "output.wav"
            make_wav(source, amplitude=800)
            original = source.read_bytes()
            client = TTSClient(Path(folder) / "client")
            with patch("app.voice.tts.run_async", return_value={"success":True,"audio":str(source)}) as request:
                path = client.speak("Taking a look", cache=True)
                make_wav(source, amplitude=10000)
                self.assertEqual(Path(path).read_bytes(), original)
                self.assertEqual(client.speak("Taking a look", cache=True), path)
                self.assertEqual(request.call_count, 1)
                client.release(path)
                self.assertTrue(Path(path).exists())

    def test_worker_uses_playback_callback_not_synthesis_completion(self):
        worker = VoiceWorker()
        worker.tts, worker.player = Mock(), Mock()
        worker.tts.speak.return_value = "voice.wav"
        events = []
        worker.started.connect(lambda _: events.append("started"))
        worker.ended.connect(lambda _: events.append("ended"))
        token = CancellationToken()
        def play(path, **callbacks):
            self.assertNotIn("started", events)
            callbacks["on_started"]()
            self.assertIsNone(token.deadline)
            callbacks["on_level"](.6)
        worker.player.play.side_effect = play
        worker.speak_item({"id":"voice", "text":"Hello", "emotion":"HAPPY", "token":token})
        self.assertEqual(events, ["started", "ended"])
        worker.tts.release.assert_called_once_with("voice.wav")


class VoiceUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    @contextmanager
    def window(self):
        with patch("app.browser.bridge.BrowserBridge.start"), patch("app.browser.bridge.BrowserBridge.stop"), \
                patch("app.voice.worker.VoiceWorker.prepare_acknowledgements"):
            window = CharacterWindow(None)
            window.work_request.disconnect()
            window.speech_request.disconnect()
            try:
                yield window
            finally:
                window.close()

    def test_actual_submit_restores_ack_and_result_gestures_wait_for_audio(self):
        with self.window() as window:
            window.submit_request("chat", "Explain this")
            ack = window.speech_queue.active
            self.assertEqual(ack["text"], "Hmm... taking a look.")
            self.assertFalse(window.companion.speaking)
            response = AgentResponse("Here is the explanation.", AgentState.TALKING,
                                     AgentIntent.GENERAL_QUESTION, False, voice_line="Here is what it means.")
            window.handle_ai_response(response)
            self.assertIs(window.speech_queue.active, ack)
            self.assertIsNotNone(window.speech_queue.pending)
            self.assertNotEqual(window.companion.state, "EXPLAINING")
            window.voice_started(ack["id"])
            window.voice_ended(ack["id"])
            result = window.speech_queue.active
            self.assertFalse(window.companion.speaking)
            window.voice_started(result["id"])
            self.assertTrue(window.companion.speaking)
            self.assertEqual(window.companion.state, "EXPLAINING")
            window.voice_level(result["id"], .8)
            self.assertEqual(window.companion.current_pose(), 5)
            before = window.companion.speech_elapsed
            window.voice_level(result["id"], 0.0)
            self.assertEqual(window.companion.speech_elapsed, before)
            self.assertEqual(window.companion.current_pose(), 4)
            window.voice_ended(result["id"])
            self.assertFalse(window.companion.speaking)
            self.assertEqual(window.companion.state, "NEUTRAL")

    def test_same_page_dom_refresh_does_not_cut_off_result_voice(self):
        with self.window() as window:
            window.request_busy = False
            window.browser_context.update("Chrome", "Page", "https://example.org", "old text")
            window.latest_browser = window.browser_context.as_dict()
            window.queue_voice("Your answer", "NEUTRAL")
            token = window.voice_token
            event = window.browser_context.update("Chrome", "Page", "https://example.org", "updated text")
            window.handle_browser_event(event)
            self.assertFalse(token.cancelled)
            self.assertIsNotNone(window.speech_queue.active)

    def test_leaving_page_cancels_its_passive_comment(self):
        with self.window() as window:
            window.latest_browser = {"title":"Old page", "url":"https://example.org/old"}
            window.queue_voice("Page comment", "CURIOUS", kind="context")
            token = window.voice_token
            event = window.browser_context.update("Chrome", "New page", "https://example.org/new", "text")
            window.handle_browser_event(event)
            self.assertTrue(token.cancelled)

    def test_worker_playback_updates_the_gui_on_its_own_thread(self):
        with self.window() as window:
            window.voice_worker.tts = Mock()
            window.voice_worker.tts.speak.return_value = "test.wav"
            window.voice_worker.player = Mock()
            release = Event()
            def play(path, **callbacks):
                callbacks["on_started"]()
                callbacks["on_level"](.8)
                release.wait(1)
            window.voice_worker.player.play.side_effect = play
            observed = []
            class Observer(QObject):
                @Slot(str)
                def started(observer, voice_id):
                    observed.append((QThread.currentThread() == self.app.thread(), window.companion.speaking))
            observer = Observer()
            window.voice_worker.started.connect(observer.started)
            window.speech_request.connect(window.voice_worker.speak_item)
            try:
                window.queue_voice("Hello", "HAPPY")
                until = time.monotonic() + 1
                while not observed and time.monotonic() < until:
                    QTest.qWait(10)
                self.assertEqual(observed, [(True, True)])
            finally:
                release.set()
                QTest.qWait(30)
