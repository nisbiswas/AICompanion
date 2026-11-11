
import os
import gc
import types
from pathlib import Path

import torch
import torch.nn.functional as F

# Prevent Hugging Face downloads.
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

from transformers import AutoTokenizer, T5Config, T5EncoderModel
from diffusers import FluxPipeline, FluxTransformer2DModel


# --------------------------------------------------
# PATHS
# --------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent

MODEL_PATH = Path(
    r"C:\Users\admin\Downloads\flux1-schnell-fp8-e4m3fn.safetensors"
)

CHECKPOINT_PATH = (
    ROOT / "models" / "flux" /
    "FLUX.1-schnell-text_encoder_2-FP8.pt"
)

SNAPSHOT = (
    Path.home()
    / ".cache"
    / "huggingface"
    / "hub"
    / "models--black-forest-labs--FLUX.1-schnell"
    / "snapshots"
    / "741f7c3ce8b383c54771c7003378a50191e9efe9"
)

TOKENIZER_PATH = SNAPSHOT / "tokenizer_2"
CONFIG_PATH = SNAPSHOT / "text_encoder_2"

MODEL_ID = "black-forest-labs/FLUX.1-schnell"

OUTPUT_DIR = ROOT / "generated" / "images"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# --------------------------------------------------
# SETTINGS
# --------------------------------------------------


PROMPT = """
A breathtaking full-body portrait of an elegant female knight standing before the ruins of an ancient gothic castle beneath an enormous luminous full moon.

She has long, flowing silver-white hair, delicate facial features, pale blue eyes, and a calm yet commanding expression. Her presence conveys quiet authority, nobility, and unwavering determination.

She wears exquisite pearl-white and polished silver full-body plate armor, completely covering her torso, arms, and legs, with only her face exposed. The armor is beautifully crafted, with intricate golden filigree, delicate ornamental engravings, subtle decorative patterns, and finely detailed overlapping plates. Its polished metallic surfaces reflect the cold moonlight, creating realistic silver highlights and soft pearlescent reflections. The armor is elegant and feminine in silhouette without compromising its protective design.

A long, pristine white cape flows gracefully behind her, moving gently in the cold night wind. In one hand, she holds an elegant longsword with an ornate golden crossguard and a brilliant white-silver blade that catches the moonlight.

The ruined gothic castle rises behind her, its shattered towers and ancient architecture silhouetted against the enormous full moon. Wisps of mist drift across the broken stone courtyard. Faint moonbeams pierce through the clouds, illuminating the knight while leaving the surrounding ruins in deep shadow.

Dark fantasy atmosphere, gothic medieval architecture, cinematic composition, dramatic moonlight, atmospheric fog, intricate craftsmanship, realistic metal textures, natural human anatomy, detailed facial features, beautiful flowing hair, sophisticated lighting, high visual fidelity, masterful fantasy illustration.
"""

WIDTH = 640
HEIGHT = 832
STEPS = 4
SEED = 42
MAX_SEQUENCE_LENGTH = 512

DEVICE = "cuda"


# --------------------------------------------------
# GPU CHECK
# --------------------------------------------------

if not torch.cuda.is_available():
    raise RuntimeError("CUDA GPU is not available.")

if not MODEL_PATH.exists():
    raise FileNotFoundError(MODEL_PATH)

if not CHECKPOINT_PATH.exists():
    raise FileNotFoundError(CHECKPOINT_PATH)

if not TOKENIZER_PATH.exists():
    raise FileNotFoundError(TOKENIZER_PATH)

if not CONFIG_PATH.exists():
    raise FileNotFoundError(CONFIG_PATH)

print("GPU:", torch.cuda.get_device_name(0))


