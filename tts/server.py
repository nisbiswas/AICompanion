import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from uuid import uuid4

import soundfile as sf
from kokoro_onnx import Kokoro


HOST = "127.0.0.1"
PORT = 8765

BASE_DIR = Path(__file__).resolve().parent

MODEL_PATH = BASE_DIR / "kokoro-v1.0.onnx"
VOICES_PATH = BASE_DIR / "voices-v1.0.bin"

OUTPUT_DIR = BASE_DIR / "audio"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

VOICE = "af_heart"
SPEED = 1.0
LANG = "en-us"


print("Loading Kokoro...")

kokoro = Kokoro(
    str(MODEL_PATH),
    str(VOICES_PATH),
)

print("Kokoro loaded.")
print(f"TTS server listening on http://{HOST}:{PORT}")


class TTSHandler(BaseHTTPRequestHandler):

    def do_POST(self):
        if self.path != "/speak":
            self.send_error(404, "Not found")
            return

        try:
            content_length = int(
                self.headers.get("Content-Length", "0")
            )

            body = self.rfile.read(content_length)
            data = json.loads(body.decode("utf-8"))

            text = str(data.get("text", "")).strip()

            if not text:
                self.send_error(400, "Missing text")
                return

            voice = str(
                data.get("voice", VOICE)
            )

            speed = float(
                data.get("speed", SPEED)
            )

            print(f"Speaking: {text}")
            print(f"Voice: {voice}, Speed: {speed}")

            samples, sample_rate = kokoro.create(
                text,
                voice=voice,
                speed=speed,
                lang=LANG,
            )

            output_path = OUTPUT_DIR / f"speech_{uuid4().hex}.wav"
            sf.write(
                output_path,
                samples,
                sample_rate,
                subtype="PCM_16",
            )

            response = {
                "success": True,
                "audio": str(output_path),
            }
            # Clients copy their clip before playback. Keep a bounded server
            # output directory rather than ever rewriting a WAV in use.
            previous = sorted(OUTPUT_DIR.glob("speech_*.wav"), key=lambda path: path.stat().st_mtime, reverse=True)
            for old in previous[64:]:
                try:
                    old.unlink()
                except OSError:
                    pass

            response_bytes = json.dumps(
                response
            ).encode("utf-8")

            self.send_response(200)
            self.send_header(
                "Content-Type",
                "application/json",
            )
            self.send_header(
                "Content-Length",
                str(len(response_bytes)),
            )
            self.end_headers()

            self.wfile.write(response_bytes)

        except Exception as exc:
            print("TTS ERROR:", exc)

            response = {
                "success": False,
                "error": str(exc),
            }

            response_bytes = json.dumps(
                response
            ).encode("utf-8")

            self.send_response(500)
            self.send_header(
                "Content-Type",
                "application/json",
            )
            self.send_header(
                "Content-Length",
                str(len(response_bytes)),
            )
            self.end_headers()

            self.wfile.write(response_bytes)

    def log_message(self, format, *args):
        return


server = HTTPServer(
    (HOST, PORT),
    TTSHandler,
)

try:
    server.serve_forever()
except KeyboardInterrupt:
    print("\nStopping TTS server...")
finally:
    server.server_close()
    kokoro.voices.close()
