# Firefox page reading and gentle voice

## Install the browser bridge

The same `browser_extension/` folder supports Chrome 121+ and Firefox 128+.
Chrome runs the background service worker; Firefox runs the background script.
The capture code uses each browser's native extension API.

1. Keep Hornet running with browser context and page reading enabled.
2. In Firefox, open `about:debugging#/runtime/this-firefox`.
3. Click **Load Temporary Add-on** and select `browser_extension/manifest.json`.
4. Allow site access if requested, then refresh existing web tabs.
5. Switch to a normal web page and ask Hornet to explain the current page.

A temporary add-on is removed when Firefox restarts. A permanent release needs
a Mozilla-signed XPI; signing/distribution is not part of the local bridge.
See [Mozilla's installation guide](https://extensionworkshop.com/documentation/develop/temporary-installation-in-firefox/).

Reload the Chrome extension at `chrome://extensions` too, and refresh existing
Chrome tabs. Both updated installations can remain enabled. Only the browser
window that currently has focus publishes captures; background browser alarms
and DOM mutations cannot replace it. A capture that finishes after focus leaves
is discarded. When you focus Hornet, its last browser snapshot is retained.

The bridge reads page text, selection and accessible editor documents. It does
not capture browser-internal pages, protected pages, video frames/audio, or hidden
transcripts. Firefox private-window access is off unless you enable it yourself.
It uses the existing local bridge at `127.0.0.1:8766`, not a cloud capture service.

## Gentle voice preset

Restart **both Hornet and the Kokoro TTS server** after this update. The new
default is `gentle`: British `bf_emma`, English `en-gb`, speed `0.90`. Emotion
changes stay near the base pace instead of accelerating happy/surprised speech.
Acknowledgements, image progress and answers use the same profile. The existing
volume normalization and playback-driven animation remain in place.

Optional settings in the repository's `.env` (no changes are needed for defaults):

```env
TTS_PROFILE=gentle
TTS_VOICE=bf_emma
TTS_SPEED=0.90
```

Try `TTS_VOICE=bf_isabella` as an alternative. Accent is inferred from voice
identity; `TTS_LANG=en-gb` or `en-us` can override it. For the original voice
and pacing, use `TTS_PROFILE=standard` and remove explicit voice/speed overrides.
Invalid settings produce a configuration error; speeds must be between 0.5 and
2.0. Very slow settings can sound less natural. Voice/accent/speed are part of
the acknowledgement cache key, so a changed profile does not reuse old clips.

Generate a comparison using only the already-installed Kokoro files:

```powershell
tts/.venv/Scripts/python.exe tts/preview_voices.py
```

The WAVs are saved in `data/voice/previews/`. They use the same gain preparation
as playback, making the comparison about tone rather than mismatched volume.
No model download or running TTS server is required for this command.

Kokoro's current integration controls voice identity, language and speaking
speed. It has no whisper/style-conditioning input. This preset approximates a
calm, Firekeeper-inspired presence; it does not reproduce the character's actor
or create genuine whispered ASMR. Slowing speech or reducing volume alone cannot
add the breathiness and delivery of a whispered recording. The next fidelity
step would be an expressive TTS model with supported whisper/style conditioning,
auditioned with an original or licensed reference voice. Evaluate latency and
GPU memory alongside Qwen/FLUX before replacing the lightweight local engine.

One candidate to audition is
[Qwen3-TTS VoiceDesign](https://github.com/QwenLM/Qwen3-TTS), whose API accepts
natural-language voice/style instructions. A useful starting description is:
"An adult feminine British voice, warm lower register, gentle breathiness,
unhurried near-whisper, intimate and reassuring, with clear consonants and
subtle emotion." This is an audition target, not a guaranteed result. That
model is not installed or integrated by this change; Windows compatibility,
latency, identity consistency and shared GPU memory need measurement first.

## Checks

```powershell
node tests/browser_capture.test.cjs
.venv/Scripts/python.exe -m unittest discover -s tests -v
```

The JavaScript tests exercise both browser APIs, editor capture, content-script
notifications, active-tab filtering and focus changes. They do not replace a
live Firefox installation check.
