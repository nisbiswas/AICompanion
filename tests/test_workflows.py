import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import Mock, patch

from app.ai.agent import CompanionAgent
from app.ai.context import ConversationContext
from app.ai.response import AgentIntent
from app.ai.workflows import RequestRoute, Workflow, WorkflowRouter
from app.images.service import ImageGenerationService
from app.permissions.manager import Permission, PermissionManager


FINAL = json.dumps({
    "response": "An answer", "state": "TALKING", "intent": "GENERAL_QUESTION",
    "permission_required": False, "tool_request": None,
    "emotion": "NEUTRAL", "voice_line": "Here you go.",
})


class WorkflowTests(unittest.TestCase):
    def agent(self, workflow, research=False):
        # Keep tests independent of local model servers and persistent user memory.
        agent = CompanionAgent.__new__(CompanionAgent)
        agent.context = ConversationContext()
        agent.permissions = PermissionManager()
        if research:
            agent.permissions.grant(Permission.WEB_SEARCH)
        agent.permissions.grant(Permission.BROWSER_CONTEXT)
        agent.permissions.grant(Permission.BROWSER_PAGE_READ)
        agent.browser_context = {"title": "Active video", "url": "https://example.org/video", "page_text": "Visible description"}
        agent.router = Mock()
        agent.router.route.return_value = RequestRoute(workflow, "resolved query or image prompt")
        agent.llm = Mock()
        agent.llm.chat.return_value = FINAL
        agent.memory = Mock()
        agent.memory.get_facts.return_value = []
        agent.memory_extractor = Mock()
        agent.memory_extractor.extract.return_value = None
        agent.tools = Mock()
        agent.tools.search_web.return_value = [{"title": "Evidence", "url": "https://example.com", "content": "Search evidence"}]
        agent.images = Mock()
        agent.images.generate.return_value = "C:/images/test.png"
        return agent

    def test_browser_question_does_not_search_with_research_enabled(self):
        agent = self.agent(Workflow.BROWSER, research=True)
        agent.respond("What is this video about?")
        agent.tools.search_web.assert_not_called()
        messages = agent.llm.chat.call_args.args[0]
        self.assertEqual(sum("Current read-only browser context" in m["content"] for m in messages), 1)
        self.assertTrue(any("Visible description" in m["content"] for m in messages))

    def test_search_does_not_receive_active_page(self):
        agent = self.agent(Workflow.WEB_RESEARCH, research=True)
        agent.respond("Search for today's news")
        agent.tools.search_web.assert_called_once_with("resolved query or image prompt", 5)
        messages = agent.llm.chat.call_args.args[0]
        self.assertFalse(any("Visible description" in m["content"] for m in messages))
        self.assertTrue(any("Search evidence" in m["content"] for m in messages))

    def test_combined_research_uses_page_and_search(self):
        agent = self.agent(Workflow.BROWSER_RESEARCH, research=True)
        agent.respond("Fact check this page using online sources")
        agent.tools.search_web.assert_called_once()
        messages = agent.llm.chat.call_args.args[0]
        self.assertTrue(any("Visible description" in m["content"] for m in messages))
        self.assertTrue(any("Search evidence" in m["content"] for m in messages))

    def test_disabled_research_denies_search_but_keeps_page(self):
        agent = self.agent(Workflow.BROWSER_RESEARCH)
        agent.respond("Fact check this page")
        agent.tools.search_web.assert_not_called()
        messages = agent.llm.chat.call_args.args[0]
        self.assertTrue(any("WEB_SEARCH permission is not granted" in m["content"] for m in messages))
        self.assertTrue(any("Visible description" in m["content"] for m in messages))

    def test_revoking_page_read_filters_cached_page(self):
        agent = self.agent(Workflow.BROWSER)
        agent.permissions.revoke(Permission.BROWSER_PAGE_READ)
        self.assertNotIn("Visible description", agent._build_browser_context())
        self.assertIn("Active video", agent._build_browser_context())
        agent.permissions.revoke(Permission.BROWSER_CONTEXT)
        self.assertNotIn("Active video", agent._build_browser_context())

    def test_model_cannot_force_search_in_browser_workflow(self):
        agent = self.agent(Workflow.BROWSER, research=True)
        self.assertIn("unavailable", agent._execute_tool({"tool": "web_search", "arguments": {"query": "wrong search"}}))
        agent.tools.search_web.assert_not_called()

    def test_image_request_returns_attachment_without_post_generation_llm(self):
        agent = self.agent(Workflow.IMAGE_GENERATION)
        response = agent.respond("Draw a fox")
        agent.images.generate.assert_called_once_with("resolved query or image prompt", agent.llm.unload)
        self.assertEqual(response.image_path, "C:/images/test.png")
        self.assertEqual(response.intent, AgentIntent.IMAGE_GENERATION)
        agent.llm.chat.assert_not_called()
        agent.memory_extractor.extract.assert_not_called()

    def test_image_button_bypasses_router(self):
        agent = self.agent(Workflow.CHAT)
        agent.generate_image("A fox")
        agent.router.route.assert_not_called()
        agent.images.generate.assert_called_once_with("A fox", agent.llm.unload)

    def test_generation_failure_does_not_claim_success(self):
        agent = self.agent(Workflow.IMAGE_GENERATION)
        agent.images.generate.side_effect = RuntimeError("CUDA unavailable")
        response = agent.respond("Draw a fox")
        self.assertIsNone(response.image_path)
        self.assertIn("CUDA unavailable", response.response)

    def test_router_uses_structured_output_and_recent_history(self):
        llm = Mock()
        llm.chat.return_value = '{"workflow":"BROWSER", "prompt":"Summarize this video"}'
        route = WorkflowRouter(llm).route("Summarize this video", [])
        self.assertEqual(route.workflow, Workflow.BROWSER)
        self.assertIn("schema", llm.chat.call_args.kwargs)

    def test_memory_failure_does_not_discard_answer(self):
        agent = self.agent(Workflow.CHAT)
        agent.memory_extractor.extract.side_effect = RuntimeError("offline")
        self.assertEqual(agent.respond("Hello").response, "An answer")

    def test_search_is_not_repeated_when_model_requests_it_again(self):
        agent = self.agent(Workflow.WEB_RESEARCH, research=True)
        tool = json.loads(FINAL)
        tool["tool_request"] = {"tool": "web_search", "arguments": {"query": "again"}}
        agent.llm.chat.side_effect = [json.dumps(tool), FINAL]
        self.assertEqual(agent.respond("Search the news").response, "An answer")
        agent.tools.search_web.assert_called_once()

    def test_third_tool_result_is_synthesized_into_final_answer(self):
        agent = self.agent(Workflow.CHAT)
        tool = json.loads(FINAL)
        tool["tool_request"] = {"tool": "read_file", "arguments": {"path": "example.py"}}
        agent.tools.read_file.return_value = "file content"
        agent.llm.chat.side_effect = [json.dumps(tool)] * 3 + [FINAL]
        response = agent.respond("Inspect my project")
        self.assertEqual(agent.tools.read_file.call_count, 3)
        self.assertEqual(response.response, "An answer")
        self.assertIsNone(response.tool_request)


