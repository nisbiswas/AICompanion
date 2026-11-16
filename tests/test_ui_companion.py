import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import unittest
from unittest.mock import Mock, patch
from PySide6.QtCore import QEvent, QTimer
from PySide6.QtWidgets import QApplication, QWidget

from app.ui.character_window import CharacterWindow
from app.ai.response import AgentResponse, AgentState, AgentIntent
from app.ui.speech_bubble import SpeechBubble
from app.ui.chat_input import ChatInput


class GenerationVoiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        # Exercise the real slots without starting model/audio/bridge threads.
        self.window = CharacterWindow.__new__(CharacterWindow)
        QWidget.__init__(self.window)
        self.window.say = Mock()
        self.window.companion = Mock()
        self.window.output_dismissed = False
        self.window.image_in_progress = False
        self.window.image_last_voice_time = 0.0
        self.window.image_waiting_index = 0
        self.window.image_voice_timer = QTimer(self.window)
        self.spoken = []
        self.window.voice_request.connect(lambda text, emotion: self.spoken.append(text))
        self.window.progress_voice_request.connect(lambda text, emotion: self.spoken.append(text))

    def tearDown(self):
        # Avoid CharacterWindow.closeEvent, which expects a running full app.
        self.window.image_voice_timer.stop()
        self.window.deleteLater()
        self.app.sendPostedEvents(None, QEvent.DeferredDelete)

    def test_image_stages_emit_voice_and_steps_do_not_spam(self):
        with patch("app.ui.character_window.time.monotonic", return_value=100):
            self.window.handle_image_progress("planning")
            self.window.handle_image_progress("step_1")
            self.window.handle_image_progress("step_2")
        self.assertEqual(len(self.spoken), 1)
        self.assertTrue(self.window.image_voice_timer.isActive())
        with patch("app.ui.character_window.time.monotonic", return_value=120):
            self.window.handle_image_progress("rendering")
        self.assertEqual(len(self.spoken), 2)

    def test_finished_generation_stops_waiting_voice(self):
        self.window.handle_image_progress("planning")
        self.window.finish_image_progress()
        count = len(self.spoken)
        self.window.image_waiting_voice()
        self.assertEqual(len(self.spoken), count)
        self.assertFalse(self.window.image_voice_timer.isActive())

    def test_only_displayed_context_questions_are_accepted_for_memory(self):
        self.window.request_busy = False
        self.window.context_reactions_enabled = True
        self.window.play_emotion = Mock()
        accepted = []
        self.window.context_reply_accepted.connect(accepted.append)
        response = AgentResponse("Practicing Genichiro's timing?", AgentState.TALKING,
                                 AgentIntent.CONVERSATION, False)
        self.window.handle_context_response(response)
        self.assertEqual(accepted, [response.response])
        self.window.request_busy = True
        self.window.handle_context_response(response)
        self.assertEqual(len(accepted), 1)

    def test_long_code_output_scrolls_and_can_be_dismissed(self):
        bubble = SpeechBubble()
        dismissed = []
        bubble.dismissed.connect(lambda: dismissed.append(True))
        bubble.say("Complete method:\n\n```java\n" + "// " + "long_code " * 70 + "\n" + "return 0;\n" * 70 + "}\n```")
        self.app.processEvents()
        self.assertGreater(bubble.text.verticalScrollBar().maximum(), 0)
        self.assertGreater(bubble.text.horizontalScrollBar().maximum(), 0)
        self.assertIn("return 0;", bubble.text.toPlainText())
        bubble.close_button.click()
        self.assertFalse(bubble.isVisible())
        self.assertTrue(dismissed)
        bubble.deleteLater()

    def test_stop_remains_available_after_dismissing_output(self):
        with patch("app.browser.bridge.BrowserBridge.start"), patch("app.browser.bridge.BrowserBridge.stop"), patch("app.voice.worker.VoiceWorker.prepare_acknowledgements"):
            window = CharacterWindow(None)
            try:
                window.work_request.disconnect()
                window.submit_request("chat", "Explain this")
                token = window.scheduler.active.token
                window.speech.close_button.click()
                self.assertTrue(window.output_dismissed)
                self.assertTrue(window.companion.stop_button.isVisible())
                window.companion.stop_button.click()
                self.assertTrue(token.cancelled)
                self.assertFalse(window.request_busy)
            finally:
                window.close()
                for widget in (window.companion, window.speech, window.chat_input, window):
                    widget.deleteLater()
                self.app.sendPostedEvents(None, QEvent.DeferredDelete)

    def test_actual_response_handler_displays_voice_when_body_is_a_dash(self):
        bubble = SpeechBubble()
        self.window.say = bubble.say
        self.window.play_emotion = Mock()
        voice = "Why thank you, that's very sweet of you to say!"
        response = AgentResponse("-", AgentState.TALKING, AgentIntent.CONVERSATION,
                                 False, voice_line=voice)
        self.window.handle_ai_response(response)
        self.app.processEvents()
        self.assertEqual(bubble.text.toPlainText(), voice)
        self.assertEqual(self.spoken, [voice])
        bubble.close()
        bubble.deleteLater()

    def test_research_control_explicitly_shows_search_permission(self):
        chat = ChatInput()
        self.assertEqual(chat.research_button.text(), "Research OFF")
        chat.set_research_enabled(True)
        self.assertEqual(chat.research_button.text(), "Research ON")
        chat.set_research_enabled(False)
        self.assertIn("OFF", chat.research_button.toolTip())
        chat.deleteLater()
