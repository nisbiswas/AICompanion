
import os
import shutil
import ctypes
import torch
import diffusers
import transformers
import huggingface_hub

from diffusers import FluxPipeline

MODEL_PATH = r"C:\Users\admin\Downloads\flux1-schnell-fp8-e4m3fn.safetensors"

print("=" * 55)
print("HORNETAI - FLUX ENVIRONMENT CHECK")
print("=" * 55)

print("\n[1] Python packages")
print("PyTorch:", torch.__version__)
print("Diffusers:", diffusers.__version__)
print("Transformers:", transformers.__version__)
print("Hugging Face Hub:", huggingface_hub.__version__)

print("\n[2] GPU")
print("CUDA available:", torch.cuda.is_available())

if torch.cuda.is_available():
    print("GPU:", torch.cuda.get_device_name(0))
    print("VRAM:", round(
        torch.cuda.get_device_properties(0).total_memory / 1024**3, 2
    ), "GB")

print("\n[3] Existing FLUX checkpoint")
print("Exists:", os.path.isfile(MODEL_PATH))

if os.path.isfile(MODEL_PATH):
    print("Size:", round(os.path.getsize(MODEL_PATH) / 1024**3, 2), "GB")

print("\n[4] System memory")

class MEMORYSTATUS(ctypes.Structure):
    _fields_ = [
        ("dwLength", ctypes.c_ulong),
        ("dwMemoryLoad", ctypes.c_ulong),
        ("ullTotalPhys", ctypes.c_ulonglong),
        ("ullAvailPhys", ctypes.c_ulonglong),
        ("ullTotalPageFile", ctypes.c_ulonglong),
        ("ullAvailPageFile", ctypes.c_ulonglong),
        ("ullTotalVirtual", ctypes.c_ulonglong),
        ("ullAvailVirtual", ctypes.c_ulonglong),
        ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
    ]

mem = MEMORYSTATUS()
mem.dwLength = ctypes.sizeof(MEMORYSTATUS)
ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(mem))

print("Total RAM:", round(mem.ullTotalPhys / 1024**3, 2), "GB")
print("Available RAM:", round(mem.ullAvailPhys / 1024**3, 2), "GB")

print("\n[5] Disk space")
disk = shutil.disk_usage("C:\\")
print("Free C: drive:", round(disk.free / 1024**3, 2), "GB")

print("\n[6] FLUX pipeline API")
import inspect
print("FluxPipeline:", inspect.signature(FluxPipeline.__init__))

print("\n[7] Hugging Face cache")
print("Cache:", huggingface_hub.constants.HF_HUB_CACHE)

print("\nEnvironment check complete.")
