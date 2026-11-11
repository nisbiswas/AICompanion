
import torch
import gc
from transformers import T5EncoderModel, QuantoConfig

MODEL_ID = "black-forest-labs/FLUX.1-schnell"

print("=" * 55)
print("HORNETAI - LOADING T5-XXL WITH FP8")
print("=" * 55)

print("\nGPU:", torch.cuda.get_device_name(0))
print("CUDA:", torch.cuda.is_available())

# Quantize T5 weights to FP8 during loading.
quant_config = QuantoConfig(weights="float8")

print("\nLoading T5-XXL...")
print("Quantization: Quanto FP8")
print("Initial loading device: CPU")

text_encoder_2 = T5EncoderModel.from_pretrained(
    MODEL_ID,
    subfolder="text_encoder_2",
    quantization_config=quant_config,
    dtype=torch.bfloat16,
    use_safetensors=True,
    low_cpu_mem_usage=True,
)

print("\nT5 loaded successfully!")

print("Model:", type(text_encoder_2).__name__)
print("First parameter device:", next(text_encoder_2.parameters()).device)
print("Quantization config:", text_encoder_2.config.model_type)

print("\nT5 FP8 loading test completed.")

# Release memory after verifying the load.
del text_encoder_2
gc.collect()
torch.cuda.empty_cache()

print("Test model released.")
