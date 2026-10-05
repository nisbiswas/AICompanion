import subprocess
from pathlib import Path


class AudioPlayer:
    def play(self, audio_path: str):
        path = Path(audio_path)

        if not path.exists():
            raise FileNotFoundError(
                f"Audio file not found: {path}"
            )

        subprocess.Popen(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                (
                    f'(New-Object Media.SoundPlayer '
                    f'"{path}").PlaySync()'
                ),
            ]
        )