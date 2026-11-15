# Hornet companion direction

The first release keeps the existing animated Hornet character. The personality
moves toward a calm, gentle, curious adult feminine companion: specific attentive
questions, quiet affection, occasional light teasing, and continuity across days.
A technical question still receives a capable technical answer. Voice reactions
are brief and natural. Screen observations should feel like an invitation to talk,
not repeated announcements of what the user opened.

## Human-face direction

The later visual identity should be an original adult character inspired by the
quiet presence of the Dark Souls III Firekeeper, rather than a literal copy:
silver-blonde hair, soft facial features, a charcoal robe, restrained antique-gold
accents and warm candlelight. The face needs readable eyes and gentle curious
expressions; a permanent eye covering would make expressive interaction harder.
The user can select the visual style without changing the companion's memory.

Start with one consistent portrait and expression variants (neutral, curious,
small smile, thinking, concerned and speaking). Keep the asset identity fixed
across variants. A lightweight 2D layered rig with mouth shapes and blinking is a
better first desktop implementation than running a video-diffusion model on
every response. Later, a Live2D-style or 3D rig could add gaze and lip sync.
The current release adds an original stylized 2D human companion atlas and fixed
desktop stage. It includes pose-based gestures, blinking and breathing. Skeletal
face animation and phoneme-level lip sync remain later stages.

## Runtime design

The Chrome bridge is the currently implemented source of visual context: title,
URL and visible text. It is sufficient for browsing, articles and text visible on
video pages, but does not see video frames or the rest of the desktop. A later
whole-desktop feature should have a visible capture toggle and capture on demand,
then summarize the image through a local vision model before returning to Qwen.
That vision stage should share the GPU handoff used by image generation.

Conversation history is durable on disk. The prompt selects recent exchanges and
relevant older conversations, so memory storage can grow without keeping all of
it in VRAM. The initial Qwen context is 24k tokens and is configurable. This can
be profiled upward for a specific model/quantization, but the app should not
promise that the GPU can fit every stored conversation at once.

## Current controls

Right-click Hornet to toggle contextual comments. Research permission continues
to govern external searches independently. Image generation emits stage updates
and bounded voice reactions through the existing CPU-friendly Kokoro service.
Conversation and image work remain serialized on the AI worker. During image
inference, Qwen is unloaded, and contextual model reactions are skipped.


## Measured profile

On this machine, 24k Qwen context stayed fully on the GPU; 32k offloaded 7% to
CPU. The default therefore uses 24,576 tokens and a conservative 9,000-token
history budget. The journal keeps all new exchanges, while recent-history
selection considers 30 exchanges and retrieves matching older ones. This is
long-term memory on disk, not an attempt to keep unlimited KV cache on the GPU.


## Implemented stylized stage

The selected first visual style is a stylized 2D original adult woman. The new
`CompanionPanel` uses a generated 4x4 RGBA atlas, with 16 poses, fixed positioning
at the bottom right and intent/emotion-driven gesture sequences. The smaller
Hornet remains the roaming mascot. Clicking either character opens chat. A Stop
control on the fixed stage remains available after dismissing output. See
`request_lifecycle.md` for the new cancellation and fresh-context behavior.
