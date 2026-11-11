from pathlib import Path
SNAPSHOT = (
    Path.home()
    / ".cache"
    / "huggingface"
    / "hub"
    / "models--black-forest-labs--FLUX.1-schnell"
    / "snapshots"
    / "741f7c3ce8b383c54771c7003378a50191e9efe9"
)

T5_TOKENIZER = SNAPSHOT / "tokenizer_2"
T5_CONFIG = SNAPSHOT / "text_encoder_2"

import os
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

import gc
from pathlib import Path

import torch
import torch.nn.functional as F
from transformers import AutoTokenizer, T5Config, T5EncoderModel


ROOT = Path(__file__).resolve().parent.parent

CHECKPOINT = (
    ROOT / "models" / "flux" /
    "FLUX.1-schnell-text_encoder_2-FP8.pt"
)

MODEL_ID = "black-forest-labs/FLUX.1-schnell"
DEVICE = "cuda"

PROMPT = (
    "A beautiful female white knight standing majestically in the ruins of an ancient gothic castle, wearing intricate silver-white plate armor with delicate golden engravings, long flowing silver-white hair, pale luminous skin, piercing icy blue eyes, holding an elegant longsword with a glowing blade, a pristine white cape flowing dramatically in the wind, ethereal moonlight illuminating her armor, subtle magical particles floating in the air, dark fantasy atmosphere, breathtaking detailed character design, cinematic composition, dramatic lighting, highly detailed medieval armor, masterpiece fantasy concept art"
)


def fp8_linear_forward(self, input):
    weight = self.weight
    bias = self.bias

    if weight.dtype == torch.float8_e4m3fn:
        weight = weight.to(dtype=input.dtype)

    if bias is not None and bias.dtype != input.dtype:
        bias = bias.to(dtype=input.dtype)

    return F.linear(input, weight, bias)


def main():
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is unavailable")

    if not CHECKPOINT.exists():
        raise FileNotFoundError(CHECKPOINT)

    print("GPU:", torch.cuda.get_device_name(0))
    print("Loading tokenizer...")

    tokenizer = AutoTokenizer.from_pretrained(
        str(T5_TOKENIZER),
        local_files_only=True,
        use_fast=True,
    )

    print("Loading checkpoint...")
    checkpoint = torch.load(
        CHECKPOINT,
        map_location="cpu",
        weights_only=True,
        mmap=True,
    )

    state_dict = checkpoint["state_dict"]

    print("Loading T5 configuration...")
    config = T5Config.from_pretrained(
        str(T5_CONFIG),
        local_files_only=True,
    )

    print("Creating T5 structure on meta device...")
    with torch.device("meta"):
        model = T5EncoderModel(config)

    print("Assigning checkpoint tensors...")
    result = model.load_state_dict(
        state_dict,
        strict=True,
        assign=True,
    )

    print("Checkpoint assignment:", result)

    del checkpoint, state_dict
    gc.collect()

    # Patch only this process's Linear implementation.
    torch.nn.Linear.forward = fp8_linear_forward

    print("Moving T5 to GPU...")
    model = model.to(device=DEVICE)
    model.eval()

    print(
        "GPU allocated after loading:",
        round(torch.cuda.memory_allocated() / (1024 ** 3), 2),
        "GiB",
    )

    print("Tokenizing prompt...")
    tokens = tokenizer(
        PROMPT,
        padding="max_length",
        max_length=512,
        truncation=True,
        return_tensors="pt",
    )

    input_ids = tokens.input_ids.to(DEVICE)
    attention_mask = tokens.attention_mask.to(DEVICE)

    print("Running T5 inference...")

    with torch.inference_mode():
        output = model(
            input_ids=input_ids,
            attention_mask=attention_mask,
        )

    embeddings = output.last_hidden_state

    print("\nT5 inference successful")
    print("Embedding shape:", tuple(embeddings.shape))
    print("Embedding dtype:", embeddings.dtype)
    print("All finite:", torch.isfinite(embeddings).all().item())
    print(
        "Embedding memory:",
        round(embeddings.numel() * embeddings.element_size() / (1024 ** 2), 2),
        "MiB",
    )
    print(
        "GPU allocated after inference:",
        round(torch.cuda.memory_allocated() / (1024 ** 3), 2),
        "GiB",
    )

    if embeddings.shape != (1, 512, 4096):
        raise RuntimeError("Unexpected T5 embedding dimensions")

    if not torch.isfinite(embeddings).all():
        raise RuntimeError("T5 produced NaN or infinite values")

    print("\nT5 test completed successfully.")


if __name__ == "__main__":
    main()
