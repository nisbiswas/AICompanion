import json
import unittest

from app.ai.response import readable_reply, has_readable_text
from app.ai.workflows import Workflow
import test_workflows


class ReadableResponseTests(unittest.TestCase):
    def test_reported_dash_response_uses_the_actual_voice_reply(self):
        voice = "Why thank you, that's very sweet of you to say!"
        agent = test_workflows.WorkflowTests().agent(Workflow.CHAT)
        agent.llm.chat.return_value = json.dumps({
            "response": "-", "voice_line": voice, "state": "TALKING",
            "intent": "CONVERSATION", "emotion": "HAPPY", "tool_request": None,
        })
        response = agent.respond("I am doing fine !! You loook so good")
        self.assertEqual(response.response, voice)
        self.assertEqual(agent.context.get_messages()[-1]["content"], voice)

    def test_whitespace_null_and_markers_fall_back_to_spoken_words(self):
        for text in (None, "", "   ", "-", "*", "---", "###", "```", "<p></p>"):
            with self.subTest(text=text):
                self.assertEqual(readable_reply(text, "Hello there."), "Hello there.")

    def test_missing_both_fields_is_an_actionable_visible_message(self):
        self.assertIn("try again", readable_reply("-", ""))

    def test_silent_passive_observation_stays_silent(self):
        agent = test_workflows.WorkflowTests().agent(Workflow.BROWSER)
        agent.llm.chat.return_value = '{"response":"-","voice_line":"","tool_request":null}'
        response = agent.react_to_browser()
        self.assertEqual(response.response, "")
        self.assertEqual(response.voice_line, "")

    def test_real_markdown_code_and_emoji_are_not_replaced(self):
        for text in ("- Hello there", "```java\nreturn 0;\n```", "# Title", "😊"):
            with self.subTest(text=text):
                self.assertTrue(has_readable_text(text))
                self.assertEqual(readable_reply(text, "Short voice"), text)

    def test_old_marker_only_assistant_entries_do_not_train_future_replies(self):
        agent = test_workflows.WorkflowTests().agent(Workflow.CHAT)
        agent.context.add_user_message("Hello")
        agent.context.add_assistant_message("-")
        agent.context.add_user_message("How are you?")
        self.assertNotIn({"role":"assistant", "content":"-"}, agent.context.get_messages())
