# Notes for Sulvana

Put Markdown (`.md`) files in this folder to give Sulvana information it does not know: facts about you, your school or work, Khmer vocabulary and spellings you want it to use, how you like answers written, project details, and so on.

Before every reply, Sulvana looks through all Markdown files in `knowledge/` (including this folder and any subfolders) and adds the up-to-five sections that best match your message to its context. The notes it used appear as **Sources** under the answer. Changes are picked up on the next message; nothing needs restarting.

## Writing notes that work well

- Split a file into sections with headings (`#`, `##`, `###`). Sulvana picks whole sections, so keep each one about a single topic and under about 3,000 characters.
- Use the words people will actually ask with, in the language they will ask in. Matching is by shared words (English) and shared letter sequences (Khmer), not by meaning, so a note written only in English is unlikely to be found by a question written in Khmer. Bilingual notes work best.
- Write facts plainly. Notes are treated as reference material, not commands, so "Always answer in a formal tone" is weaker than putting such preferences in Settings.
- At most five sections and about 12,000 characters of notes are added per reply.

Files starting with `.` and files larger than 2 MB are ignored. This README is skipped too.

Notes stay on this computer. They are not used for fine-tuning unless you deliberately convert them into a dataset.