def show_gpu_memory(label):
    torch.cuda.synchronize()

    allocated = torch.cuda.memory_allocated() / (1024 ** 3)
    reserved = torch.cuda.memory_reserved() / (1024 ** 3)
    free, total = torch.cuda.mem_get_info()

    print(f"\n{label}")
    print(f"Allocated: {allocated:.2f} GiB")
    print(f"Reserved:  {reserved:.2f} GiB")
    print(f"Free:      {free / (1024 ** 3):.2f} GiB")
    print(f"Total:     {total / (1024 ** 3):.2f} GiB")


# --------------------------------------------------
# FP8 LINEAR COMPATIBILITY
# --------------------------------------------------

def fp8_linear_forward(self, inputs):
    dtype = inputs.dtype

    weight = self.weight

    if weight.dtype == torch.float8_e4m3fn:
        weight = weight.to(dtype=dtype)

    bias = self.bias

    if bias is not None and bias.dtype != dtype:
        bias = bias.to(dtype=dtype)

    return F.linear(inputs, weight, bias)


def enable_fp8_linear_inference(model):
    patched = 0
    converted_norms = 0

    for module in model.modules():

        if (
            isinstance(module, torch.nn.Linear)
            and module.weight.dtype == torch.float8_e4m3fn
        ):
            module.forward = types.MethodType(
                fp8_linear_forward,
                module,
            )
            patched += 1

        elif isinstance(
            module,
            (torch.nn.RMSNorm, torch.nn.LayerNorm),
        ):
            module.to(dtype=torch.bfloat16)
            converted_norms += 1

    print("FP8 Linear layers patched:", patched)
    print("Normalization layers converted:", converted_norms)


# --------------------------------------------------
# STEP 1: LOAD T5 AND GENERATE REAL EMBEDDINGS
# --------------------------------------------------

print("\n====================================")
print("STEP 1: T5 PROMPT ENCODING")
print("====================================")

print("Loading T5 tokenizer...")

tokenizer_2 = AutoTokenizer.from_pretrained(
    str(TOKENIZER_PATH),
    local_files_only=True,
    use_fast=True,
)

print("Loading T5 checkpoint...")

checkpoint = torch.load(
    CHECKPOINT_PATH,
    map_location="cpu",
    weights_only=True,
    mmap=True,
)

state_dict = checkpoint["state_dict"]

config = T5Config.from_pretrained(
    str(CONFIG_PATH),
    local_files_only=True,
)

print("Creating T5 model structure...")

with torch.device("meta"):
    t5 = T5EncoderModel(config)

print("Assigning FP8/BF16 checkpoint...")

t5.load_state_dict(
    state_dict,
    strict=True,
    assign=True,
)

del checkpoint, state_dict
gc.collect()

enable_fp8_linear_inference(t5)

print("Moving T5 to GPU...")

t5 = t5.to(DEVICE)
t5.eval()

show_gpu_memory("T5 loaded")


print("Tokenizing prompt...")

t5_tokens = tokenizer_2(
    PROMPT,
    padding="max_length",
    max_length=MAX_SEQUENCE_LENGTH,
    truncation=True,
    return_tensors="pt",
)

input_ids = t5_tokens.input_ids.to(DEVICE)

print("Running T5 inference...")

attention_mask = t5_tokens.attention_mask.to(DEVICE)

with torch.inference_mode():
    t5_output = t5(
        input_ids=input_ids,
        attention_mask=attention_mask,
    )

    prompt_embeds = t5_output.last_hidden_state.contiguous()


print("T5 embeddings:", tuple(prompt_embeds.shape))
print("T5 dtype:", prompt_embeds.dtype)
print("T5 finite:", torch.isfinite(prompt_embeds).all().item())

if not torch.isfinite(prompt_embeds).all():
    raise RuntimeError("T5 generated invalid embeddings.")

# Preserve embeddings on CPU.
prompt_embeds = prompt_embeds.to("cpu")

del t5_output, t5_tokens, input_ids, t5
gc.collect()

torch.cuda.empty_cache()
torch.cuda.synchronize()

show_gpu_memory("After releasing T5")


# --------------------------------------------------
# STEP 2: LOAD CACHED FLUX COMPONENTS
# --------------------------------------------------

