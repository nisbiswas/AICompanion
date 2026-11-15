"""Run the isolated FLUX environment without importing torch into the desktop app."""
import json
import os
import time
from app.ai.cancellation import check_cancelled
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

    def generate(self, prompt: str, unload_model, *, plan=None, progress=None) -> str:
        if not prompt.strip():
            raise ValueError("Describe the image you want to create.")
        if not self.python.is_file():
            raise RuntimeError("Image engine Python not found. Set IMAGE_ENGINE_PYTHON in .env.")
        with IMAGE_LOCK:
            self.output_dir.mkdir(parents=True, exist_ok=True)
            output = (self.output_dir / f"hornet_{uuid4().hex}.png").resolve()
            progress_path = output.with_suffix(".progress.json")
            request = {"prompt": plan.prompt if plan else prompt, "original_prompt": prompt,
                       "output": str(output), "progress_path": str(progress_path)}
            if plan:
                request.update(clip_prompt=plan.clip_prompt, width=plan.width, height=plan.height,
                               planning_note=plan.note)
            if os.getenv("IMAGE_SEED"):
                request["seed"] = int(os.environ["IMAGE_SEED"])
            if progress:
                progress("loading")
            unload_model()
            try:
                check_cancelled()
                process = subprocess.Popen(
                    [str(self.python), str(ROOT / "image_engine/generate.py")],
                    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    text=True, encoding="utf-8", errors="replace", cwd=str(ROOT),
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                )
                deadline = time.monotonic() + float(os.getenv("IMAGE_GENERATION_TIMEOUT", "900"))
                first, last_stage = True, None
                try:
                    while True:
                        check_cancelled()
                        if time.monotonic() >= deadline:
                            raise subprocess.TimeoutExpired("image engine", 900)
                        try:
                            stdout, stderr = process.communicate(input=json.dumps(request) if first else None, timeout=0.2)
                            result = subprocess.CompletedProcess(process.args, process.returncode, stdout, stderr)
                            break
                        except subprocess.TimeoutExpired:
                            first = False
                            if progress and progress_path.exists():
                                try:
                                    stage = json.loads(progress_path.read_text(encoding="utf-8"))["stage"]
                                    if stage != last_stage:
                                        progress(stage)
                                        last_stage = stage
                                except (OSError, ValueError, KeyError):
                                    pass
                finally:
                    if process.poll() is None:
                        process.kill()
                        process.communicate(timeout=10)
            except subprocess.TimeoutExpired as exc:
                raise RuntimeError("Image generation timed out; the image process was stopped.") from exc
            finally:
                progress_path.unlink(missing_ok=True)
            if result.returncode != 0:
                detail = (result.stderr or result.stdout).strip()[-2000:]
                raise RuntimeError(f"Image generation failed: {detail}")
            if not output.is_file() or not output.stat().st_size:
                raise RuntimeError("The image engine did not produce an image.")
            return str(output)
