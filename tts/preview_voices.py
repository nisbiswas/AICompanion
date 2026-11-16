"""Compare installed voices using the same PCM preparation as Hornet playback."""
import argparse
import json
from pathlib import Path
import sys

import soundfile as sf
from kokoro_onnx import Kokoro

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.voice.audio import prepare_audio
from app.voice.profile import language_for_voice


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--voices", nargs="+", default=["bf_emma", "bf_isabella"])
    parser.add_argument("--speed", type=float, default=.90)
    parser.add_argument("--text", default="There you are. Take your time. Tell me what you have found, and we can look at it together.")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "data/voice/previews")
    args = parser.parse_args()
    if not .5 <= args.speed <= 2.0:
        parser.error("Speed must be between 0.5 and 2.0.")
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    engine = Kokoro(str(ROOT / "tts/kokoro-v1.0.onnx"), str(ROOT / "tts/voices-v1.0.bin"))
    try:
        for voice in args.voices:
            if voice not in engine.get_voices():
                parser.error(f"Voice is not installed: {voice}")
        for voice in args.voices:
            lang = language_for_voice(voice)
            samples, rate = engine.create(args.text, voice=voice, speed=args.speed, lang=lang)
            path = output / f"{voice}_gentle.wav"
            sf.write(str(path), samples, rate, subtype="PCM_16")
            audio = prepare_audio(path)
            audio.save(path)
            print(json.dumps({"voice":voice, "speed":args.speed, "lang":lang,
                              "duration":round(audio.duration, 2), "audio":str(path)}), flush=True)
    finally:
        engine.voices.close()


if __name__ == "__main__":
    main()
