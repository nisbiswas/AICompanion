from PySide6.QtCore import QObject, Signal, Slot
from app.character.controller import CharacterController
from app.ai.cancellation import RequestCancelled, request_scope


class AIWorker(QObject):
    completed = Signal(object)
    progress = Signal(str, str)

    def __init__(self, permissions):
        super().__init__()
        self.controller = CharacterController(permissions=permissions)

    @Slot(object)
    def execute(self, item):
        agent = self.controller.agent
        if item.token.cancelled:
            self.completed.emit({"item": item, "cancelled": True})
            return
        checkpoint = agent.context.checkpoint()
        try:
            with request_scope(item.token):
                agent.set_browser_context(item.browser)
                agent.progress_callback = lambda stage: self.progress.emit(item.id, stage)
                if item.kind == "context":
                    response = agent.react_to_browser()
                elif item.kind == "image":
                    response = agent.generate_image(item.text)
                else:
                    response = agent.respond(item.text)
            self.completed.emit({"item": item, "response": response})
        except RequestCancelled:
            agent.context.rollback(checkpoint)
            self.completed.emit({"item": item, "cancelled": True})
        except Exception as exc:
            self.completed.emit({"item": item, "error": str(exc)})

    @Slot(str)
    def remember_context_reply(self, reply):
        self.controller.agent.context.add_assistant_message(reply)
