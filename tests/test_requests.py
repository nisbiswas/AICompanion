import asyncio
import json
from pathlib import Path
import subprocess
import tempfile
from threading import Timer
import time
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import httpx
from app.ai.cancellation import CancellationToken, RequestCancelled, request_scope, run_async
from app.ai.context import ConversationContext
from app.ai.ollama_client import OllamaClient
from app.images.service import ImageGenerationService
from app.ui.requests import RequestScheduler, WorkItem
from app.ui.ai_worker import AIWorker
from app.ui.character_window import CharacterWindow
from app.voice.worker import VoiceWorker
import test_workflows
from app.ai.workflows import Workflow


class RequestTests(unittest.TestCase):
    def test_latest_request_replaces_pending_and_cancels_running(self):
        queue = RequestScheduler()
        first = queue.submit("chat", "one", {"title": "A"})
        self.assertIsNone(queue.submit("chat", "two", {"title": "B"}))
        second = queue.pending
        queue.submit("image", "three", {"title": "C"})
        self.assertTrue(first.token.cancelled)
        self.assertTrue(second.token.cancelled)
        self.assertFalse(queue.accepts(first.id))
        third = queue.finish(first.id)
        self.assertEqual(third.text, "three")
        self.assertEqual(third.browser["title"], "C")
        self.assertTrue(queue.accepts(third.id))

    def test_stop_cancels_active_and_pending(self):
        queue = RequestScheduler()
        first = queue.submit("chat", "one", {})
        queue.submit("chat", "two", {})
        pending = queue.pending
        queue.cancel()
        self.assertTrue(first.token.cancelled)
        self.assertTrue(pending.token.cancelled)
        self.assertIsNone(queue.finish(first.id))

    def test_cancel_interrupts_inflight_async_request(self):
        token = CancellationToken()
        cleaned_up = []
        async def slow_request():
            try:
                await asyncio.sleep(30)
            finally:
                cleaned_up.append(True)
        timer = Timer(0.12, token.cancel)
        timer.start()
        started = time.monotonic()
        try:
            with request_scope(token), self.assertRaises(RequestCancelled):
                run_async(slow_request)
        except RequestCancelled:
            pass
        timer.cancel()
        self.assertLess(time.monotonic() - started, 1.5)
        self.assertTrue(cleaned_up)

    def test_cancelled_work_does_not_pollute_conversation_memory(self):
        worker = AIWorker.__new__(AIWorker)
        from PySide6.QtCore import QObject
        QObject.__init__(worker)
        history = ConversationContext()
        history.add_user_message("Earlier completed exchange")
        token = CancellationToken()
        agent = Mock()
        agent.context = history
        def respond(message):
            history.add_user_message(message)
            history.add_assistant_message("partial answer")
            token.cancel()
        agent.respond.side_effect = respond
        worker.controller = SimpleNamespace(agent=agent)
        results = []
        worker.completed.connect(results.append)
        worker.execute(WorkItem("chat", "cancel me", {}, token, "one"))
        self.assertTrue(results[0]["cancelled"])
        self.assertEqual(len(history.messages), 1)

    def test_cancel_kills_image_process(self):
        token = CancellationToken()
        process = Mock()
        process.args = ["image engine"]
        process.poll.return_value = None
        def communicate(**kwargs):
            if kwargs.get("input"):
                token.cancel()
                raise subprocess.TimeoutExpired("image engine", .2)
            return "", ""
        process.communicate.side_effect = communicate
        with tempfile.TemporaryDirectory() as folder:
            service = ImageGenerationService()
            service.python = Path(__file__)
            service.output_dir = Path(folder)
            with patch("app.images.service.subprocess.Popen", return_value=process):
                with self.assertRaises(RequestCancelled), request_scope(token):
                    service.generate("fox", Mock())
        process.kill.assert_called_once()

    def test_old_passive_reaction_is_not_presented(self):
        token = CancellationToken()
        window = SimpleNamespace(context_token=token, browser_revision=2,
                                 context_reaction_busy=True, handle_context_response=Mock())
        item = WorkItem("context", "", {"_revision":1, "_requested_at":time.monotonic()}, token, "one")
        CharacterWindow.handle_work_completed(window, {"item":item,"response":Mock()})
        window.handle_context_response.assert_not_called()

    def test_late_passive_reaction_is_not_presented(self):
        token = CancellationToken()
        window = SimpleNamespace(context_token=token, browser_revision=2,
                                 context_reaction_busy=True, handle_context_response=Mock())
        item = WorkItem("context", "", {"_revision":2, "_requested_at":time.monotonic()-30}, token, "one")
        CharacterWindow.handle_work_completed(window, {"item":item,"response":Mock()})
        window.handle_context_response.assert_not_called()

    def test_expired_queued_speech_never_synthesizes_or_plays(self):
        worker = VoiceWorker()
        worker.tts = Mock()
        worker.player = Mock()
        worker.speak_item({"id":"old", "text":"An old Kafka topic", "emotion":"NEUTRAL",
                           "token":CancellationToken(deadline=time.monotonic()-1)})
        worker.tts.speak.assert_not_called()
        worker.player.play.assert_not_called()


class ResponseTests(unittest.TestCase):
    def with_transport(self, handler, action):
        original = httpx.AsyncClient
        with patch("app.ai.ollama_client.httpx.AsyncClient", side_effect=lambda **kwargs: original(transport=httpx.MockTransport(handler), **kwargs)):
            return action()

    def test_token_limited_answer_is_retried_before_display(self):
        budgets = []
        def handle(request):
            budgets.append(json.loads(request.content)["options"]["num_predict"])
            if len(budgets) == 1:
                return httpx.Response(200, json={"message":{"content":"partial"}, "done":True,"done_reason":"length"})
            return httpx.Response(200, json={"message":{"content":"{}"}, "done":True,"done_reason":"stop"})
        self.assertEqual(self.with_transport(handle, lambda: OllamaClient().chat([])), "{}")
        self.assertEqual(budgets, [4096,8192])

    def test_cut_connection_does_not_become_a_complete_answer(self):
        def handle(request):
            return httpx.Response(200, json={"message":{"content":"{}"}, "done":False})
        with self.assertRaisesRegex(RuntimeError, "before the answer was complete"):
            self.with_transport(handle, lambda: OllamaClient().chat([]))

    def test_passive_observation_cannot_inherit_old_kafka_topics(self):
        agent = test_workflows.WorkflowTests().agent(Workflow.BROWSER)
        agent.context.add_user_message("Help me with Kafka consumer offsets")
        agent.memory.get_facts.return_value = ["The user builds Kafka brokers"]
        response = agent.react_to_browser()
        messages = agent.llm.chat.call_args.args[0]
        self.assertNotIn("Kafka", json.dumps(messages))
        self.assertEqual(response.voice_line, response.response)

    def test_browser_context_includes_editor_document_separately(self):
        agent = test_workflows.WorkflowTests().agent(Workflow.BROWSER)
        agent.browser_context["code_text"] = "public int reverse(int x) { return x; }"
        agent.browser_context["selected_text"] = "signed 32-bit integer"
        context = agent._build_browser_context()
        self.assertIn("public int reverse", context)
        self.assertIn("signed 32-bit integer", context)


if __name__ == "__main__":
    unittest.main()
