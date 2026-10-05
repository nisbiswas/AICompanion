from PySide6.QtCore import Qt, QTimer, QThread, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QApplication, QLabel, QWidget

from app.character.character import Character
from app.character.states import CharacterState
from app.ui.chat_input import ChatInput
from app.ui.speech_bubble import SpeechBubble
from app.ui.ai_worker import AIWorker
from app.voice.worker import VoiceWorker


class CharacterWindow(QWidget):

    # =========================================================
    # SIGNALS
    # =========================================================

    ai_request = Signal(str)
    voice_request = Signal(str, str)

    SCALE = 4

    CANVAS_WIDTH = 352
    CANVAS_HEIGHT = 256

    REACTION_DURATION = 1200

    def __init__(self, controller):
        super().__init__()

        self.controller = controller

        # =====================================================
        # AI WORKER THREAD
        # =====================================================

        self.ai_thread = QThread(self)

        self.ai_worker = AIWorker()

        self.ai_worker.moveToThread(
            self.ai_thread
        )

        self.ai_request.connect(
            self.ai_worker.process
        )

        self.ai_worker.finished.connect(
            self.handle_ai_response
        )

        self.ai_worker.error.connect(
            self.handle_ai_error
        )

        self.ai_thread.start()

        # =====================================================
        # VOICE WORKER THREAD
        # =====================================================

        self.voice_thread = QThread(self)

        self.voice_worker = VoiceWorker()

        self.voice_worker.moveToThread(
            self.voice_thread
        )

        self.voice_request.connect(
            self.voice_worker.speak
        )

        self.voice_worker.error.connect(
            self.handle_voice_error
        )

        self.voice_thread.start()

        # =====================================================
        # CHARACTER
        # =====================================================

        self.character = Character()

        self.frame_index = 0
        self.base_state = CharacterState.IDLE
        self.reaction_active = False

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

        # =====================================================
        # CHAT INPUT
        # =====================================================

        self.chat_input = ChatInput()

        self.chat_input.submitted.connect(
            self.handle_user_message
        )

        self.chat_input.cancelled.connect(
            self.hide_input
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
            lambda: self.say(
                "Hey! What are you doing?"
            ),
        )

        QTimer.singleShot(
            5000,
            self.hide_speech,
        )

    # =========================================================
    # ANIMATION
    # =========================================================

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

        self.speech.say_near(
            text,
            self,
        )

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

        self.say(
            "Hmm..."
        )

        self.ai_request.emit(
            text
        )

    # =========================================================
    # AI → GUI
    # =========================================================

    def handle_ai_response(
        self,
        response,
    ):

        if response is None:
            return

        emotion = response.emotion.value

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

        self.play_emotion(
            emotion
        )

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

        self.pending_read_aloud_text = None

        self.say(
            "Sorry... something went wrong."
        )

        print(
            "AI ERROR:",
            error,
        )

    # =========================================================
    # VOICE ERROR
    # =========================================================

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
            - 40
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

        self.ai_thread.quit()

        self.ai_thread.wait()

        self.voice_thread.quit()

        self.voice_thread.wait()

        event.accept()