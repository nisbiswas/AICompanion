
import torch
import inspect

from optimum.quanto import qfloat8, quantize, freeze
from transformers import T5EncoderModel

print("PyTorch:", torch.__version__)
print("T5 class:", T5EncoderModel)

try:
    from transformers import QuantoConfig

    print("\nTransformers QuantoConfig: AVAILABLE")
    print("Signature:", inspect.signature(QuantoConfig))

    config = QuantoConfig(weights="float8")
    print("FP8 configuration:", config)

except Exception as e:
    print("\nTransformers QuantoConfig unavailable:")
    print(type(e).__name__, e)

print("\nTesting Quanto FP8 quantization on CPU...")

model = torch.nn.Sequential(
    torch.nn.Linear(1024, 1024),
    torch.nn.GELU(),
    torch.nn.Linear(1024, 512),
)

quantize(model, weights=qfloat8)
freeze(model)

x = torch.randn(1, 1024)
output = model(x)

print("Quantization successful!")
print("Output shape:", output.shape)
print("\nCompatibility test complete.")
