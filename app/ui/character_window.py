import os
import time
from uuid import uuid4

from PySide6.QtCore import Qt, QTimer, QThread, Signal, Slot
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QApplication, QLabel, QMenu, QWidget

from app.character.character import Character
from app.character.states import CharacterState
from app.ui.chat_input import ChatInput
from app.ui.speech_bubble import SpeechBubble
from app.ui.ai_worker import AIWorker
from app.voice.worker import VoiceWorker
from app.character.cursor_tracker import CursorTracker
from PySide6.QtGui import QTransform
from app.browser.context import BrowserContext
from app.browser.bridge import BrowserBridge
from app.permissions.manager import PermissionManager, Permission
from app.behavior.controller import BehaviorController
from app.voice.stt_worker import STTWorker
from app.ui.image_preview import ImagePreview
from app.ui.requests import RequestScheduler, WorkItem
from app.ai.cancellation import CancellationToken
from app.ai.response import readable_reply
from app.ui.companion_panel import CompanionPanel
from app.voice.queue import SpeechQueue


class CharacterWindow(QWidget):

    # =========================================================
    # SIGNALS
    # =========================================================

    work_request = Signal(object)
    speech_request = Signal(object)
    prepare_voice_request = Signal()
    progress_voice_request = Signal(str, str)
    context_reply_accepted = Signal(str)
    voice_request = Signal(str, str)
    stt_request = Signal()

    
    browser_context_for_ai = Signal(object)

    SCALE = 2

    CANVAS_WIDTH = 176
    CANVAS_HEIGHT = 128

    REACTION_DURATION = 1200

    def __init__(self, controller):
        super().__init__()

        self.controller = controller

        # =====================================================
        # AI WORKER THREAD
        # =====================================================

        self.ai_thread = QThread(self)
        
        self.permissions = PermissionManager()

        self.ai_worker = AIWorker(
            self.permissions
        )

        self.ai_worker.moveToThread(
            self.ai_thread
        )

        self.scheduler = RequestScheduler()
        self.latest_browser = {}
        self.browser_revision = 0
        self.context_token = None
        self.voice_token = None
        self.current_voice_id = None
        self.speech_queue = SpeechQueue()
        self.response_pose = "NEUTRAL"
        self.last_user_activity = time.monotonic()
        self.output_dismissed = False
        self.has_user_interacted = False
        self.request_busy = False
        self.image_previews = []
        self.context_reaction_busy = False
        self.context_reactions_enabled = os.getenv("CONTEXT_REACTIONS_ENABLED", "true").lower() == "true"
        self.image_in_progress = False
        self.image_last_voice_time = 0.0
        self.work_request.connect(self.ai_worker.execute)
        self.ai_worker.progress.connect(self.handle_work_progress)
        self.ai_worker.completed.connect(self.handle_work_completed)
        self.context_reply_accepted.connect(self.ai_worker.remember_context_reply)

        self.ai_thread.start()

        # =====================================================
        # VOICE WORKER THREAD
        # =====================================================

        self.voice_thread = QThread(self)

        self.voice_worker = VoiceWorker()

        self.voice_worker.moveToThread(
            self.voice_thread
        )

        self.voice_request.connect(self.queue_voice)
        self.progress_voice_request.connect(self.queue_progress_voice)
        self.speech_request.connect(self.voice_worker.speak_item)
        self.prepare_voice_request.connect(self.voice_worker.prepare_acknowledgements)
        self.voice_worker.started.connect(self.voice_started)
        self.voice_worker.ended.connect(self.voice_ended)
        self.voice_worker.level.connect(self.voice_level)

        self.voice_worker.error.connect(
            self.handle_voice_error
        )

        self.voice_thread.start()
        self.prepare_voice_request.emit()
        self.image_voice_timer = QTimer(self)
        self.image_voice_timer.setInterval(35000)
        self.image_voice_timer.timeout.connect(self.image_waiting_voice)
        self.image_waiting_index = 0

        # =====================================================
        # CHARACTER
        # =====================================================

        self.character = Character()

        self.frame_index = 0
        self.base_state = CharacterState.IDLE
        self.reaction_active = False
        self.facing_right = False

        # =====================================================
        # READ-ALOUD STATE
        # =====================================================

        self.pending_read_aloud_text = None

        # =====================================================
        # WINDOW
        # =====================================================

        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
        )

        self.setAttribute(
            Qt.WA_TranslucentBackground
        )

        self.setFixedSize(
            self.CANVAS_WIDTH,
            self.CANVAS_HEIGHT,
        )

        # =====================================================
        # CHARACTER LABEL
        # =====================================================

        self.label = QLabel(self)

        self.label.setAttribute(
            Qt.WA_TransparentForMouseEvents
        )

        self.label.setAttribute(
            Qt.WA_TranslucentBackground
        )

        self.label.setAlignment(
            Qt.AlignCenter
        )

        # =====================================================
        # SPEECH
        # =====================================================

        self.speech = SpeechBubble()
        self.speech.stop_requested.connect(self.cancel_request)
        self.speech.dismissed.connect(self.dismiss_output)
        self.companion = CompanionPanel()
        self.companion.clicked.connect(self.show_input)
        self.companion.stop_requested.connect(self.cancel_request)
        self.companion.show()
        self.context_debounce = QTimer(self)
        self.context_debounce.setSingleShot(True)
        self.context_debounce.setInterval(1500)
        self.context_debounce.timeout.connect(self.request_context_reaction)

        # =====================================================
        # CHAT INPUT
        # =====================================================

        self.chat_input = ChatInput()

        self.chat_input.submitted.connect(
            self.handle_user_message
        )
        self.chat_input.image_generation_requested.connect(self.handle_image_request)

        self.chat_input.cancelled.connect(
            self.cancel_request
        )
        self.chat_input.research_changed.connect(
            self.set_research_enabled
            )
        self.chat_input.microphone_requested.connect(
            self.handle_microphone_request
        )
        # =====================================================
        # ANIMATION TIMER
        # =====================================================

        self.timer = QTimer(self)

        self.timer.timeout.connect(
            self.next_frame
        )

        # =====================================================
        # REACTION TIMER
        # =====================================================

        self.reaction_timer = QTimer(self)

        self.reaction_timer.setSingleShot(
            True
        )

        self.reaction_timer.timeout.connect(
            self.end_reaction
        )

        # =====================================================
        # INITIALIZATION
        # =====================================================

        self.load_animation()

        self.move_to_bottom_right()

        self.timer.start(160)

        QTimer.singleShot(
            700,
            self.startup_greeting,
        )

        ## cursor tracker

        
        self.cursor_tracker = CursorTracker(self)
        self.cursor_tracker.start()

        # =====================================================
        # BROWSER CONTEXT
        # =====================================================


        # self.ai_worker = AIWorker(
        #     self.permissions
        # )

        self.browser_context = BrowserContext()

        self.browser_bridge = BrowserBridge(
            self.browser_context,
            self.permissions,
        )

        self.behavior_controller = BehaviorController()

        self.browser_bridge.event_received.connect(
        self.handle_browser_event
            )
        # Read-only browser metadata and visible page text are enabled.
        # Navigation and browser interactions remain disabled.
        self.permissions.grant(
            Permission.BROWSER_CONTEXT
        )

        self.permissions.grant(
            Permission.BROWSER_PAGE_READ
        )

        # self.permissions.grant(
        #     Permission.WEB_SEARCH
        # )

        
        self.browser_bridge.start()

        # Debug browser context while testing.

        # =====================================================
        # STT WORKER THREAD
        # =====================================================

        self.stt_thread = QThread(self)

        self.stt_worker = STTWorker()

        self.stt_worker.moveToThread(
            self.stt_thread
        )

        self.stt_request.connect(
            self.stt_worker.listen
        )

        self.stt_worker.finished.connect(
            self.handle_stt_result
        )

        self.stt_worker.error.connect(
            self.handle_stt_error
        )

        self.stt_thread.start()
        


    # =========================================================
    # ANIMATION
    # =========================================================


    
    def set_facing_right(self, facing_right: bool):
        if self.facing_right == facing_right:
            return

        self.facing_right = facing_right

        # Re-render the current animation frame.
        self.load_animation()

    def load_animation(self):

        animation = (
            self.character.current_animation()
        )

        pixmap = QPixmap(
            str(animation["path"])
        )

        if pixmap.isNull():
            return

        frame_count = animation["frames"]

        frame_width = (
            pixmap.width()
            // frame_count
        )

        frame_height = pixmap.height()

        frame = pixmap.copy(
            self.frame_index * frame_width,
            0,
            frame_width,
            frame_height,
        )

        frame = frame.scaled(
            frame.width() * self.SCALE,
            frame.height() * self.SCALE,
            Qt.KeepAspectRatio,
            Qt.FastTransformation,
        )

        if self.facing_right:
            frame = frame.transformed(
                QTransform().scale(-1, 1)
            )

        self.label.resize(
            frame.size()
        )

        x = (
            self.width()
            - frame.width()
        ) // 2

        y = (
            self.height()
            - frame.height()
        ) // 2

        self.label.move(
            x,
            y,
        )

        self.label.setPixmap(
            frame
        )

    def next_frame(self):

        animation = (
            self.character.current_animation()
        )

        frame_count = animation["frames"]

        if frame_count <= 1:
            return

        self.frame_index = (
            self.frame_index + 1
        ) % frame_count

        self.load_animation()

    # =========================================================
    # EMOTIONS / REACTIONS
    # =========================================================

    def play_emotion(self, emotion: str):

        emotion = emotion.upper()

        if emotion in {
            "NEUTRAL",
            "CURIOUS",
            "THINKING",
        }:

            self.end_reaction()

            return

        reaction_state = (
            self.character
            .emotion_animation_map
            .get(emotion)
        )

        if reaction_state is None:

            self.end_reaction()

            return

        self.base_state = (
            self.character.state
        )

        self.character.set_state(
            reaction_state
        )

        self.frame_index = 0

        self.reaction_active = True

        self.load_animation()

        self.reaction_timer.stop()

        self.reaction_timer.start(
            self.REACTION_DURATION
        )

    def end_reaction(self):

        if not self.reaction_active:
            return

        self.reaction_active = False

        self.character.set_state(
            self.base_state
        )

        self.frame_index = 0

        self.load_animation()

    # =========================================================
    # SPEECH BUBBLE
    # =========================================================

    def say(self, text: str):

        if not self.output_dismissed:
            self.speech.say_near(text, self.companion)

    def hide_speech(self):

        self.speech.hide()

    def position_speech(self):

        bubble_width = (
            self.speech.width()
        )

        bubble_height = (
            self.speech.height()
        )

        x = (
            self.x()
            + self.width() // 2
            - bubble_width // 2
        )

        y = (
            self.y()
            - bubble_height
            - 10
        )

        self.speech.move(
            x,
            y,
        )

    # =========================================================
    # MOUSE
    # =========================================================

    def mousePressEvent(self, event):

        if event.button() != Qt.LeftButton:
            return

        self.show_input()

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        reactions = menu.addAction("Comment on browser context")
        reactions.setCheckable(True)
        reactions.setChecked(self.context_reactions_enabled)
        if menu.exec(event.globalPos()) == reactions:
            self.context_reactions_enabled = reactions.isChecked()

    def show_input(self):

        screen = self.screen()

        if screen is None:
            return

        available = screen.availableGeometry()

        character_rect = self.frameGeometry()

        x = (
            character_rect.left()
            - self.chat_input.width()
            - 20
        )

        y = (
            character_rect.center().y()
            - self.chat_input.height() // 2
        )

        x = max(
            available.left() + 10,
            min(
                x,
                available.right()
                - self.chat_input.width()
                - 10,
            ),
        )

        y = max(
            available.top() + 10,
            min(
                y,
                available.bottom()
                - self.chat_input.height()
                - 10,
            ),
        )

        self.chat_input.move(
            x,
            y
        )

        self.chat_input.show()

        self.chat_input.raise_()

        self.chat_input.setFocus()

    def hide_input(self):

        self.chat_input.hide()

    # =========================================================
    # USER → AI
    # =========================================================


    def set_research_enabled(self, enabled: bool):

        if enabled:
            self.permissions.grant(
                Permission.WEB_SEARCH
            )
        else:
            self.permissions.revoke(
                Permission.WEB_SEARCH
            )

        print(
            "RESEARCH:",
            "ON" if enabled else "OFF",
        )

        print(
            "WEB_SEARCH:",
            self.permissions.is_allowed(
                Permission.WEB_SEARCH
            ),
        )

    def handle_user_message(
        self,
        text: str,
    ):

        self.hide_input()

        text = text.strip()

        if not text:
            return

        # =====================================================
        # READ-ALOUD CONFIRMATION
        # =====================================================

        if self.pending_read_aloud_text is not None:

            normalized = text.lower().strip()

            yes_answers = {
                "yes",
                "yeah",
                "yep",
                "yup",
                "sure",
                "okay",
                "ok",
                "please",
                "read it",
                "read it to me",
                "go ahead",
            }

            no_answers = {
                "no",
                "nope",
                "nah",
                "not now",
                "no thanks",
                "don't",
                "dont",
            }

            if normalized in yes_answers:

                text_to_read = (
                    self.pending_read_aloud_text
                )

                self.pending_read_aloud_text = None

                self.voice_request.emit(
                    text_to_read,
                    "NEUTRAL",
                )

                return

            if normalized in no_answers:

                self.pending_read_aloud_text = None

                return

            self.pending_read_aloud_text = None

        # =====================================================
        # NORMAL AI REQUEST
        # =====================================================
        
        self.submit_request("chat", text)

    def handle_image_request(self, prompt):
        if prompt.strip():
            self.hide_input()
            self.submit_request("image", prompt.strip())

    def submit_request(self, kind, text):
        self.has_user_interacted = True
        self.cancel_context_reaction()
        self.invalidate_speech()
        self.finish_image_progress()
        self.last_user_activity = time.monotonic()
        self.output_dismissed = False
        self.pending_read_aloud_text = None
        item = self.scheduler.submit(kind, text, self.browser_context.as_dict())
        self.request_busy = True
        self.speech.set_busy(True)
        self.companion.set_busy(True)
        self.companion.set_state("THINKING", "Thinking with you")
        self.say("Taking a look…" if item else "Switching to your latest request…")
        self.queue_voice("Hmm... taking a look." if kind == "chat" else "Let me picture that for a moment.",
                         "THINKING", kind="ack", pose="THINKING")
        if item:
            self.work_request.emit(item)

    def cancel_context_reaction(self):
        self.context_debounce.stop()
        if self.context_token:
            self.context_token.cancel()
        self.context_reaction_busy = False

    def cancel_request(self):
        self.ignore_stt_result = True
        self.scheduler.cancel()
        self.cancel_context_reaction()
        self.invalidate_speech()
        self.finish_image_progress()
        self.request_busy = False
        self.pending_read_aloud_text = None
        self.speech.set_busy(False)
        self.companion.set_busy(False)
        self.output_dismissed = False
        self.companion.set_state("NEUTRAL", "Here with you")
        self.say("Cancelled.")
        self.hide_input()

    def dismiss_output(self):
        self.output_dismissed = True
        self.invalidate_speech()

    @Slot(str, str)
    def handle_work_progress(self, request_id, stage):
        if self.scheduler.accepts(request_id):
            self.handle_image_progress(stage)

    @Slot(object)
    def handle_work_completed(self, result):
        item = result["item"]
        if item.kind == "context":
            if (self.context_token is item.token and not item.token.cancelled
                    and item.browser.get("_revision") == self.browser_revision
                    and time.monotonic() - item.browser.get("_requested_at", 0) < 15):
                self.handle_context_response(result.get("response"))
            if self.context_token is item.token:
                self.context_reaction_busy = False
                self.context_token = None
            return
        accepted = self.scheduler.accepts(item.id)
        following = self.scheduler.finish(item.id)
        if accepted and not result.get("cancelled"):
            if result.get("error"):
                self.handle_ai_error(result["error"])
            else:
                self.handle_ai_response(result.get("response"))
        if following:
            self.request_busy = True
            self.work_request.emit(following)
        elif self.scheduler.active is None:
            self.request_busy = False
            self.speech.set_busy(False)
            self.companion.set_busy(False)

    def invalidate_speech(self):
        if hasattr(self, "speech_queue"):
            self.speech_queue.cancel()
        if self.voice_token:
            self.voice_token.cancel()
        self.current_voice_id = None
        if hasattr(self, "voice_worker"):
            self.voice_worker.player.stop()
        if hasattr(self, "companion"):
            self.companion.set_speaking(False)
            self.companion.set_voice_level(0.0)
        if getattr(self, "reaction_active", False):
            self.end_reaction()

    @Slot(str, str)
    def queue_voice(self, text, emotion, *, kind="result", pose=None):
        if self.output_dismissed or not text.strip():
            return
        item = self.speech_queue.enqueue(text, emotion, kind=kind,
            pose=pose or (self.response_pose if kind == "result" else emotion),
            page=(self.latest_browser.get("url"), self.latest_browser.get("title")))
        if item:
            self.dispatch_voice(item)

    def dispatch_voice(self, item):
        self.voice_worker.player.stop()
        self.voice_token = item["token"]
        self.current_voice_id = item["id"]
        self.companion.set_speaking(False)
        self.companion.set_voice_level(0.0)
        self.speech_request.emit(item)

    @Slot(str, str)
    def queue_progress_voice(self, text, emotion):
        self.queue_voice(text, emotion, kind="progress", pose="THINKING")

    @Slot(str)
    def voice_started(self, voice_id):
        if voice_id == self.current_voice_id:
            item = self.speech_queue.active
            self.companion.set_state(item["pose"], "Taking a look" if item["kind"] == "ack" else "Talking with you")
            self.companion.set_speaking(True)
            self.play_emotion(item["emotion"])
            self.reaction_timer.stop()

    @Slot(str, float)
    def voice_level(self, voice_id, level):
        if voice_id == self.current_voice_id:
            self.companion.set_voice_level(level)

    @Slot(str)
    def voice_ended(self, voice_id):
        if voice_id == self.current_voice_id:
            self.companion.set_speaking(False)
            self.companion.set_voice_level(0.0)
            self.end_reaction()
            self.current_voice_id = None
            following = self.speech_queue.finish(voice_id)
            self.companion.set_state("THINKING" if self.request_busy else "NEUTRAL",
                                     "Thinking with you" if self.request_busy else "Here with you")
            if following:
                self.dispatch_voice(following)

    def handle_image_progress(self, stage: str):
        self.image_in_progress = True
        if not self.image_voice_timer.isActive():
            self.image_voice_timer.start()
        lines = {
            "planning": ("Let me picture that for a moment.", "CURIOUS"),
            "encoding": ("I've got the scene in mind. I'm working on it.", "THINKING"),
            "rendering": ("It's taking shape now.", "HAPPY"),
        }
        label = {
            "planning": "Planning your image…", "loading": "Making room for the image model…",
            "encoding": "Reading your scene…", "loading_flux": "Loading FLUX…",
            "rendering": "Creating your image…", "saving": "Saving your image…",
        }.get(stage, f"Creating your image — {stage.replace('_', ' ')}…")
        self.say(label)
        now = time.monotonic()
        if stage in lines and (stage == "planning" or now - self.image_last_voice_time >= 12):
            self.progress_voice_request.emit(*lines[stage])
            self.image_last_voice_time = now

    def image_waiting_voice(self):
        if self.image_in_progress and time.monotonic() - self.image_last_voice_time >= 25:
            lines = ["I'm still here. This scene needs a little more time.",
                     "You can keep doing your thing. I'll let you know when it's ready."]
            # Two gentle updates at most; don't repeat a line indefinitely.
            if self.image_waiting_index < len(lines):
                self.progress_voice_request.emit(lines[self.image_waiting_index], "NEUTRAL")
                self.image_waiting_index += 1
                self.image_last_voice_time = time.monotonic()

    def finish_image_progress(self):
        self.image_in_progress = False
        self.image_voice_timer.stop()
        self.image_waiting_index = 0

    def handle_context_response(self, response):
        self.context_reaction_busy = False
        if (self.request_busy or not self.context_reactions_enabled
                or self.output_dismissed or response is None or not response.response.strip()):
            return
        self.say(response.response)
        self.context_reply_accepted.emit(response.response)
        if response.voice_line:
            self.queue_voice(response.voice_line, response.emotion.value, kind="context", pose=response.emotion.value)
        else:
            self.companion.set_state(response.emotion.value, "A little thought")
            self.play_emotion(response.emotion.value)

    # =========================================================
    # AI → GUI
    # =========================================================

    def handle_ai_response(
        self,
        response,
    ):

        self.request_busy = False
        self.finish_image_progress()
        if response is None:
            return
        response.response = readable_reply(response.response, response.voice_line)

        if response.image_path:
            try:
                preview = ImagePreview(response.image_path, self)
                self.image_previews.append(preview)
                preview.finished.connect(lambda _, item=preview: self.image_previews.remove(item))
                preview.show()
            except ValueError as exc:
                self.say(str(exc))
                return


        emotion = response.emotion.value
        pose = "EXPLAINING" if response.intent.value in {"CODE_ANALYSIS", "CODE_CHANGE", "GENERAL_QUESTION"} else emotion
        if response.image_path:
            pose = "PRESENTING"
        self.response_pose = pose
        if not response.voice_line:
            self.companion.set_state(pose, "Here with you")

        print(
            "VOICE LINE:",
            repr(response.voice_line),
        )

        print(
            "READ ALOUD:",
            response.read_aloud,
        )

        print(
            "EMOTION:",
            emotion,
        )

        # -----------------------------------------------------
        # CHARACTER REACTION
        # -----------------------------------------------------
        

        
        if not response.voice_line:
            self.play_emotion(emotion)

        # -----------------------------------------------------
        # FULL RESPONSE
        # -----------------------------------------------------

        self.say(
            response.response
        )

        # -----------------------------------------------------
        # READ-ALOUD
        # -----------------------------------------------------

        if response.read_aloud:

            self.pending_read_aloud_text = (
                response.response
            )

        else:

            self.pending_read_aloud_text = None

        # -----------------------------------------------------
        # CONTEXTUAL VOICE
        # -----------------------------------------------------

        voice_line = (
            response.voice_line.strip()
            if response.voice_line
            else ""
        )

        if voice_line:

            print(
                "SPEAKING:",
                repr(voice_line),
            )

            self.voice_request.emit(
                voice_line,
                emotion,
            )

    # =========================================================
    # AI ERROR
    # =========================================================

    def handle_ai_error(
        self,
        error: str,
    ):

        self.request_busy = False
        self.finish_image_progress()
        self.pending_read_aloud_text = None

        self.companion.set_state("SAD", "Let's try again")
        self.say(f"I couldn't finish this request. {error}")

        print(
            "AI ERROR:",
            error,
        )

    # =========================================================
    # VOICE ERROR
    # =========================================================

    @Slot(str)
    def handle_voice_error(
        self,
        error: str,
    ):

        print(
            "========== VOICE ERROR =========="
        )

        print(error)

        print(
            "================================="
        )

    # =========================================================
    # POSITION
    # =========================================================

    def move_to_bottom_right(self):

        screen = (
            QApplication
            .primaryScreen()
            .availableGeometry()
        )

        x = (
            screen.right()
            - self.width()
            - 340
        )

        y = (
            screen.bottom()
            - self.height()
            - 40
        )

        self.move(
            x,
            y,
        )

    # =========================================================
    # CLEANUP
    # =========================================================

    def closeEvent(
        self,
        event,
    ):

        self.scheduler.cancel()
        self.cancel_context_reaction()
        self.invalidate_speech()
        self.companion.close()
        self.speech.hide()
        self.chat_input.hide()
        self.browser_bridge.stop()

        self.ai_thread.quit()
        self.ai_thread.wait()

        self.voice_thread.quit()
        self.voice_thread.wait()

        self.stt_thread.quit()
        self.stt_thread.wait()

        event.accept()


    @Slot(object)
    def handle_browser_event(self, event):
        previous_page = (self.latest_browser.get("url"), self.latest_browser.get("title"))
        self.latest_browser = self.browser_context.as_dict()
        self.browser_revision += 1
        self.cancel_context_reaction()
        page_changed = previous_page != (event.url, event.title)
        # DOM/selection refreshes must never cut off the explicit answer.
        # Only a passive comment belonging to a page we left is stale speech.
        if (page_changed and self.speech_queue.active
                and self.speech_queue.active["kind"] == "context"):
            self.invalidate_speech()
        if (not self.request_busy and self.context_reactions_enabled
                and self.behavior_controller.should_react(event)):
            self.pending_browser_event = event
            self.context_debounce.start()

    def request_context_reaction(self):
        if (self.request_busy or self.speech_queue.active or self.output_dismissed or not self.context_reactions_enabled
                or time.monotonic() - self.last_user_activity < 12):
            return
        event = getattr(self, "pending_browser_event", None)
        if event is None or self.behavior_controller.handle_browser_event(event) is None:
            return
        snapshot = self.browser_context.as_dict()
        snapshot.update(_revision=self.browser_revision, _requested_at=time.monotonic())
        self.context_token = CancellationToken(deadline=time.monotonic() + 10)
        item = WorkItem("context", "", snapshot, self.context_token, uuid4().hex)
        self.context_reaction_busy = True
        self.work_request.emit(item)

    def startup_greeting(self):

        if self.request_busy or self.output_dismissed or self.has_user_interacted:
            return
        greeting="Hey. How are you doing?"

        self.say(
            greeting
                )        
        self.queue_voice(greeting, "HAPPY", kind="greeting", pose="HAPPY")

    # =========================================================
    # MICROPHONE / STT
    # =========================================================

    def handle_microphone_request(self):
        self.has_user_interacted = True
        self.ignore_stt_result = False

        print(
            "MICROPHONE: Listening..."
        )

        self.chat_input.set_microphone_enabled(
            False
        )

        self.chat_input.input.setPlaceholderText(
            "Listening..."
        )

        self.stt_request.emit()

    @Slot(str)
    def handle_stt_result(
        self,
        text: str,
    ):

        self.chat_input.set_microphone_enabled(
            True
        )
        if getattr(self, "ignore_stt_result", False):
            return

        self.chat_input.input.setPlaceholderText(
            "Speak to Hornet..."
        )

        text = text.strip()

        print(
            "STT RESULT:",
            repr(text),
        )

        if not text:
            return

        self.chat_input.input.setText(
            text
        )

        self.chat_input.submit()

    @Slot(str)
    def handle_stt_error(
        self,
        error: str,
    ):

        self.chat_input.set_microphone_enabled(
            True
        )

        self.chat_input.input.setPlaceholderText(
            "Speak to Hornet..."
        )

        print(
            "========== STT ERROR =========="
        )

        print(error)

        print(
            "==============================="
        )

