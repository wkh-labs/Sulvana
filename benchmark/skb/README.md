# Sulvana Khmer Benchmark (SKB)

A harder, Khmer-first companion to the Khmer Bilingual AI Benchmark in the folder above.
147 original items (CC0); nothing is scraped. Unlike the older benchmark, an answer to a
Khmer question only counts if it is **written in Khmer**, and text copied from the question
earns no credit.

| Section | Items | What it tests |
|---|---:|---|
| reading | 20 | Khmer passages, answered in Khmer, some needing a small calculation |
| math | 21 | Word problems in Khmer (Khmer digits accepted) |
| knowledge | 20 | Cambodia and general knowledge, asked and answered in Khmer |
| translate_to_khmer | 15 | English sentences; scored by the key words any correct translation contains |
| translate_to_english | 10 | Khmer sentences; same idea in reverse |
| instructions | 15 | Rules checked mechanically: number of sentences, numbered lists, one-word answers, no Latin letters |
| reasoning | 8 | Short logic problems in Khmer |
| english | 8 | English control questions |
| basics | 30 | Single words both ways, simple sums, yes/no facts |

Run it (stop Sulvana first; it needs the GPU):

```bash
python3 benchmark/run_benchmark.py --suite skb --label dolphin-base
python3 benchmark/run_benchmark.py --suite skb --label my-adapter --lora runs/finetune/<run>/<adapter>.gguf
```

Results and every answer with the reason it failed: `runs/benchmark/skb-<label>/report.json`.

Edit items in `build.py` and run it to regenerate `questions.jsonl`, `answer_key.private.jsonl`
and `manifest.json`; bump `VERSION` whenever an item changes, and never put the answer key in
training data.

Scores on 2026-10-14 (greedy decoding, no tools): Dolphin 3.0 8B 12.2%, with the
`khmer-quick-01` adapter 32.0%.
