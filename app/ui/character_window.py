from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QApplication, QLabel, QWidget

from app.character.character import Character
from app.ui.chat_input import ChatInput
from app.ui.speech_bubble import SpeechBubble


class CharacterWindow(QWidget):
    SCALE = 4

    def __init__(self, controller):
        super().__init__()

        self.controller = controller
        self.character = Character()
        self.frame_index = 0

        # -------------------------
        # Window
        # -------------------------

        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
        )

        self.setAttribute(Qt.WA_TranslucentBackground)

        # -------------------------
        # Hornet
        # -------------------------

        self.label = QLabel(self)

        self.label.setAttribute(
            Qt.WA_TransparentForMouseEvents
        )

        self.label.setAttribute(
            Qt.WA_TranslucentBackground
        )

        # -------------------------
        # Speech bubble
        # -------------------------

        self.speech = SpeechBubble()

        # -------------------------
        # Input
        # -------------------------

        self.chat_input = ChatInput()

        self.chat_input.submitted.connect(
            self.handle_user_message
        )

        self.chat_input.cancelled.connect(
            self.hide_input
        )

        # -------------------------
        # Animation
        # -------------------------

        self.timer = QTimer(self)
        self.timer.timeout.connect(
            self.next_frame
        )

        self.load_animation()

        self.move_to_bottom_right()

        self.timer.start(160)

        # -------------------------
        # Startup greeting
        # -------------------------

        QTimer.singleShot(
            700,
            lambda: self.say(
                "Hey! What are you doing?"
            )
        )

        QTimer.singleShot(
            4700,
            self.hide_speech
        )

    # =========================
    # Animation
    # =========================

    def load_animation(self):
        animation = self.character.current_animation()

        pixmap = QPixmap(
            str(animation["path"])
        )

        frame_count = animation["frames"]

        frame_width = (
            pixmap.width() // frame_count
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

        self.label.setPixmap(frame)
        self.label.resize(frame.size())

        self.resize(frame.size())

    def next_frame(self):
        animation = self.character.current_animation()

        frame_count = animation["frames"]

        if frame_count <= 1:
            return

        self.frame_index = (
            self.frame_index + 1
        ) % frame_count

        self.load_animation()

    # =========================
    # Speech
    # =========================

    def say(self, text: str):
        if not text:
            return

        self.speech.say(text)
        self.position_speech()

    def hide_speech(self):
        self.speech.hide()

    def position_speech(self):
        bubble_width = self.speech.width()
        bubble_height = self.speech.height()

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

        self.speech.move(x, y)

    # =========================
    # Interaction
    # =========================

    def mousePressEvent(self, event):
        if event.button() != Qt.LeftButton:
            return

        self.show_input()

    def show_input(self):
        self.chat_input.move(
            self.x()
            + self.width() // 2
            - self.chat_input.width() // 2,
            self.y()
            - self.chat_input.height()
            - 20,
        )

        self.chat_input.show()
        self.chat_input.raise_()
        self.chat_input.setFocus()

    def hide_input(self):
        self.chat_input.hide()

    def handle_user_message(self, text: str):
        self.hide_input()

        self.say("Hmm...")

        QApplication.processEvents()

        response = (
            self.controller.respond_to_user(text)
        )

         # Change Hornet's animation based on her emotion
        self.character.set_emotion(
            response.emotion.value
     )

    # Reset animation to the first frame
        self.frame_index = 0
        self.load_animation()

        self.say(response.response)
    # =========================
    # Position
    # =========================

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

        self.move(x, y)