# Sulvana: credits and licences

Sulvana is a non-commercial project by **WKH Labs** (Wisdom · Khmer · Heritage).

## Models

- **Sulvana 2.0 9B** is built on [XiaomiMiMo/MiMo-V2.6-Distill-Qwen-9B](https://huggingface.co/XiaomiMiMo/MiMo-V2.6-Distill-Qwen-9B)
  (MIT licence, Copyright Xiaomi), which is a fine-tune of [Qwen/Qwen3.5-9B](https://huggingface.co/Qwen/Qwen3.5-9B)
  (Apache License 2.0, Copyright Alibaba Cloud). WKH Labs modified these models by LoRA fine-tuning for Khmer.
  WKH Labs is not affiliated with or endorsed by Xiaomi or Alibaba.
- **Sulvana v1** was built on [Dolphin 3.0 Llama 3.1 8B](https://huggingface.co/dphn/Dolphin3.0-Llama3.1-8B), based on
  Meta's Llama 3.1 8B, licensed under the Llama 3.1 Community License. Built with Llama.
- Image understanding uses Qwen2.5-VL-3B-Instruct (Apache 2.0); image generation uses Z-Image Turbo (see `Z-Image-Turbo.md`).

The licence texts of the base models are distributed with their weights on Hugging Face and must accompany any copy of
the models or of models derived from them.

## Online services

- **Better Khmer** (off unless the user turns it on) sends Khmer messages and replies to Google Translate's public web
  endpoint (translate.googleapis.com). This is not an official, documented API for apps; Google may limit or change it.
- **Web search** (only when asked) sends the search query to DuckDuckGo.

## Training data for the Khmer fine-tune

- [ALT, the Asian Language Treebank](https://huggingface.co/datasets/mutiyama/alt) (CC BY 4.0): English–Khmer sentence pairs.
- [saillab/alpaca-khmer-cleaned](https://huggingface.co/datasets/saillab/alpaca-khmer-cleaned): a machine translation of
  Stanford Alpaca, whose data is licensed CC BY-NC 4.0 (non-commercial). Adapters trained on it are for non-commercial use.
- Khmer examples generated with Google Gemini (`datasets/khmer-gemini/`, `datasets/khmer-cloud/`): synthetic data, used for
  non-commercial fine-tuning only. Google's Gemini API terms restrict using outputs to develop competing models; WKH Labs
  chose to use it for this non-commercial project.
