"""PCM preparation and an amplitude envelope for playback-driven gestures."""
from array import array
from dataclasses import dataclass
import math
import sys
import wave


@dataclass
class PreparedAudio:
    samples: array
    sample_rate: int
    channels: int
    levels: list[float]
    gain: float
    frame_seconds: float = 0.03

    @property
    def duration(self):
        return len(self.samples) / self.channels / self.sample_rate

    def save(self, path):
        samples = array("h", self.samples)
        if sys.byteorder != "little":
            samples.byteswap()
        with wave.open(str(path), "wb") as output:
            output.setnchannels(self.channels)
            output.setsampwidth(2)
            output.setframerate(self.sample_rate)
            output.writeframes(samples.tobytes())


def prepare_audio(path):
    with wave.open(str(path), "rb") as source:
        if source.getsampwidth() != 2 or source.getcomptype() != "NONE":
            raise ValueError("Voice playback expects uncompressed 16-bit PCM WAV audio.")
        channels, rate = source.getnchannels(), source.getframerate()
        samples = array("h", source.readframes(source.getnframes()))
    if sys.byteorder != "little":
        samples.byteswap()
    block = max(channels, int(rate * 0.03) * channels)
    rms = [math.sqrt(sum(x*x for x in samples[i:i+block]) / len(samples[i:i+block])) / 32768
           for i in range(0, len(samples), block)]
    maximum = max(rms, default=0)
    audible = [i for i, value in enumerate(rms) if value > max(0.001, maximum * 0.06)]
    if audible:
        # Preserve one window of breath around the utterance, while removing
        # synthesis padding that would make speaking animations lead the voice.
        first, last = max(0, audible[0]-1), min(len(rms), audible[-1]+2)
        samples = samples[first*block:last*block]
        rms = rms[first:last]
    peak = max((abs(x) for x in samples), default=0) / 32768
    voiced = [value for value in rms if value > max(0.001, maximum * 0.12)]
    active_rms = math.sqrt(sum(x*x for x in voiced)/len(voiced)) if voiced else 0
    # Consistent speech level with bounded gain and peak headroom. Never alter
    # the Windows mixer or the volume of another application.
    gain = min(6.0, 0.16 / active_rms, 0.95 / peak) if active_rms and peak else 1.0
    normalized = array("h", (max(-32767, min(32767, round(x*gain))) for x in samples))
    levels = [min(1.0, value / max(maximum, 0.001)) for value in rms]
    return PreparedAudio(normalized, rate, channels, levels, gain)
