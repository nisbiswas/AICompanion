
from pathlib import Path
from collections import Counter
import torch

ROOT = Path(__file__).resolve().parent.parent
MODEL_PATH = ROOT / "models" / "flux" / "FLUX.1-schnell-text_encoder_2-FP8.pt"

if not MODEL_PATH.exists():
    raise FileNotFoundError(MODEL_PATH)

print("Checkpoint:", MODEL_PATH)
print(f"Size: {MODEL_PATH.stat().st_size / (1024**3):.2f} GiB")

checkpoint = torch.load(
    MODEL_PATH,
    map_location="cpu",
    weights_only=True,
    mmap=True,
)

print("\nTop-level type:", type(checkpoint).__name__)

if isinstance(checkpoint, dict):
    print("Top-level keys:", list(checkpoint.keys())[:30])


def collect_tensors(obj, prefix=""):
    result = {}

    if isinstance(obj, dict):
        for key, value in obj.items():
            name = f"{prefix}.{key}" if prefix else str(key)
            result.update(collect_tensors(value, name))

    elif isinstance(obj, torch.Tensor):
        result[prefix] = obj

    return result


tensors = collect_tensors(checkpoint)

print("\nTotal tensors:", len(tensors))

dtype_counts = Counter(str(t.dtype) for t in tensors.values())

print("\nDtype distribution:")
for dtype, count in dtype_counts.items():
    print(f"{dtype}: {count}")

print("\nFirst 30 tensors:")
for index, (name, tensor) in enumerate(tensors.items()):
    if index >= 30:
        break

    print(f"{name}: shape={tuple(tensor.shape)}, dtype={tensor.dtype}")

print("\nLast 10 tensor names:")
for name in list(tensors.keys())[-10:]:
    print(name)

print("\nInspection complete.")
