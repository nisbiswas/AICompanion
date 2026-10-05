import soundfile as sf
from kokoro_onnx import Kokoro


kokoro = Kokoro(
    "kokoro-v1.0.onnx",
    "voices-v1.0.bin",
)

text = (
    "Hello. I am your companion. "
    "It is nice to meet you."
)

samples, sample_rate = kokoro.create(
    text,
    voice="af_heart",
    speed=1.0,
    lang="en-us",
)

sf.write(
    "test_voice.wav",
    samples,
    sample_rate,
    subtype="PCM_16",
)

kokoro.voices.close()

print("Created test_voice.wav")