class ImageServiceTests(unittest.TestCase):
    def test_isolated_process_runs_after_unload_and_produces_unique_paths(self):
        with tempfile.TemporaryDirectory() as folder:
            service = ImageGenerationService()
            service.python = Path(__file__)  # Existing path; process itself is mocked.
            service.output_dir = Path(folder)
            events = []

            def run(command, **kwargs):
                events.append("generate")
                self.assertIsInstance(command, list)
                self.assertNotIn("shell", kwargs)
                request = json.loads(kwargs["input"])
                self.assertEqual(request["prompt"], 'A fox with "quotes" and $symbols')
                Path(request["output"]).write_bytes(b"test image")
                return subprocess.CompletedProcess(command, 0, "", "")

            with patch("app.images.service.subprocess.run", side_effect=run):
                first = service.generate('A fox with "quotes" and $symbols', lambda: events.append("unload"))
                second = service.generate('A fox with "quotes" and $symbols', lambda: events.append("unload"))
            self.assertNotEqual(first, second)
            self.assertEqual(events, ["unload", "generate", "unload", "generate"])

    def test_missing_environment_does_not_unload_qwen(self):
        service = ImageGenerationService()
        service.python = Path("does-not-exist/python.exe")
        unload = Mock()
        with self.assertRaisesRegex(RuntimeError, "IMAGE_ENGINE_PYTHON"):
            service.generate("fox", unload)
        unload.assert_not_called()

    def test_timeout_is_reported(self):
        service = ImageGenerationService()
        service.python = Path(__file__)
        with tempfile.TemporaryDirectory() as folder:
            service.output_dir = Path(folder)
            with patch("app.images.service.subprocess.run", side_effect=subprocess.TimeoutExpired("engine", 1)):
                with self.assertRaisesRegex(RuntimeError, "timed out"):
                    service.generate("fox", Mock())


if __name__ == "__main__":
    unittest.main()
