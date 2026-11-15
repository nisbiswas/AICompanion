import json
import unittest
from unittest.mock import patch

import httpx
from app.ai.workflows import Workflow
from app.ai.response import AgentState
from app.tools.web_search import WebSearchTool
import test_workflows


class ResearchOutcomeTests(unittest.TestCase):
    def test_disabled_research_never_asks_model_for_an_old_gpu_recommendation(self):
        agent = test_workflows.WorkflowTests().agent(Workflow.WEB_RESEARCH)
        agent.llm.chat.return_value = json.dumps({"response": "Buy an RTX 3090"})
        response = agent.respond("Which NVIDIA GPU is best for gaming?")
        self.assertIn("Research is OFF", response.response)
        self.assertNotIn("3090", response.response)
        self.assertEqual(response.state, AgentState.WAITING_FOR_PERMISSION)
        agent.tools.search_web.assert_not_called()
        agent.llm.chat.assert_not_called()

    def test_backend_failure_does_not_turn_into_a_training_knowledge_answer(self):
        agent = test_workflows.WorkflowTests().agent(Workflow.WEB_RESEARCH, research=True)
        agent.tools.search_web.side_effect = RuntimeError("Cannot connect to SearXNG")
        response = agent.respond("What is the latest GPU?")
        self.assertIn("Cannot connect to SearXNG", response.response)
        self.assertNotIn("3090", response.response)
        agent.llm.chat.assert_not_called()

    def test_empty_search_does_not_invent_a_current_answer(self):
        agent = test_workflows.WorkflowTests().agent(Workflow.WEB_RESEARCH, research=True)
        agent.tools.search_web.return_value = []
        response = agent.respond("What is the latest GPU?")
        self.assertIn("no usable results", response.response)
        agent.llm.chat.assert_not_called()

    def test_successful_search_includes_the_real_source_links(self):
        agent = test_workflows.WorkflowTests().agent(Workflow.WEB_RESEARCH, research=True)
        response = agent.respond("Search current gaming GPUs")
        self.assertIn("https://example.com", response.response)
        messages = agent.llm.chat.call_args.args[0]
        self.assertIn("WEB SEARCH COMPLETED SUCCESSFULLY", json.dumps(messages))
        agent.tools.search_web.assert_called_once()

    def test_successful_search_cannot_be_presented_as_search_unavailable(self):
        agent = test_workflows.WorkflowTests().agent(Workflow.WEB_RESEARCH, research=True)
        raw = json.loads(test_workflows.FINAL)
        raw["response"] = "I'm not able to perform a web search right now, but buy an RTX 3090."
        agent.llm.chat.return_value = json.dumps(raw)
        response = agent.respond("Search current gaming GPUs")
        self.assertNotIn("not able", response.response)
        self.assertNotIn("3090", response.response)
        self.assertIn("https://example.com", response.response)

    def test_browser_only_questions_still_do_not_search(self):
        agent = test_workflows.WorkflowTests().agent(Workflow.BROWSER, research=True)
        agent.respond("What is this video about?")
        agent.tools.search_web.assert_not_called()


class SearchBackendTests(unittest.TestCase):
    def search_with(self, handler):
        original = httpx.AsyncClient
        with patch("app.tools.web_search.httpx.AsyncClient", side_effect=lambda **kwargs: original(transport=httpx.MockTransport(handler), **kwargs)):
            return WebSearchTool().search("GPU specification", 2)

    def test_json_format_denial_has_an_actionable_error(self):
        with self.assertRaisesRegex(RuntimeError, "search.formats includes json"):
            self.search_with(lambda request: httpx.Response(403))

    def test_html_response_is_not_treated_as_search_results(self):
        with self.assertRaisesRegex(RuntimeError, "did not return JSON"):
            self.search_with(lambda request: httpx.Response(200, text="<html>Search</html>"))

    def test_invalid_urls_and_payload_rows_do_not_become_evidence(self):
        results = self.search_with(lambda request: httpx.Response(200, json={"results":[
            None, {"title":"Bad link", "url":"javascript:alert(1)"},
            {"title":"Source", "url":"https://example.com/specs", "content":"A specification"},
        ]}))
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["url"], "https://example.com/specs")
