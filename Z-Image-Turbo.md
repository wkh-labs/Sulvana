# Z-Image Turbo on this laptop

This setup is separate from the Qwen chat app. It uses the quantized Z-Image-Turbo
image model, a Qwen3-4B text encoder, and the original Z-Image VAE. The runner is
the Vulkan build of stable-diffusion.cpp and targets the RTX 5070 Laptop GPU.

## Start

Open `z-image-gui.sh` to type a prompt and generate an image. Images and logs are
saved under `runs/z-image/`.

From a terminal, you can also run:

```bash
./z-image.sh "A watercolor painting of Angkor Wat at sunrise"
```

The default is 768 × 768. For a larger image:

```bash
Z_WIDTH=1024 Z_HEIGHT=1024 ./z-image.sh "A watercolor painting of Angkor Wat at sunrise"
```

Generation may be slower when other GPU apps, including Qwen chat, are open.
Close them first if you run out of GPU memory. The text encoder and VAE run on
the CPU; image-model weights are offloaded through system RAM to fit 8 GB VRAM.

## Sources

- Z-Image Turbo Q4_K_M: https://huggingface.co/unsloth/Z-Image-Turbo-GGUF
- Qwen3-4B-Instruct-2507 Q4_K_M: https://huggingface.co/unsloth/Qwen3-4B-Instruct-2507-GGUF
- Z-Image Turbo VAE: https://huggingface.co/Tongyi-MAI/Z-Image-Turbo
- stable-diffusion.cpp: https://github.com/leejet/stable-diffusion.cpp
