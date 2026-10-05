from pathlib import Path

from app.character.states import CharacterState


class Character:
    def __init__(self):
        self.assets_dir = (
            Path(__file__).resolve().parents[2]
            / "assets"
            / "character"
            / "hornet"
        )

        self.state = CharacterState.IDLE

        self.animations = {
            CharacterState.IDLE: {
                "path": self.assets_dir / "hornet_idle_pixel.png",
                "frames": 2,
            },
            CharacterState.RUN: {
                "path": self.assets_dir / "hornet_run_pixel.png",
                "frames": 2,
            },
            CharacterState.SITTING: {
                "path": self.assets_dir / "hornet_sitting_pixel.png",
                "frames": 1,
            },
            CharacterState.TAUNT: {
                "path": self.assets_dir / "hornet_taunt_pixel.png",
                "frames": 1,
            },
            CharacterState.ATTACK: {
                "path": self.assets_dir / "pixel_hornet_attack.png",
                "frames": 1,
            },
        }

        self.emotion_animation_map = {
            "NEUTRAL": CharacterState.IDLE,
            "HAPPY": CharacterState.TAUNT,
            "SHY": CharacterState.SITTING,
            "ANNOYED": CharacterState.ATTACK,
            "SAD": CharacterState.SITTING,
            "CURIOUS": CharacterState.IDLE,
            "SURPRISED": CharacterState.ATTACK,
            "THINKING": CharacterState.SITTING,
        }

    def set_state(self, state: CharacterState):
        if state not in self.animations:
            raise ValueError(f"No animation available for {state}")

        self.state = state

    def set_emotion(self, emotion: str):
        emotion = emotion.upper()

        state = self.emotion_animation_map.get(
            emotion,
            CharacterState.IDLE,
        )

        self.set_state(state)

    def current_animation(self):
        return self.animations[self.state]