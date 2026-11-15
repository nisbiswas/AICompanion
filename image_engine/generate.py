"""One image per process. Read a JSON request on stdin; exit releases all GPU state."""
import gc
import json
import os
from pathlib import Path
import secrets
import sys
import types
import time


def report(request, stage):
    if request.get("progress_path"):
        path = Path(request["progress_path"])
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps({"stage": stage}), encoding="utf-8")
        temporary.replace(path)

os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"


def generate(request):
    started = time.monotonic()
    import torch
    import torch.nn.functional as F
    from diffusers import FluxPipeline, FluxTransformer2DModel
    from huggingface_hub import hf_hub_download
    from transformers import AutoTokenizer, T5Config, T5EncoderModel

    root = Path(__file__).resolve().parents[1]
    model_id = "black-forest-labs/FLUX.1-schnell"
    transformer_path = Path(os.getenv(
        "FLUX_TRANSFORMER_PATH",
        str(Path.home() / "Downloads/flux1-schnell-fp8-e4m3fn.safetensors"),
    ))
    t5_path = Path(os.getenv(
        "FLUX_T5_PATH", str(root / "models/flux/FLUX.1-schnell-text_encoder_2-FP8.pt")
    ))
    for path in (transformer_path, t5_path):
        if not path.is_file():
            raise FileNotFoundError(f"Model not found: {path}. Configure FLUX_TRANSFORMER_PATH / FLUX_T5_PATH.")
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA GPU is unavailable in the image engine environment.")
    # The cache intentionally omits full-precision transformer/T5 weights.
    # Resolve one cached config instead of requiring a complete HF snapshot.
    snapshot = Path(hf_hub_download(
        model_id, "text_encoder_2/config.json", local_files_only=True,
    )).parent.parent
    prompt = str(request["prompt"]).strip()
    if not prompt:
        raise ValueError("Image prompt is empty.")
    width = int(request.get("width", 1024))
    height = int(request.get("height", 1024))
    if any(d < 256 or d > 1536 or d % 16 for d in (width, height)):
        raise ValueError("Image dimensions must be multiples of 16 between 256 and 1536.")
    device = "cuda"
    seed = int(request.get("seed", secrets.randbelow(2**32)))
    warnings = []
    report(request, "encoding")

    # Retain the FP8 compatibility approach validated in generate_test.py.
    def fp8_forward(layer, inputs):
        weight = layer.weight.to(dtype=inputs.dtype)
        bias = layer.bias
        if bias is not None:
            bias = bias.to(dtype=inputs.dtype)
        return F.linear(inputs, weight, bias)

    def patch_fp8(model):
        for module in model.modules():
            if isinstance(module, torch.nn.Linear) and module.weight.dtype == torch.float8_e4m3fn:
                module.forward = types.MethodType(fp8_forward, module)
            elif isinstance(module, (torch.nn.RMSNorm, torch.nn.LayerNorm)):
                module.to(dtype=torch.bfloat16)

    # Encode with real T5, then release it before loading FLUX.
    tokenizer = AutoTokenizer.from_pretrained(
        str(snapshot / "tokenizer_2"), local_files_only=True, use_fast=True,
    )
    config = T5Config.from_pretrained(str(snapshot / "text_encoder_2"), local_files_only=True)
    checkpoint = torch.load(t5_path, map_location="cpu", weights_only=True, mmap=True)
    with torch.device("meta"):
        t5 = T5EncoderModel(config)
    t5.load_state_dict(checkpoint["state_dict"], strict=True, assign=True)
    del checkpoint
    patch_fp8(t5)
    t5 = t5.to(device).eval()
    token_count = len(tokenizer(prompt).input_ids)
    if token_count > 256:
        raise ValueError(f"The compiled prompt has {token_count} T5 tokens; Schnell supports 256. Shorten the brief instead of silently dropping details.")
    tokens = tokenizer(prompt, padding="max_length", max_length=256,
                       truncation=True, return_tensors="pt")
    with torch.inference_mode():
        # Match FluxPipeline._get_t5_prompt_embeds: padding is not masked.
        encoded = t5(tokens.input_ids.to(device), output_hidden_states=False)
        embeddings = encoded.last_hidden_state.contiguous().cpu()
    if not torch.isfinite(embeddings).all():
        raise RuntimeError("T5 generated invalid embeddings.")
    del encoded, tokens, t5, tokenizer
    gc.collect()
    torch.cuda.empty_cache()
    report(request, "loading_flux")

    pipe = FluxPipeline.from_pretrained(
        str(snapshot), transformer=None, text_encoder_2=None,
        torch_dtype=torch.bfloat16, local_files_only=True, low_cpu_mem_usage=True,
    )
    transformer = FluxTransformer2DModel.from_single_file(
        str(transformer_path), config=str(snapshot), subfolder="transformer",
        torch_dtype=torch.float8_e4m3fn, local_files_only=True,
    )
    patch_fp8(transformer)
    pipe.transformer = transformer
    # Accelerate moves CLIP, transformer and VAE to the GPU in sequence.
    # Avoid keeping every component resident during 1MP generation on 16GB cards.
    pipe.enable_model_cpu_offload()
    pipe.vae.enable_slicing()
    pipe.vae.enable_tiling()
    clip_prompt = str(request.get("clip_prompt", prompt))
    if len(pipe.tokenizer(clip_prompt).input_ids) > 77:
        warnings.append("CLIP prompt exceeded 77 tokens; use a shorter global description.")
    clip_tokens = pipe.tokenizer(clip_prompt, padding="max_length", max_length=77,
                                 truncation=True, return_tensors="pt")
    with torch.inference_mode():
        # Match FluxPipeline._get_clip_prompt_embeds: no attention mask.
        clip = pipe.text_encoder(clip_tokens.input_ids.to(device), output_hidden_states=False)
        pooled = clip.pooler_output.to(device=device, dtype=torch.bfloat16)
        report(request, "rendering")

        def on_step(pipeline, step, timestep, callback_kwargs):
            report(request, f"step_{step + 1}")
            return callback_kwargs

        result = pipe(
            prompt=None,
            prompt_embeds=embeddings.to(device=device, dtype=torch.bfloat16),
            pooled_prompt_embeds=pooled,
            width=width, height=height, num_inference_steps=4,
            guidance_scale=0.0, max_sequence_length=256,
            generator=torch.Generator(device=device).manual_seed(seed),
            callback_on_step_end=on_step,
            output_type="pil",
        )
    output = Path(request["output"])
    output.parent.mkdir(parents=True, exist_ok=True)
    metadata = {
        "engine_version": 2, "model": model_id,
        "original_prompt": request.get("original_prompt", prompt),
        "prompt": prompt, "clip_prompt": clip_prompt,
        "planning_note": request.get("planning_note", ""),
        "width": width, "height": height, "seed": seed, "steps": 4,
        "guidance_scale": 0.0, "max_sequence_length": 256,
        "t5_tokens": token_count, "warnings": warnings,
        "elapsed_seconds": round(time.monotonic() - started, 2),
        "peak_vram_gib": round(torch.cuda.max_memory_allocated() / 1024**3, 2),
    }
    report(request, "saving")
    from PIL.PngImagePlugin import PngInfo
    png_info = PngInfo()
    png_info.add_text("hornet", json.dumps(metadata, ensure_ascii=False))
    result.images[0].save(output, format="PNG", pnginfo=png_info)
    output.with_suffix(".json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    pipe.maybe_free_model_hooks()
    print(json.dumps({"image_path": str(output)}))


if __name__ == "__main__":
    generate(json.load(sys.stdin))
