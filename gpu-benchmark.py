#!/usr/bin/env python3
"""Short, stock-power CUDA stability and cooling check."""

import time

import torch


if not torch.cuda.is_available():
    raise SystemExit("CUDA is not available")

device = torch.device("cuda")
size = 8192
duration_seconds = 20

left = torch.randn((size, size), device=device, dtype=torch.bfloat16)
right = torch.randn((size, size), device=device, dtype=torch.bfloat16)
torch.cuda.synchronize()

started = time.perf_counter()
iterations = 0
while time.perf_counter() - started < duration_seconds:
    result = left @ right
    torch.cuda.synchronize()
    iterations += 1

elapsed = time.perf_counter() - started
operations = iterations * 2 * size**3

print(f"Completed {iterations} BF16 matrix multiplications in {elapsed:.1f} seconds")
print(f"Average throughput: {operations / elapsed / 1e12:.1f} TFLOP/s")
print(f"Peak PyTorch allocation: {torch.cuda.max_memory_allocated() / 2**30:.2f} GiB")
print(f"Checksum: {result[0, 0].item():.4f}")
