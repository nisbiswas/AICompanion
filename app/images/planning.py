"""Compile a visual brief within Schnell's conditioning budget."""
import json
import re
from dataclasses import dataclass


@dataclass(frozen=True)
class ImagePlan:
    prompt: str
    clip_prompt: str
    width: int = 1024
    height: int = 1024
    note: str = ""


PLAN_SCHEMA = {
    "type": "object",
    "properties": {
        "prompt": {"type": "string"},
        "clip_prompt": {"type": "string"},
        "aspect": {"type": "string", "enum": ["square", "portrait", "landscape"]},
        "note": {"type": "string"},
    },
    "required": ["prompt", "clip_prompt", "aspect", "note"],
}

PLAN_PROMPT = """Compile the user's image brief for FLUX.1-schnell. Return JSON.
prompt: a concrete visual description in at most 100 English words, subject and
action first, then composition, essential secondary elements, lighting and style.
Preserve named characters, appearance, left/right placement and requested words.
Keep the main subject's clothing, colors, pose and expression before tiny props
or extra background landmarks, even when shortening a crowded brief.
For a known character such as Sekiro's Wolf, describe the human face, tied hair,
orange shinobi coat, scarf, prosthetic left arm and katana when appropriate.
Wolf is a human nickname, not an animal. Describe him as a human Japanese male
shinobi named Sekiro; don't use 'Wolf' alone as the main subject. Resolve other
ambiguous character aliases into their concrete visual identity as well.
Do not replace a named subject with an unrelated generic figure. Prefer clear
human anatomy and readable faces; don't add arbitrary details to an explicit brief.
Do not add 'masterpiece', quality-tag lists, negative-prompt lists or contradictions.
clip_prompt: at most 30 English words giving the subject, composition and style.
aspect: follow requested framing; epic wide-angle multi-subject scenes use landscape,
portraits use portrait, otherwise square. note: concise explanation if a crowded
brief was simplified, or if small text/character likeness cannot be guaranteed.
Never claim every detail of a crowded scene is guaranteed. A long scene must keep
the main relationship and core landmarks ahead of tiny background decorations.
"""


class ImagePromptPlanner:
    def __init__(self, llm):
        self.llm = llm

    def plan(self, prompt, history=None):
        messages = [{"role": "system", "content": PLAN_PROMPT}]
        messages += (history or [])[-4:]
        messages += [{"role": "user", "content": prompt}]
        data = json.loads(self.llm.chat(messages, schema=PLAN_SCHEMA))
        # Small models sometimes ignore prose length limits. Validate and ask for
        # an actual shorter composition before the image engine sees the brief.
        if len(str(data.get("prompt", "")).split()) > 110:
            messages.extend([
                {"role": "assistant", "content": json.dumps(data)},
                {"role": "user", "content": (
                    "That image prompt exceeds the hard length limit. Rewrite the JSON. "
                    "Use only 70 to 90 words for prompt, no style-tag list. Keep the main "
                    "character, their action, and the most important spatial relationships. "
                    "Explain omitted small details in note. Keep clip_prompt under 30 words."
                )},
            ])
            data = json.loads(self.llm.chat(messages, schema=PLAN_SCHEMA))
        sizes = {"square": (1024, 1024), "portrait": (768, 1152), "landscape": (1152, 768)}
        width, height = sizes.get(data.get("aspect"), sizes["square"])
        description = str(data.get("prompt", "")).strip()
        clip = str(data.get("clip_prompt", "")).strip()
        if "sekiro" in prompt.lower():
            # Avoid the model rendering the literal animal when it sees the alias.
            description = re.sub(r"\bWolf\b", "Sekiro", description, flags=re.IGNORECASE)
            clip = re.sub(r"\bWolf\b", "Sekiro", clip, flags=re.IGNORECASE)
            if "human" not in description.lower():
                description = "A human Japanese male shinobi named Sekiro, with a visible human face. " + description
            if "human" not in clip.lower():
                clip = "Human Japanese male shinobi Sekiro. " + clip
        if not description or not clip:
            raise ValueError("Image planning returned an empty description. Please try again.")
        if len(description.split()) > 110:
            raise ValueError("The image brief is still too crowded for Schnell. Try one main subject and two background elements.")
        return ImagePlan(description, clip, width, height, str(data.get("note", "")))
