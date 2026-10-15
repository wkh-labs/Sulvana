import time

import bitsandbytes as bnb
import torch


def gib(value: int) -> float:
    return value / 1024**3


print(f"PyTorch: {torch.__version__}")
print(f"PyTorch CUDA runtime: {torch.version.cuda}")
print(f"CUDA available: {torch.cuda.is_available()}")

if not torch.cuda.is_available():
    raise SystemExit("CUDA is not visible. Run this check from the host, not a restricted sandbox.")

device = torch.device("cuda:0")
properties = torch.cuda.get_device_properties(device)
free, total = torch.cuda.mem_get_info(device)
print(f"GPU: {properties.name}")
print(f"Compute capability: {properties.major}.{properties.minor}")
print(f"VRAM visible to PyTorch: {gib(total):.2f} GiB total, {gib(free):.2f} GiB free")
print(f"BF16 supported: {torch.cuda.is_bf16_supported()}")
print(f"bitsandbytes: {bnb.__version__}")

torch.backends.cuda.matmul.allow_tf32 = True
a = torch.randn((4096, 4096), device=device, dtype=torch.bfloat16)
b = torch.randn((4096, 4096), device=device, dtype=torch.bfloat16)

for _ in range(3):
    _ = a @ b
torch.cuda.synchronize()

started = time.perf_counter()
for _ in range(10):
    result = a @ b
torch.cuda.synchronize()
elapsed = time.perf_counter() - started

if not torch.isfinite(result).all():
    raise SystemExit("GPU produced non-finite values during the BF16 test.")

print(f"BF16 matrix test: passed ({elapsed / 10:.4f} seconds per 4096x4096 multiply)")
print(f"Peak PyTorch allocation: {gib(torch.cuda.max_memory_allocated()):.2f} GiB")

