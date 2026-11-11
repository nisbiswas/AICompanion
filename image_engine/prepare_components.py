
import torch
from diffusers import FluxPipeline

MODEL_ID = "black-forest-labs/FLUX.1-schnell"

print("=" * 55)
print("HORNETAI - PREPARING FLUX COMPONENTS")
print("=" * 55)

print("\nLoading smaller FLUX components...")
print("Transformer: SKIPPED")
print("T5 text encoder: SKIPPED")

pipe = FluxPipeline.from_pretrained(
    MODEL_ID,
    transformer=None,
    text_encoder_2=None,
    torch_dtype=torch.bfloat16,
    low_cpu_mem_usage=True,
)

print("\nComponents loaded:")

for name in [
    "scheduler",
    "vae",
    "text_encoder",
    "tokenizer",
    "tokenizer_2",
    "transformer",
    "text_encoder_2",
]:
    component = getattr(pipe, name, None)
    print(f"{name}: {'Loaded' if component is not None else 'Skipped'}")

print("\nSmaller components downloaded and cached successfully.")

del pipe
print("\nPreparation complete.")