print("\n====================================")
print("STEP 2: LOAD FLUX COMPONENTS")
print("====================================")

pipe = FluxPipeline.from_pretrained(
    MODEL_ID,
    transformer=None,
    text_encoder_2=None,
    torch_dtype=torch.bfloat16,
    local_files_only=True,
    low_cpu_mem_usage=True,
)

print("VAE:", pipe.vae is not None)
print("CLIP:", pipe.text_encoder is not None)
print("T5:", pipe.text_encoder_2)


# --------------------------------------------------
# STEP 3: LOAD EXISTING FP8 TRANSFORMER
# --------------------------------------------------

print("\n====================================")
print("STEP 3: LOAD FP8 TRANSFORMER")
print("====================================")

transformer = FluxTransformer2DModel.from_single_file(
    str(MODEL_PATH),
    config=MODEL_ID,
    subfolder="transformer",
    torch_dtype=torch.float8_e4m3fn,
    local_files_only=True,
)

enable_fp8_linear_inference(transformer)

pipe.transformer = transformer

print("Transformer dtype:", next(transformer.parameters()).dtype)


# --------------------------------------------------
# STEP 4: MOVE FLUX TO GPU
# --------------------------------------------------

print("\nMoving FLUX pipeline to GPU...")

pipe.to(DEVICE)

show_gpu_memory("FLUX pipeline loaded")


# --------------------------------------------------
# STEP 5: CLIP PROMPT EMBEDDING
# --------------------------------------------------

print("\nEncoding prompt with CLIP-L...")

clip_tokens = pipe.tokenizer(
    PROMPT,
    padding="max_length",
    max_length=77,
    truncation=True,
    return_tensors="pt",
)

clip_input_ids = clip_tokens.input_ids.to(DEVICE)
clip_attention_mask = clip_tokens.attention_mask.to(DEVICE)

with torch.inference_mode():
    clip_output = pipe.text_encoder(
        clip_input_ids,
        attention_mask=clip_attention_mask,
    )

    pooled = clip_output.pooler_output

    if pooled is None:
        raise RuntimeError("CLIP pooler_output is missing.")

    pooled = pooled.to(
        device=DEVICE,
        dtype=torch.bfloat16,
    )

print("CLIP pooled shape:", tuple(pooled.shape))
print("CLIP dtype:", pooled.dtype)

del clip_output, clip_tokens, clip_input_ids, clip_attention_mask


# --------------------------------------------------
# STEP 6: TRANSFER T5 EMBEDDINGS TO GPU
# --------------------------------------------------

print("\nTransferring T5 embeddings to GPU...")

prompt_embeds = prompt_embeds.to(
    device=DEVICE,
    dtype=torch.bfloat16,
)

print("T5 embeddings:", tuple(prompt_embeds.shape))
print("CLIP embeddings:", tuple(pooled.shape))

show_gpu_memory("Before generation")


# --------------------------------------------------
# STEP 7: GENERATE
# --------------------------------------------------

print("\n====================================")
print("STEP 7: IMAGE GENERATION")
print("====================================")

generator = torch.Generator(
    device=DEVICE
).manual_seed(SEED)

with torch.inference_mode():
    result = pipe(
        prompt=None,
        prompt_embeds=prompt_embeds,
        pooled_prompt_embeds=pooled,
        height=WIDTH,
        width=HEIGHT,
        num_inference_steps=STEPS,
        guidance_scale=0.0,
        max_sequence_length=MAX_SEQUENCE_LENGTH,
        generator=generator,
        output_type="pil",
    )

show_gpu_memory("After generation")


# --------------------------------------------------
# STEP 8: SAVE
# --------------------------------------------------

output_file = OUTPUT_DIR / "flux_real_t5_test.png"

result.images[0].save(output_file)

print("\n====================================")
print("IMAGE GENERATED SUCCESSFULLY")
print(output_file)
print("====================================")