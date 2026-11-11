
import inspect
import torch

from transformers import T5EncoderModel, QuantoConfig

print("=" * 55)
print("HORNETAI - T5 LOADING API CHECK")
print("=" * 55)

print("\nT5 model class:")
print(T5EncoderModel)

print("\nfrom_pretrained signature:")
print(inspect.signature(T5EncoderModel.from_pretrained))

print("\nQuanto configuration:")
config = QuantoConfig(weights="float8")
print(config)

print("\nConfiguration dictionary:")
print(config.to_dict())

print("\nCUDA:")
print(torch.cuda.is_available())

if torch.cuda.is_available():
    print("GPU:", torch.cuda.get_device_name(0))

print("\nT5 loading API check complete.")
