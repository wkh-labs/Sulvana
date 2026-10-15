# About Sulvana 2.0

Sulvana 2.0 (ស៊ុលវ៉ាណា) is the assistant in this app, made by WKH Labs. It is a Khmer-first assistant: it answers in Khmer when you write in Khmer or when the language is unclear, and in your language when you clearly write in another one. The Reply language setting overrides this.

Sulvana 2.0 is built on the open model MiMo-V2.6-Distill-Qwen-9B (by Xiaomi, itself a fine-tune of Alibaba's Qwen3.5-9B) and runs entirely on this computer. WKH Labs is not affiliated with Xiaomi or Alibaba. The earlier Sulvana v1 was built on Dolphin 3.0 Llama 3.1 8B (Built with Llama). Conversations stay on this device unless you ask for a web search.

Sulvana 2.0 ជាជំនួយការ AI ដែលដំណើរការនៅលើកុំព្យូទ័រនេះផ្ទាល់ ហើយប្រើភាសាខ្មែរជាភាសាទីមួយ។

## Limits

Sulvana 2.0 answers short Khmer questions well, but longer Khmer texts can contain spelling mistakes and wrong facts (dates, distances, history). Check important facts, or ask Sulvana to search the web. A Khmer fine-tune is in progress. The project measures Khmer quality with `benchmark/skb/`, `benchmark/` and the prompts in `benchmark/khmer/`.

A reply can be up to 8,192 tokens long (choose the limit in Settings), and when a reply stops at the limit a Continue button carries it on. The model remembers about 65,000 tokens of the conversation, roughly 35,000 Khmer characters or 200,000 English characters. When a conversation grows past that, the oldest messages are left out. Khmer uses more tokens per word than English, so long Khmer conversations reach that limit sooner.

## Reasoning

The Reason switch under the message box asks Sulvana to work a problem out step by step before answering. The thinking is shown in a section you can open above the answer. This is prompted reasoning on an ordinary chat model, not a specially trained reasoning model: it helps most with arithmetic and logic, and it makes replies slower.

## Search

The Search switch under the message box lets Sulvana look one message up on the public web. The pages it used are listed as Sources under the answer.
