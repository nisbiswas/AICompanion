
import torch
from diffusers import FluxTransformer2DModel

MODEL_PATH = r"C:\Users\admin\Downloads\flux1-schnell-fp8-e4m3fn.safetensors"

CONFIG_REPO = "black-forest-labs/FLUX.1-schnell"

print("PyTorch:", torch.__version__)
print("CUDA:", torch.cuda.is_available())
print("GPU:", torch.cuda.get_device_name(0))

print("\nLoading FLUX transformer...")

transformer = FluxTransformer2DModel.from_single_file(
    MODEL_PATH,
    config=CONFIG_REPO,
    subfolder="transformer",
    torch_dtype=torch.float8_e4m3fn,
)

print("\nTransformer loaded successfully!")
print("Parameter dtype:", next(transformer.parameters()).dtype)
print("Parameter device:", next(transformer.parameters()).device)

del transformer
torch.cuda.empty_cache()

print("\nInspection complete.")
