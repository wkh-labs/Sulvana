# Notes for Sulvana

Put Markdown (`.md`) files in this folder to give Sulvana information it does not know: facts about you, your school or work, Khmer vocabulary and spellings you want it to use, how you like answers written, project details, and so on.

Before every reply, Sulvana reads an index of all Markdown files in `knowledge/` (including this folder and any subfolders): the description of each file in `knowledge/INDEX.md` plus its section titles. It picks up to three files that help with your message and reads their relevant sections; keyword matching adds any closely matching section it missed. The notes it used appear as **Sources** under the answer. Changes are picked up on the next message; nothing needs restarting.

When you add a note, also add one line to `knowledge/INDEX.md` saying what it is for and when to use it (`- my-note.md: …`). That description is what Sulvana reads when deciding whether to open the note.

## Writing notes that work well

- Split a file into sections with headings (`#`, `##`, `###`). Sulvana picks whole sections, so keep each one about a single topic and under about 3,000 characters.
- Use the words people will actually ask with, in the language they will ask in. Matching is by shared words (English) and shared letter sequences (Khmer), not by meaning, so a note written only in English is unlikely to be found by a question written in Khmer. Bilingual notes work best.
- Write facts plainly. Notes are treated as reference material, not commands, so "Always answer in a formal tone" is weaker than putting such preferences in Settings.
- At most five sections and about 12,000 characters of notes are added per reply.

Files starting with `.` and files larger than 2 MB are ignored. This README is skipped too.

Notes stay on this computer. They are not used for fine-tuning unless you deliberately convert them into a dataset.
