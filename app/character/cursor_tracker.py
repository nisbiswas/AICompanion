from PySide6.QtCore import QObject, QTimer
from PySide6.QtGui import QCursor


class CursorTracker(QObject):

    def __init__(
        self,
        window,
        follow_distance: int = 140,
        speed: float = 0.12,
    ):
        super().__init__(window)

        self.window = window
        self.follow_distance = follow_distance
        self.speed = speed

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_position)

    def start(self):
        if not self.timer.isActive():
            self.timer.start(30)

    def stop(self):
        self.timer.stop()

    def update_position(self):
        cursor = QCursor.pos()

        current = self.window.frameGeometry().center()

        dx = cursor.x() - current.x()
        dy = cursor.y() - current.y()

        distance_squared = dx * dx + dy * dy

        if distance_squared <= self.follow_distance ** 2:
            return

        # Tell the character which direction she is moving.
        if dx > 0:
            self.window.set_facing_right(True)
        elif dx < 0:
            self.window.set_facing_right(False)

        # Smooth movement.
        new_x = int(current.x() + dx * self.speed)
        new_y = int(current.y() + dy * self.speed)

        target_center = current.__class__(new_x, new_y)

        top_left = (
            target_center
            - self.window.rect().center()
        )

        self.window.move(top_left)