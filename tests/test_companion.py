import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from app.ai.context import ConversationContext
from app.ai.ollama_client import OllamaClient
from app.behavior.controller import BehaviorController
from app.browser.context import BrowserContext
from app.images.planning import ImagePromptPlanner
from app.memory.memory_extractor import MemoryExtractor


class ConversationTests(unittest.TestCase):
    def test_more_than_ten_exchanges_survive_restart(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "history.sqlite3"
            history = ConversationContext(path)
            for index in range(15):
                history.add_user_message(f"Question {index}")
                history.add_assistant_message(json.dumps({"response": f"Answer {index}", "voice_line": "unused"}))
            restored = ConversationContext(path)
            self.assertEqual(len(restored.get_messages()), 30)
            self.assertEqual(restored.get_messages()[1]["content"], "Answer 0")
            self.assertEqual(restored.get_messages()[-1]["content"], "Answer 14")

    def test_old_conversation_is_retrieved_after_leaving_recent_window(self):
        with tempfile.TemporaryDirectory() as folder:
            history = ConversationContext(Path(folder) / "history.sqlite3", max_turns=10)
            history.add_user_message("My favorite dessert is pistachio ice cream")
            history.add_assistant_message("I'll remember pistachio.")
            for index in range(12):
                history.add_user_message(f"Question {index}")
                history.add_assistant_message(f"Answer {index}")
            self.assertNotIn("pistachio", str(history.get_messages()))
            self.assertIn("pistachio", history.relevant_history("What is my favorite dessert?"))

    def test_prompt_budget_does_not_delete_persisted_history(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "history.sqlite3"
            history = ConversationContext(path, token_budget=512)
            for index in range(15):
                history.add_user_message("question " * 100)
                history.add_assistant_message("answer " * 100)
            self.assertLess(len(history.get_messages()), len(history.messages))
            restored = ConversationContext(path, token_budget=20000)
            self.assertEqual(len(restored.get_messages()), 30)

    def test_clear_removes_persisted_history(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "history.sqlite3"
            history = ConversationContext(path)
            history.add_user_message("hello")
            history.clear()
            self.assertEqual(ConversationContext(path).get_messages(), [])


class CompanionPipelineTests(unittest.TestCase):
    def test_planner_selects_wide_composition_and_keeps_original_input(self):
        llm = Mock()
        llm.chat.return_value = json.dumps({"prompt": "A knight and constellation figure", "clip_prompt": "Dark fantasy panorama", "aspect": "landscape", "note": "Small details simplified"})
        plan = ImagePromptPlanner(llm).plan("A very long original scene")
        self.assertEqual((plan.width, plan.height), (1152, 768))
        self.assertEqual(llm.chat.call_args.args[0][-1]["content"], "A very long original scene")

    def test_memory_extractor_uses_its_own_schema(self):
        extractor = MemoryExtractor()
        extractor.llm = Mock()
        extractor.llm.chat.return_value = '{"remember":true,"fact":"The user likes Sekiro."}'
        self.assertEqual(extractor.extract("I like Sekiro"), "The user likes Sekiro.")
        schema = extractor.llm.chat.call_args.kwargs["schema"]
        self.assertIn("remember", schema["properties"])
        self.assertNotIn("voice_line", schema["properties"])

    def test_overlong_image_plan_is_rewritten(self):
        llm = Mock()
        long_plan = {"prompt": "word " * 140, "clip_prompt": "wide scene", "aspect": "landscape", "note": ""}
        short_plan = dict(long_plan, prompt="A kneeling knight reaches for a butterfly.")
        llm.chat.side_effect = [json.dumps(long_plan), json.dumps(short_plan)]
        plan = ImagePromptPlanner(llm).plan("Original crowded scene")
        self.assertEqual(llm.chat.call_count, 2)
        self.assertEqual(plan.prompt, short_plan["prompt"])

    def test_sekiro_alias_is_not_left_as_an_animal_subject(self):
        llm = Mock()
        llm.chat.return_value = json.dumps({"prompt": "Wolf stands in a forest.", "clip_prompt": "Wolf in the forest", "aspect": "portrait", "note": ""})
        plan = ImagePromptPlanner(llm).plan("Draw Sekiro")
        self.assertIn("human", plan.prompt.lower())
        self.assertNotIn("wolf", plan.clip_prompt.lower())

    def test_ollama_requests_explicit_context_size(self):
        client = OllamaClient()
        import httpx
        captured = []
        original_client = httpx.AsyncClient
        def handle(request):
            captured.append(json.loads(request.content))
            return httpx.Response(200, json={"message": {"content": "{}"}, "done": True, "done_reason": "stop"})
        with patch("app.ai.ollama_client.httpx.AsyncClient", side_effect=lambda **kwargs: original_client(transport=httpx.MockTransport(handle), **kwargs)):
            client.chat([])
        self.assertEqual(captured[0]["options"]["num_ctx"], client.context_length)

    def test_dynamic_text_refresh_does_not_repeat_context_reaction(self):
        behavior = BehaviorController()
        context = BrowserContext()
        first = context.update("Chrome", "Sekiro guide", "https://example.org", "first text")
        self.assertIsNotNone(behavior.handle_browser_event(first))
        changed_text = context.update("Chrome", "Sekiro guide", "https://example.org", "changed text")
        self.assertFalse(behavior.should_react(changed_text))


if __name__ == "__main__":
    unittest.main()
