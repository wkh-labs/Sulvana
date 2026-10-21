# Sulvana local tools

Sulvana has three optional tools. They are deliberately narrow: the assistant can look things up and inspect the project without gaining control of the computer.

Explicit `/terminal`, `/docs`, and `/search` commands show the tool output directly. Ordinary questions may use the same tools as reference data for Sulvana's answer.

## Documentation search

`docs.search` searches Markdown files inside Sulvana's `knowledge/` folder and the project documentation. It returns matching passages with file names and line numbers. It cannot read files outside the workspace, private browser data, passwords, or hidden operating-system folders.

Use it for questions about Sulvana, the installed models, local image generation, vision, or the agent's own limits.

## Web search

`web.search` looks up a short public query on the web and returns a compact list of titles, links, and snippets (up to eight results). Sulvana does not upload local files or attach chat history. Only the search query leaves the computer; Sulvana does not open or read the result pages.

With Settings → **Search when unsure** on (the default), Sulvana first asks itself, in one short request, whether it really knows the answer. If the question is about a specific fact, definition, name, place, number or recent event it is not sure of, or contains a word it does not recognise, it searches before answering (status "Checking…", then "Searching the web…"). It does not search for maths, code, writing, small talk, coding mode, or questions the notes already cover. Only the short search query leaves the computer. If DuckDuckGo refuses, Wikipedia's search is used.

Otherwise the tool only runs when the user explicitly asks for it, in one of three ways: turning on the **Search** switch under the message box for that one message (it switches itself off again after sending), asking in words to search or look something up online in English or Khmer (for example "search the web for…" or "ស្វែងរកតាមអ៊ីនធឺណិត…"), or the `/search` command. The words that only instruct Sulvana to search are removed from the query, so the search engine receives the subject rather than the whole sentence.

The results Sulvana used are listed under its answer as **Sources**. Clicking a source opens that page in the user's own web browser; Sulvana itself never opens links.

## Khmer tools (translation behind the scenes)

Sulvana's own written Khmer has mistakes, so for Khmer conversations it can work in English and have its answer translated. Settings → Khmer tools (ឧបករណ៍ភាសាខ្មែរ) has three choices. The app calls this "Khmer tools" and does not use the word "translate" for it:

- **This computer** (default): Hy-MT2 1.8B, Tencent's translation model, runs on the CPU (`models/hy-mt2-1.8b`, 1.9 GB, started by Sulvana next to the chat model). It translates the user's Khmer question into English, Sulvana answers in English, and Hy-MT2 writes the Khmer a paragraph at a time while the answer is written. School and technical terms come from `knowledge/khmer-english-glossary.md`. Nothing leaves the computer. If Hy-MT2 is not available, the chat model rewrites its own answer in Khmer instead (slower and less accurate: in a blind comparison Hy-MT2 won 17 of 19 answers). Replies are marked "Khmer tools".
- **Google**: Google Translate's public web endpoint translates both ways. Most accurate, but the Khmer messages and replies are sent to Google, so the app asks once on the home screen before using it. Replies are marked "via Google Translate" and the header shows "Google Translate on". If Google refuses requests (HTTP 429) it is left alone for 10 minutes and the local translator takes over.
- **Off**: Sulvana writes the Khmer itself.

Code blocks are never translated. Questions about Khmer itself (grammar, spelling, word meanings) can be answered less well through English. `/translate <text>` translates one piece of text (with Google only if the user chose Google). `SULVANA_TRANSLATE=0` disables translation for everyone.

## Read aloud

Under a Khmer answer, **Listen** (ស្តាប់) reads it aloud with a Khmer voice that runs on this computer (`sulvana_speech.py`, Meta's MMS text-to-speech, `models/mms-tts-khm`, 145 MB). Numbers are read as Khmer words; code, links and English words are skipped. Nothing is sent online.

A friend using the shared link (share.sh) can chat, but terminal checks and coding mode are only available on the computer running Sulvana.

## Read-only terminal

`terminal.read` runs a small set of inspection commands in the Sulvana workspace. Allowed commands are:

- `pwd`, `ls`, `rg --files`, `rg <term>` in project Markdown guides, `git status`, `git diff --stat`
- `python --version`, `node --version`, `nvidia-smi`
- `df -h .`, `du -sh <workspace-relative-folder>`

It has a 10-second time limit, a 50 KB output limit, and no shell operators. It cannot install packages, change files, delete data, access home-folder secrets, run network commands, or execute arbitrary scripts.

## One-time approval for source inspection

Sulvana can also ask to run one of these exact read-only command forms inside the project:

- `ls <project-folder>`
- `head -n <1–120> <project-source-file>`
- `wc -l <project-source-file>`
- `rg -n -F <literal-text> <project-source-file>`
- `git log -5 --oneline`

The app shows the exact command and waits up to 60 seconds for **Allow once** or **Deny**. Stop, closing the request, and timeout deny it. An approval is tied to one unpredictable request ID and cannot authorize a different command. Source inspection excludes hidden paths, model files, generated images, datasets, installed dependencies, files outside the project, and files larger than 256 KB.

Commands that write, install, delete, change settings, use credentials, read excluded folders, or run arbitrary shell or code remain blocked. Web search runs when the user asks for online/current information, or when Sulvana is unsure and Search when unsure is on.

## Notes (automatic)

Before every reply, Sulvana adds up to five sections (about 12,000 characters) from Markdown files in `knowledge/` that share words (or, for Khmer, letter sequences) with the message. This needs no tool call and runs entirely on this computer. Files the user adds to `knowledge/notes/` are included; see `knowledge/notes/README.md`. The sections used are listed under the answer as Sources. Notes are reference material, not instructions.

## Coding mode

With **Code** switched on under the message box, Sulvana becomes a coding agent for one project folder (chosen with the folder button, or in Settings → Coding project folder). It works step by step with six tools: list files, read a file, search files, edit a file (by line numbers or by exact old text), write a new file, and run a command. Each step appears in the reply as a card; edits show their diff and commands show their output.

Reading and searching are automatic. Edits and commands wait for approval, and commands run in a sandbox without network access that can only change the project folder. Under a reply that changed files, **Undo** restores them. If the project has an `AGENTS.md`, `CLAUDE.md` or `SULVANA.md`, Sulvana reads it as the project's instructions.

The harness lives in `sulvana_code.py`. The underlying 8B model is a modest coder: it often needs a few tries, and its edits deserve a careful look before you allow them.
