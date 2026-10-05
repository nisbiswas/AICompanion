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

    # Send user messages to the AI worker thread.
    ai_request = Signal(str)

    # Send short voice reactions to the TTS worker thread.
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

        # Move AI worker away from GUI thread.
        self.ai_worker.moveToThread(
            self.ai_thread
        )

        # GUI -> AI worker
        self.ai_request.connect(
            self.ai_worker.process
        )

        # AI worker -> GUI
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

        # Move TTS worker away from GUI thread.
        self.voice_worker.moveToThread(
            self.voice_thread
        )

        # GUI -> Voice worker
        self.voice_request.connect(
            self.voice_worker.speak
        )

        # Voice worker -> GUI
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

        # Remember normal state.
        self.base_state = (
            self.character.state
        )

        # Switch to reaction.
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
    # SPEECH
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

        # Place input to the LEFT of Hornet.
        x = (
            character_rect.left()
            - self.chat_input.width()
            - 20
        )

        # Vertically center it with Hornet.
        y = (
            character_rect.center().y()
            - self.chat_input.height() // 2
        )

        # Keep inside monitor horizontally.
        x = max(
            available.left() + 10,
            min(
                x,
                available.right()
                - self.chat_input.width()
                - 10,
            ),
        )

        # Keep inside monitor vertically.
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
            y,
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

        # Tell user that Hornet is processing.
        self.say(
            "Hmm..."
        )

        # Send message to AI worker.
        #
        # IMPORTANT:
        #
        # We do NOT call the AI directly here.
        #
        # The GUI remains responsive while Ollama
        # generates the response.

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

        # -----------------------------------------------------
        # CHARACTER REACTION
        # -----------------------------------------------------

        self.play_emotion(
            emotion
        )

        # -----------------------------------------------------
        # FULL TEXT RESPONSE
        # -----------------------------------------------------

        # The complete AI response is shown in the
        # speech bubble.
        #
        # It is NOT sent to TTS.

        self.say(
            response.response
        )

        # -----------------------------------------------------
        # SHORT VOICE REACTION
        # -----------------------------------------------------

        voice_line = self.get_voice_line(
            emotion
        )

        if voice_line:

            self.voice_request.emit(
                voice_line,
                emotion,
            )

    def get_voice_line(
        self,
        emotion: str,
    ) -> str | None:

        emotion = emotion.upper()

        voice_lines = {

            # Normal response.
            "NEUTRAL":
                "Hmm... look at this.",

            # Happy / playful.
            "HAPPY":
                "Hehe... look at this.",

            # Shy.
            #
            # The "...", combined with the slower
            # TTS speed, creates a small pause.
            "SHY":
                "Umm... here...",

            # Annoyed / slightly aggressive.
            "ANNOYED":
                "Tch... seriously?",

            # Sad.
            "SAD":
                "Hmm... that's unfortunate.",

            # Curious.
            "CURIOUS":
                "Hmm? What's this?",

            # Surprised.
            "SURPRISED":
                "W-Wait... what?",

            # Thinking.
            "THINKING":
                "Hmm...",
        }

        return voice_lines.get(
            emotion,
            "Hmm...",
        )

    def handle_ai_error(
        self,
        error: str,
    ):

        self.say(
            "Sorry... something went wrong."
        )

        print(
            "AI ERROR:",
            error,
        )

    # =========================================================
    # VOICE
    # =========================================================

    def handle_voice_error(
        self,
        error: str,
    ):

        # Voice failure should NOT break the
        # character or AI response.

        print(
            "VOICE ERROR:",
            error,
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

        # Stop AI thread.
        self.ai_thread.quit()

        self.ai_thread.wait()

        # Stop voice thread.
        self.voice_thread.quit()

        self.voice_thread.wait()

        event.accept()