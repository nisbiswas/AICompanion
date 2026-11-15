"""Run the isolated FLUX environment without importing torch into the desktop app."""
import json
import os
from pathlib import Path
import subprocess
from threading import Lock
from uuid import uuid4


ROOT = Path(__file__).resolve().parents[2]
IMAGE_LOCK = Lock()


class ImageGenerationService:
    def __init__(self):
        default_python = ROOT / "image_engine" / ".venv" / (
            "Scripts/python.exe" if os.name == "nt" else "bin/python"
        )
        self.python = Path(os.getenv("IMAGE_ENGINE_PYTHON", str(default_python)))
        self.output_dir = Path(os.getenv("IMAGE_OUTPUT_DIR", str(ROOT / "generated/images")))

    def generate(self, prompt: str, unload_model) -> str:
        if not prompt.strip():
            raise ValueError("Describe the image you want to create.")
        if not self.python.is_file():
            raise RuntimeError("Image engine Python not found. Set IMAGE_ENGINE_PYTHON in .env.")
        with IMAGE_LOCK:
            self.output_dir.mkdir(parents=True, exist_ok=True)
            output = (self.output_dir / f"hornet_{uuid4().hex}.png").resolve()
            unload_model()
            try:
                result = subprocess.run(
                    [str(self.python), str(ROOT / "image_engine/generate.py")],
                    input=json.dumps({"prompt": prompt, "output": str(output)}),
                    text=True, encoding="utf-8", errors="replace",
                    capture_output=True, cwd=str(ROOT),
                    timeout=float(os.getenv("IMAGE_GENERATION_TIMEOUT", "900")),
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                )
            except subprocess.TimeoutExpired as exc:
                raise RuntimeError("Image generation timed out; the image process was stopped.") from exc
            if result.returncode != 0:
                detail = (result.stderr or result.stdout).strip()[-2000:]
                raise RuntimeError(f"Image generation failed: {detail}")
            if not output.is_file() or not output.stat().st_size:
                raise RuntimeError("The image engine did not produce an image.")
            return str(output)
