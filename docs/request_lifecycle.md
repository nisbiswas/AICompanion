# Requests, cancellation and fresh context

## Successive submissions

The desktop companion uses **latest request wins**. A new message cancels the
running request and replaces any pending message. There is one running item and
at most one pending item, so rapid corrections cannot create a long invisible
queue. The output says when it is switching to the latest request. An explicit
multi-step instruction should be submitted as one message.

Stop is available in both the output bubble and fixed companion panel. Escape
in the chat input or focused output also cancels. Stop clears the pending item,
cancels active work and interrupts speech. Closing the output with **×** dismisses
text and speech; generation can finish quietly. A later explicit request opens
the output again. Passive observations do not reopen dismissed output.

Every item has a cancellation token, an ID and its own browser snapshot. The GUI
accepts only the current ID. HTTP inference streams are closed on cancellation;
the isolated FLUX process is killed and reaped. Speech requests have expiring
tokens, and Windows audio playback can be stopped without untracked PowerShell
players. Cancelling a request rolls back its unfinished conversation entries.

## Complete output

The output is Markdown with selectable text and vertical/horizontal scrollbars.
Its height is bounded so it fits on screen, but content is not discarded. The
model's final stream event is checked: a token-limited result is retried once
with more output tokens, and disconnected/incomplete JSON is not presented as
a completed answer. The compact active prompt asks for complete requested
methods and prohibits claims of editing unseen files.

## Browser capture

Reload the unpacked extension and refresh open browser tabs after this update.
The content script debounces visible DOM, selection and editor input changes.
Captures prioritize main/article text over navigation, include selected text,
and read accessible Monaco/CodeMirror/Ace documents and visible textareas/pre
blocks separately. The bridge receives capture length/truncation metadata.
Model input includes editor code independently from a page's description.

This is browser text context, not whole-desktop vision. Canvas/video pixels,
images and editor state not exposed by the page are not understood. A virtualized
editor whose full model is inaccessible may only expose visible lines. The
companion should say when code is missing instead of claiming it changed it.
The text capture is bounded at 24,000 characters plus 16,000 editor characters;
the model receives a further bounded excerpt with an explicit truncation flag.

Each explicit request snapshots context when submitted. Background context is
not put in a queued stream of worker slots. Passive comments use only the current
page, without old projects or conversation history. A page change or explicit
request cancels a pending comment. Passive inference has a 10-second deadline;
comments older than 15 seconds or carrying an old page revision are discarded.
Unchanged-page refreshes cannot create a delayed backlog. Displayed observations
are recorded as assistant messages so the next user reply has context.

## Characters

Hornet is rendered at 2x scale instead of 4x and follows within screen bounds.
The new original stylized companion occupies a fixed 300x340 stage at the bottom
right. Its transparent 16-pose atlas supplies explaining/presenting hand gestures,
thinking, playful waving/winking, annoyance, shyness, concern and surprise.
Idle breathing and blinking continue between replies. Speech and intent/emotion
select the pose sequences. This is sprite animation, not generated video or a
full skeletal face rig.


## Research outcomes

Research starts OFF and the chat control explicitly displays **Research OFF** or
**Research ON**. This is a permission, not a mode that forces searches for browser
questions. Natural follow-up clarifications preserve a research intent, and
current-product searches include the current year unless a historical date was
requested. Permission being disabled does not change the intent into ordinary chat.

A disabled search, failed backend or empty result set stops a web-only request
with a deterministic explanation. It is not sent back to the model to produce
an outdated recommendation from training knowledge. Combined page/research
requests may still explain the supplied page, with external verification clearly
marked as unavailable. Successful research passes actual sources to the model
and includes their URLs in the response. Search success cannot be presented as
an unavailable-search apology.

The backend reports connection failure, timeout, invalid JSON and HTTP errors
separately. The local SearXNG base URL can be overridden with `SEARXNG_URL`.
A 403 JSON-format denial points to `search.formats` in SearXNG settings. A healthy
homepage alone does not prove that JSON search or upstream engines are working.


## Speech and animation timing

Each explicit chat request speaks a cached **"Hmm... taking a look."** acknowledgement.
Image requests use a matching image-planning acknowledgement. A result arriving
quickly waits for that short acknowledgement to finish. There is one active
utterance and at most one pending answer. Progress narration, passive comments
and startup greetings cannot interrupt an explicit answer. A new request, Stop
or dismissing output still interrupts the current sequence immediately.

Routine DOM/selection refreshes no longer stop result speech. Leaving a browser
page cancels only a passive comment tied to that page. Startup greetings are
skipped after the user has already interacted. Speech expiry guards waiting and
synthesis; it is removed at playback start so it cannot clip the tail of a valid
utterance or long read-aloud.

The player prepares a private 16-bit PCM WAV, removes leading/trailing synthesis
padding, applies bounded loudness normalization and preserves peak headroom.
It never changes the system mixer or other applications. The TTS client snapshots
each returned clip so older servers that reuse output.wav cannot rewrite audio
being played. The updated TTS server also gives clips unique filenames and keeps
a bounded output folder. Cached acknowledgements are stored in data/voice;
ordinary client clips and normalized playback files are removed after use.

Playback start, amplitude updates and playback end drive the character. Explicit
Qt slots route these events onto the GUI thread. The roaming Hornet reaction is
held for the spoken line, and the fixed companion starts its gesture sequence
when playback starts. Quiet intervals pause the gesture clock; explanation
sprites use an open/closed-mouth pair selected by audio amplitude. This is
amplitude-driven sprite animation, not phoneme-level lip sync.

Restart Hornet for the client changes. Restart the Kokoro TTS server as well to
apply unique server-side WAV filenames. Client snapshots remain compatible with
the previous server while it is still running.
