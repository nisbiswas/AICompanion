import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import unittest
from unittest.mock import patch
from PySide6.QtCore import QPoint, Qt, QUrl
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from app.ui.speech_bubble import SpeechBubble


class OutputWindowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.bubble = SpeechBubble()

    def tearDown(self):
        self.bubble.close()
        self.bubble.deleteLater()

    def test_screenshot_sentence_wraps_inside_actual_viewport(self):
        sentence = "You are watching a video titled 'the weeknd - after hours' and I can help with the details shown on this page."
        self.bubble.say(sentence)
        self.app.processEvents()
        self.assertEqual(self.bubble.text.toPlainText(), sentence)
        self.assertEqual(self.bubble.text.horizontalScrollBar().maximum(), 0)
        self.assertGreater(self.bubble.text.viewport().height(), 50)
        self.assertGreater(self.bubble.text.document().begin().layout().lineCount(), 1)

    def test_user_can_enlarge_window_and_new_replies_preserve_size(self):
        self.bubble.say("A short answer")
        self.app.processEvents()
        self.bubble.resize(730, 540)
        self.app.processEvents()
        chosen = self.bubble.size()
        self.assertTrue(self.bubble.user_resized)
        self.assertGreater(chosen.width(), SpeechBubble.WIDTH)
        self.assertGreater(chosen.height(), SpeechBubble.MAX_HEIGHT)
        self.bubble.say("Thinking...")
        self.app.processEvents()
        self.assertEqual(self.bubble.size(), chosen)

    def test_maximize_and_restore_keep_the_response(self):
        self.bubble.say("Response remains available while maximizing.")
        self.app.processEvents()
        previous = self.bubble.size()
        QTest.mouseClick(self.bubble.maximize_button, Qt.LeftButton)
        self.app.processEvents()
        self.assertTrue(self.bubble.isMaximized())
        self.bubble.say("A later response stays maximized.")
        self.app.processEvents()
        self.assertTrue(self.bubble.isMaximized())
        QTest.mouseClick(self.bubble.maximize_button, Qt.LeftButton)
        self.app.processEvents()
        self.assertFalse(self.bubble.isMaximized())
        self.assertEqual(self.bubble.size(), previous)
        self.assertEqual(self.bubble.text.toPlainText(), "A later response stays maximized.")

    def test_auto_growth_stays_inside_monitor(self):
        self.bubble.say("A short answer")
        self.app.processEvents()
        area = self.bubble.screen().availableGeometry()
        self.bubble.move(area.right() - self.bubble.width(), area.bottom() - self.bubble.height())
        self.bubble.say("A line of a longer response.\n\n" * 80)
        self.app.processEvents()
        self.assertLessEqual(self.bubble.frameGeometry().bottom(), area.bottom())
        self.assertGreater(self.bubble.text.verticalScrollBar().maximum(), 0)

    def test_actual_resize_grip_drag_enlarges_window(self):
        self.bubble.say("Drag the lower-right corner.")
        self.bubble.move(10, 10)
        self.app.processEvents()
        before = self.bubble.size()
        grip = self.bubble.resize_grip
        start = grip.rect().center()
        QTest.mousePress(grip, Qt.LeftButton, pos=start)
        QTest.mouseMove(grip, start + QPoint(110, 100), delay=20)
        QTest.mouseRelease(grip, Qt.LeftButton, pos=start + QPoint(110, 100))
        self.app.processEvents()
        self.assertGreater(self.bubble.width(), before.width())
        self.assertGreater(self.bubble.height(), before.height())

    def test_marker_only_output_cannot_leave_an_empty_bubble(self):
        self.bubble.say("-")
        self.app.processEvents()
        self.assertIn("readable reply", self.bubble.text.toPlainText())

    def test_markup_that_hides_its_label_falls_back_to_plain_source(self):
        source = "[](https://example.org)"
        self.bubble.say(source)
        self.app.processEvents()
        self.assertIn("example.org", self.bubble.text.toPlainText())

    def test_clicking_a_source_opens_browser_and_preserves_answer(self):
        self.bubble.say("Sources:\n\n[Official documentation](https://example.org/docs)")
        self.app.processEvents()
        content = self.bubble.text.toPlainText()
        viewport = self.bubble.text.viewport()
        # Hit-test the rendered anchor, then exercise a real mouse click.
        link_point = next((QPoint(x, y) for y in range(0, viewport.height(), 3)
                           for x in range(0, viewport.width(), 3)
                           if self.bubble.text.anchorAt(QPoint(x, y)) == "https://example.org/docs"), None)
        self.assertIsNotNone(link_point)
        with patch("app.ui.speech_bubble.QDesktopServices.openUrl", return_value=True) as open_url:
            QTest.mouseClick(viewport, Qt.LeftButton, pos=link_point)
            self.app.processEvents()
            open_url.assert_called_once_with(QUrl("https://example.org/docs"))
        self.assertEqual(self.bubble.text.toPlainText(), content)
        self.assertTrue(self.bubble.text.textInteractionFlags() & Qt.TextSelectableByMouse)

    def test_non_web_links_do_not_launch_local_apps(self):
        with patch("app.ui.speech_bubble.QDesktopServices.openUrl") as open_url:
            self.bubble.open_source_link(QUrl("file:///C:/Windows/notepad.exe"))
            self.bubble.open_source_link(QUrl("javascript:alert(1)"))
            open_url.assert_not_called()
