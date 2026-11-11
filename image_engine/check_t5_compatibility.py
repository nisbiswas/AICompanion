
from pathlib import Path
import torch
from transformers import T5Config, T5EncoderModel

ROOT = Path(__file__).resolve().parent.parent
CHECKPOINT = ROOT / "models" / "flux" / "FLUX.1-schnell-text_encoder_2-FP8.pt"

if not CHECKPOINT.exists():
    raise FileNotFoundError(CHECKPOINT)

print("Loading checkpoint metadata...")
checkpoint = torch.load(
    CHECKPOINT,
    map_location="cpu",
    weights_only=True,
    mmap=True,
)

if "state_dict" not in checkpoint:
    raise KeyError(f"Expected 'state_dict'. Found: {list(checkpoint.keys())}")

weights = checkpoint["state_dict"]

print("Loading cached FLUX T5 configuration...")
config = T5Config.from_pretrained(
    "black-forest-labs/FLUX.1-schnell",
    subfolder="text_encoder_2",
    local_files_only=True,
)

print("\nT5 configuration:")
for key in (
    "model_type",
    "vocab_size",
    "d_model",
    "d_ff",
    "num_layers",
    "num_heads",
    "feed_forward_proj",
):
    print(f"{key}: {getattr(config, key, None)}")

print("\nCreating model structure on meta device...")
with torch.device("meta"):
    model = T5EncoderModel(config)

expected = set(model.state_dict().keys())
actual = set(weights.keys())

matched = expected & actual
missing = expected - actual
unexpected = actual - expected

print("\nCheckpoint compatibility:")
print("Expected model tensors:", len(expected))
print("Checkpoint tensors:", len(actual))
print("Matching tensors:", len(matched))
print("Missing tensors:", len(missing))
print("Unexpected tensors:", len(unexpected))

if missing:
    print("\nFirst missing keys:")
    for key in sorted(missing)[:20]:
        print(" ", key)

if unexpected:
    print("\nFirst unexpected keys:")
    for key in sorted(unexpected)[:20]:
        print(" ", key)

print("\nCompatibility inspection complete.")
