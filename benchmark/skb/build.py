#!/usr/bin/env python3
"""Build the Sulvana Khmer Benchmark (SKB) files from the item list below. Deterministic; no scraped text.

Every item was written for this benchmark. Khmer items must be answered in Khmer script to score.
"""

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
VERSION = "1.1.0"
ITEMS = []


def add(section, prompt, check, lang="km", difficulty="medium"):
    ITEMS.append({"section": section, "prompt": prompt, "lang": lang, "difficulty": difficulty, "check": check})


def answer(*aliases, khmer=True):
    return {"type": "contains", "any": list(aliases), "require_khmer": khmer}


def number(value, khmer=True, tolerance=1e-6):
    return {"type": "number", "value": value, "tolerance": tolerance, "require_khmer": khmer}


def keywords(*groups, khmer=True, english=False):
    return {"type": "keywords", "groups": [list(g) for g in groups], "require_khmer": khmer, "require_english": english}


def starts(*aliases, max_chars=None, khmer=True):
    return {"type": "starts", "any": list(aliases), "max_chars": max_chars, "require_khmer": khmer}


# ---------------------------------------------------------------- A. reading comprehension (answers in Khmer)
P1 = ("សុខាមានអាយុដប់ប្រាំបីឆ្នាំ។ នាងរស់នៅក្នុងខេត្តសៀមរាប ជាមួយឪពុកម្តាយ និងប្អូនប្រុសពីរនាក់។ "
      "រៀងរាល់ព្រឹក សុខាជិះកង់ទៅសាលារៀន ដែលមានចម្ងាយប្រាំគីឡូម៉ែត្រពីផ្ទះ។ "
      "នាងចូលចិត្តមុខវិជ្ជាគណិតវិទ្យាជាងគេ ហើយចង់ក្លាយជាវិស្វករនៅថ្ងៃអនាគត។ នៅថ្ងៃអាទិត្យ នាងជួយម្តាយលក់នំនៅផ្សារ។")
P2 = ("ឆ្នាំនេះ ភ្លៀងធ្លាក់យឺតជាងធម្មតាប្រហែលមួយខែ។ លោកតាសំ ជាកសិករនៅខេត្តបាត់ដំបង បានសម្រេចចិត្តដាំពោតជំនួសស្រូវ "
      "ព្រោះពោតត្រូវការទឹកតិចជាង។ គាត់មានដីបីហិកតា។ គាត់ដាំពោតលើដីពីរហិកតា ហើយទុកដីដែលនៅសល់សម្រាប់ដាំបន្លែ។")
P3 = ("ហាងរបស់លោកស្រីចាន់ លក់កាហ្វេមួយកែវ ៥០០០ រៀល និងតែមួយកែវ ៣០០០ រៀល។ ព្រឹកនេះ គាត់លក់កាហ្វេបាន ២០ កែវ "
      "និងតែបាន ១៥ កែវ។ អតិថិជនដែលទិញកាហ្វេពីរកែវ ទទួលបាននំមួយដោយឥតគិតថ្លៃ។")
P4 = ("ប្រាសាទអង្គរវត្តត្រូវបានសាងសង់នៅសតវត្សទីដប់ពីរ ក្នុងរជ្ជកាលព្រះបាទសូរ្យវរ្ម័នទីពីរ។ ដំបូងឡើយ ប្រាសាទនេះឧទ្ទិសដល់ព្រះវិស្ណុ។ "
      "សព្វថ្ងៃ អង្គរវត្តជានិមិត្តរូបជាតិ ហើយមានរូបនៅលើទង់ជាតិកម្ពុជា។")
P5 = ("ដារ៉ាចេញពីផ្ទះម៉ោងប្រាំពីរព្រឹក។ ជាធម្មតា គាត់ធ្វើដំណើរទៅការិយាល័យអស់រយៈពេលសែសិបប្រាំនាទី។ ការប្រជុំចាប់ផ្តើមម៉ោងប្រាំបីព្រឹក។ "
      "ថ្ងៃនេះ ផ្លូវកកស្ទះ ដូច្នេះការធ្វើដំណើររបស់គាត់យូរជាងធម្មតាម្ភៃនាទី។")
read = lambda passage, question: f"អត្ថបទ៖ {passage}\n\nសំណួរ៖ {question}\nសូមឆ្លើយជាភាសាខ្មែរ។"
add("reading", read(P1, "តើសុខារស់នៅខេត្តអ្វី?"), answer("សៀមរាប"), difficulty="easy")
add("reading", read(P1, "តើសុខាមានប្អូនប្រុសប៉ុន្មាននាក់?"), number(2))
add("reading", read(P1, "តើសុខាចង់ក្លាយជាអ្វីនៅថ្ងៃអនាគត?"), answer("វិស្វករ"), difficulty="easy")
add("reading", read(P1, "ប្រសិនបើសុខាជិះកង់ទៅសាលា ហើយត្រឡប់មកផ្ទះវិញ តើនាងជិះបានចម្ងាយសរុបប៉ុន្មានគីឡូម៉ែត្រក្នុងមួយថ្ងៃ?"), number(10), difficulty="hard")
add("reading", read(P2, "តើលោកតាសំរស់នៅខេត្តអ្វី?"), answer("បាត់ដំបង"), difficulty="easy")
add("reading", read(P2, "ហេតុអ្វីបានជាលោកតាសំដាំពោតជំនួសស្រូវ?"), keywords(["ទឹកតិច", "ទឹកតិចជាង", "មិនត្រូវការទឹកច្រើន"]))
add("reading", read(P2, "តើមានដីប៉ុន្មានហិកតាដែលលោកតាសំមិនបានដាំពោត?"), number(1), difficulty="hard")
add("reading", read(P2, "តើលោកតាសំដាំអ្វីលើដីដែលនៅសល់?"), answer("បន្លែ"))
add("reading", read(P3, "តើលោកស្រីចាន់រកចំណូលពីការលក់កាហ្វេបានប៉ុន្មានរៀលព្រឹកនេះ?"), number(100000))
add("reading", read(P3, "តើលោកស្រីចាន់រកចំណូលសរុបពីកាហ្វេ និងតែ បានប៉ុន្មានរៀល?"), number(145000), difficulty="hard")
add("reading", read(P3, "តើព្រឹកនេះ លោកស្រីចាន់លក់ភេសជ្ជៈបានប៉ុន្មានកែវសរុប?"), number(35))
add("reading", read(P3, "តើអតិថិជនដែលទិញកាហ្វេពីរកែវ ទទួលបានអ្វីដោយឥតគិតថ្លៃ?"), answer("នំ"), difficulty="easy")
add("reading", read(P4, "តើប្រាសាទអង្គរវត្តត្រូវបានសាងសង់នៅសតវត្សទីប៉ុន្មាន?"), number(12))
add("reading", read(P4, "តើប្រាសាទអង្គរវត្តត្រូវបានសាងសង់ក្នុងរជ្ជកាលព្រះមហាក្សត្រណា?"), answer("សូរ្យវរ្ម័ន"))
add("reading", read(P4, "ដំបូងឡើយ តើប្រាសាទអង្គរវត្តឧទ្ទិសដល់ព្រះណា?"), answer("វិស្ណុ"))
add("reading", read(P4, "តើរូបប្រាសាទអង្គរវត្តមាននៅលើអ្វី?"), answer("ទង់ជាតិ", "ទង់"), difficulty="easy")
add("reading", read(P5, "ជាធម្មតា តើដារ៉ាទៅដល់ការិយាល័យម៉ោងប៉ុន្មាន?"), answer("7:45", "៧:៤៥", "៧ ម៉ោង ៤៥", "ប្រាំពីរម៉ោងសែសិបប្រាំ", "ម៉ោង ៧ និង ៤៥"), difficulty="hard")
add("reading", read(P5, "ថ្ងៃនេះ តើដារ៉ាទៅដល់ការិយាល័យម៉ោងប៉ុន្មាន?"), answer("8:05", "៨:០៥", "៨ ម៉ោង ៥", "ប្រាំបីម៉ោងប្រាំនាទី", "ម៉ោង ៨ និង ៥"), difficulty="hard")
add("reading", read(P5, "ថ្ងៃនេះ តើដារ៉ាយឺតពេលប្រជុំប៉ុន្មាននាទី?"), number(5), difficulty="hard")
add("reading", read(P5, "ថ្ងៃនេះ តើដារ៉ាធ្វើដំណើរអស់រយៈពេលប៉ុន្មាននាទី?"), number(65))

# ---------------------------------------------------------------- B. word problems in Khmer
for prompt, value, level in [
    ("ផ្លែស្វាយមួយគីឡូក្រាមតម្លៃ ៦០០០ រៀល។ តើស្វាយ ៣.៥ គីឡូក្រាម តម្លៃប៉ុន្មានរៀល?", 21000, "medium"),
    ("សិស្ស ៤៨ នាក់ត្រូវបែងចែកជាក្រុម ក្រុមនីមួយៗមាន ៦ នាក់។ តើមានក្រុមប៉ុន្មាន?", 8, "easy"),
    ("ឡានមួយធ្វើដំណើរ ៦០ គីឡូម៉ែត្រក្នុងមួយម៉ោង។ តើវាត្រូវការប៉ុន្មានម៉ោង ដើម្បីធ្វើដំណើរ ២១០ គីឡូម៉ែត្រ?", 3.5, "medium"),
    ("អាវមួយតម្លៃ ៤០ ដុល្លារ។ ហាងបញ្ចុះតម្លៃ ២៥%។ តើតម្លៃថ្មីប៉ុន្មានដុល្លារ?", 30, "medium"),
    ("ចតុកោណកែងមួយមានបណ្តោយ ១២ ម៉ែត្រ និងទទឹង ៧ ម៉ែត្រ។ តើក្រឡាផ្ទៃរបស់វាប៉ុន្មានម៉ែត្រការ៉េ?", 84, "easy"),
    ("ចតុកោណកែងមួយមានបណ្តោយ ១២ ម៉ែត្រ និងទទឹង ៧ ម៉ែត្រ។ តើបរិមាត្ររបស់វាប៉ុន្មានម៉ែត្រ?", 38, "medium"),
    ("បងមានអាយុច្រើនជាងប្អូន ៦ ឆ្នាំ។ អាយុរបស់ពួកគេបូកគ្នាស្មើ ៣០ ឆ្នាំ។ តើប្អូនអាយុប៉ុន្មានឆ្នាំ?", 12, "hard"),
    ("ខ្ញុំមានលុយ ២០ ដុល្លារ។ ខ្ញុំទិញសៀវភៅ ៣ ក្បាល ក្បាលនីមួយៗតម្លៃ ៤.៥ ដុល្លារ។ តើខ្ញុំនៅសល់ប៉ុន្មានដុល្លារ?", 6.5, "medium"),
    ("មួយដុល្លារស្មើ ៤១០០ រៀល។ តើ ២៥ ដុល្លារស្មើប៉ុន្មានរៀល?", 102500, "medium"),
    ("ធុងទឹកមួយផ្ទុកបាន ២០០ លីត្រ។ ឥឡូវនេះវាពេញ ៤០%។ តើត្រូវបន្ថែមទឹកប៉ុន្មានលីត្រទៀត ទើបធុងពេញ?", 120, "hard"),
    ("x + 2x + 3x = ៤២។ តើ x ស្មើប៉ុន្មាន?", 7, "medium"),
    ("តើមធ្យមភាគនៃ ៨, ១២, ១៥ និង ២៥ ស្មើប៉ុន្មាន?", 15, "medium"),
    ("ក្នុងថ្នាក់មួយមានសិស្ស ៤០ នាក់ ក្នុងនោះ ៦០% ជាសិស្សស្រី។ តើមានសិស្សប្រុសប៉ុន្មាននាក់?", 16, "hard"),
    ("កម្មករ ៣ នាក់សាងសង់ជញ្ជាំងមួយអស់ ១២ ថ្ងៃ។ បើមានកម្មករ ៦ នាក់ ធ្វើការក្នុងល្បឿនដូចគ្នា តើត្រូវការប៉ុន្មានថ្ងៃ?", 6, "hard"),
    ("តើលេខបន្ទាប់ក្នុងលំដាប់ ២, ៦, ១២, ២០, ៣០, ... ជាលេខអ្វី?", 42, "hard"),
    ("តើ ១៥% នៃ ២៤០ ស្មើប៉ុន្មាន?", 36, "medium"),
    ("រង្វង់មួយមានកាំ ៥ សង់ទីម៉ែត្រ។ យក π = ៣.១៤។ តើបរិមាត្ររបស់វាប៉ុន្មានសង់ទីម៉ែត្រ?", 31.4, "hard"),
    ("សុភាសន្សំលុយ ១៥០០០ រៀលរៀងរាល់សប្តាហ៍។ តើត្រូវការប៉ុន្មានសប្តាហ៍ ដើម្បីសន្សំបាន ២៧០០០០ រៀល?", 18, "medium"),
    ("ឪពុកអាយុ ៤០ ឆ្នាំ ហើយកូនអាយុ ១០ ឆ្នាំ។ តើប៉ុន្មានឆ្នាំទៀត ឪពុកនឹងមានអាយុទ្វេដងនៃអាយុកូន?", 20, "hard"),
    ("តើ ២៥ × ៤ + ១០ ស្មើប៉ុន្មាន?", 110, "easy"),
]:
    add("math", prompt + " សូមឆ្លើយជាភាសាខ្មែរ។", number(value), difficulty=level)
add("math", "ថ្ងៃនេះជាថ្ងៃច័ន្ទ។ តើ ១០ ថ្ងៃទៀតជាថ្ងៃអ្វី? សូមឆ្លើយជាភាសាខ្មែរ។", answer("ព្រហស្បតិ៍", "ព្រហស្បត្តិ៍"), difficulty="hard")

# ---------------------------------------------------------------- C. knowledge, asked and answered in Khmer
for prompt, aliases, level in [
    ("តើរាជធានីរបស់ប្រទេសកម្ពុជាមានឈ្មោះអ្វី?", ["ភ្នំពេញ"], "easy"),
    ("តើទន្លេធំជាងគេដែលហូរកាត់ប្រទេសកម្ពុជាមានឈ្មោះអ្វី?", ["មេគង្គ"], "easy"),
    ("តើបឹងទឹកសាបធំជាងគេនៅប្រទេសកម្ពុជាមានឈ្មោះអ្វី?", ["ទន្លេសាប"], "medium"),
    ("តើរូបិយប័ណ្ណជាតិរបស់ប្រទេសកម្ពុជាមានឈ្មោះអ្វី?", ["រៀល"], "easy"),
    ("តើប្រទេសណាដែលនៅជាប់ព្រំដែនខាងលិចនៃប្រទេសកម្ពុជា?", ["ថៃ"], "medium"),
    ("តើប្រទេសណាដែលនៅជាប់ព្រំដែនខាងកើតនៃប្រទេសកម្ពុជា?", ["វៀតណាម", "យួន"], "medium"),
    ("តើប្រទេសណាដែលនៅជាប់ព្រំដែនខាងជើងនៃប្រទេសកម្ពុជា ក្រៅពីប្រទេសថៃ?", ["ឡាវ"], "medium"),
    ("តើភ្នំខ្ពស់ជាងគេនៅប្រទេសកម្ពុជាមានឈ្មោះអ្វី?", ["ឱរ៉ាល់", "អូរ៉ាល់"], "hard"),
    ("តើពិធីបុណ្យចូលឆ្នាំថ្មីប្រពៃណីជាតិខ្មែរ ប្រារព្ធឡើងនៅខែអ្វី?", ["មេសា"], "medium"),
    ("តើប្រទេសកម្ពុជាទទួលបានឯករាជ្យពីប្រទេសណា?", ["បារាំង"], "medium"),
    ("តើផ្កាជាតិរបស់ប្រទេសកម្ពុជាគឺផ្កាអ្វី?", ["រំដួល"], "hard"),
    ("តើសត្វជាតិរបស់ប្រទេសកម្ពុជាគឺសត្វអ្វី?", ["គោព្រៃ"], "hard"),
    ("តើប្រាសាទអង្គរវត្តស្ថិតនៅក្នុងខេត្តណា?", ["សៀមរាប"], "easy"),
    ("តើភពណាដែលធំជាងគេក្នុងប្រព័ន្ធព្រះអាទិត្យ?", ["ព្រហស្បតិ៍", "ព្រហស្បត្តិ៍"], "medium"),
    ("តើរុក្ខជាតិស្រូបយកឧស្ម័នអ្វីពីខ្យល់ ពេលធ្វើរស្មីសំយោគ?", ["កាបូនឌីអុកស៊ីត", "កាបូនិច"], "hard"),
    ("តើមនុស្សដកដង្ហើមចូលយកឧស្ម័នអ្វីដើម្បីរស់?", ["អុកស៊ីសែន", "អុកស៊ីហ្សែន"], "easy"),
    ("តើសរីរាង្គអ្វីដែលបូមឈាមទៅគ្រប់ផ្នែកនៃរាងកាយ?", ["បេះដូង"], "easy"),
]:
    add("knowledge", prompt + " សូមឆ្លើយជាភាសាខ្មែរ។", answer(*aliases), difficulty=level)
for prompt, value, level in [
    ("តើអក្សរខ្មែរមានព្យញ្ជនៈប៉ុន្មានតួ?", 33, "hard"),
    ("តើប្រទេសកម្ពុជាទទួលបានឯករាជ្យនៅឆ្នាំណា (គ្រិស្តសករាជ)?", 1953, "hard"),
    ("តើទឹកកកកើតឡើងនៅសីតុណ្ហភាពប៉ុន្មានអង្សាសេ?", 0, "easy"),
]:
    add("knowledge", prompt + " សូមឆ្លើយជាភាសាខ្មែរ។", number(value), difficulty=level)

# ---------------------------------------------------------------- D. English to Khmer (key words that any correct translation contains)
for english, groups, level in [
    ("I am hungry.", [["ឃ្លាន"]], "easy"),
    ("The weather is very hot today.", [["ក្តៅ", "ក្ដៅ"], ["ថ្ងៃនេះ"]], "easy"),
    ("Where is the hospital?", [["មន្ទីរពេទ្យ", "មន្ទីពេទ្យ"], ["ណា"]], "medium"),
    ("My mother is a teacher.", [["ម្តាយ", "ម្ដាយ", "ម៉ាក់"], ["គ្រូ"]], "medium"),
    ("We will go to the market tomorrow.", [["ផ្សារ"], ["ស្អែក"]], "medium"),
    ("Please drink more water.", [["ទឹក"], ["ផឹក"]], "easy"),
    ("The children are playing football.", [["ក្មេង", "កុមារ", "កូន"], ["បាល់"]], "medium"),
    ("How much does this shirt cost?", [["អាវ"], ["ប៉ុន្មាន"]], "medium"),
    ("I have two older brothers.", [["បងប្រុស"], ["ពីរ", "២"]], "hard"),
    ("She reads a book every night.", [["សៀវភៅ"], ["អាន"], ["យប់"]], "medium"),
    ("The road is wet because it rained.", [["ផ្លូវ"], ["សើម"], ["ភ្លៀង"]], "hard"),
    ("Thank you very much for your help.", [["អរគុណ"], ["ជួយ", "ជំនួយ"]], "easy"),
    ("The doctor said I must rest for three days.", [["គ្រូពេទ្យ", "វេជ្ជបណ្ឌិត", "ពេទ្យ"], ["សម្រាក"], ["បី", "៣"]], "hard"),
    ("Learning a new language takes time and patience.", [["ភាសា"], ["ពេល"], ["អត់ធ្មត់"]], "hard"),
    ("The farmer plants rice in the rainy season.", [["កសិករ"], ["ស្រូវ"], ["វស្សា", "រដូវភ្លៀង"]], "hard"),
]:
    add("translate_to_khmer", f"សូមបកប្រែប្រយោគនេះជាភាសាខ្មែរ៖ {english}", keywords(*groups), difficulty=level)

# ---------------------------------------------------------------- E. Khmer to English
for khmer, groups, level in [
    ("ខ្ញុំចូលចិត្តញ៉ាំផ្លែស្វាយ។", [["like", "love", "enjoy"], ["mango"]], "easy"),
    ("ឆ្កែកំពុងដេកនៅក្រោមតុ។", [["dog"], ["sleep"], ["table"]], "medium"),
    ("បងស្រីរបស់ខ្ញុំធ្វើការនៅធនាគារ។", [["sister"], ["bank"]], "medium"),
    ("ថ្ងៃស្អែកនឹងមានភ្លៀងខ្លាំង។", [["tomorrow"], ["rain"]], "easy"),
    ("សូមបិទទ្វារ។", [["close", "shut"], ["door"]], "easy"),
    ("យើងបានទៅលេងសមុទ្រកាលពីសប្តាហ៍មុន។", [["sea", "beach", "ocean"], ["last week"]], "hard"),
    ("គាត់មិនអាចមកបានទេ ព្រោះគាត់ឈឺ។", [["can't", "cannot", "could not", "couldn't", "unable", "can not"], ["sick", "ill"]], "medium"),
    ("ផ្ទះរបស់យើងនៅជិតសាលារៀន។", [["house", "home"], ["near", "close to", "next to"], ["school"]], "medium"),
    ("ខ្ញុំត្រូវការពេលវេលាបន្ថែមដើម្បីបញ្ចប់កិច្ចការនេះ។", [["need"], ["time"], ["finish", "complete"]], "hard"),
    ("កសិករដាំស្រូវនៅរដូវវស្សា។", [["farmer"], ["rice"], ["rain", "wet season", "monsoon"]], "hard"),
]:
    add("translate_to_english", f"Translate into English: {khmer}", keywords(*groups, khmer=False, english=True), lang="en", difficulty=level)

# ---------------------------------------------------------------- F. following instructions in Khmer (checked by rule)
fmt = lambda **rule: {"type": "format", "require_khmer": True, **rule}
add("instructions", "សូមសរសេរប្រយោគបីអំពីទឹក។ ប្រយោគនីមួយៗត្រូវបញ្ចប់ដោយសញ្ញា ។", fmt(khmer_full_stops=3), difficulty="hard")
add("instructions", "សូមរាយឈ្មោះផ្លែឈើបួនមុខ ជាបញ្ជីដែលមានលេខរៀងពី ១ ដល់ ៤ ជាភាសាខ្មែរ។", fmt(numbered_lines=4), difficulty="medium")
add("instructions", "ឆ្លើយតែមួយពាក្យប៉ុណ្ណោះ៖ តើមេឃនៅពេលថ្ងៃភ្លឺស្រឡះមានពណ៌អ្វី?", fmt(contains_all=["ខៀវ"], max_chars=12), difficulty="medium")
add("instructions", "សូមសរសេរពាក្យ «សួស្តី» បីដង ដោយបំបែកដោយសញ្ញាក្បៀស ហើយកុំសរសេរអ្វីផ្សេងទៀត។", fmt(count={"សួស្តី": 3}, max_chars=30), difficulty="medium")
add("instructions", "សូមសរសេរប្រយោគមួយអំពីសាលារៀន ដោយមិនប្រើអក្សរឡាតាំង ឬលេខ។", fmt(contains_all=["សាលា"], no_latin=True, no_digits=True), difficulty="medium")
add("instructions", "ឆ្លើយត្រឹមតែ «បាទ» ឬ «ទេ»៖ តើព្រះអាទិត្យរះនៅទិសខាងកើតមែនទេ?", starts("បាទ", "ចាស", "មែន", max_chars=10), difficulty="easy")
add("instructions", "សូមសរសេរលេខពី ១ ដល់ ៥ ជាលេខខ្មែរ ដោយបំបែកដោយដកឃ្លា ហើយកុំសរសេរអ្វីផ្សេងទៀត។", fmt(contains_all=["១ ២ ៣ ៤ ៥"], max_chars=15), difficulty="medium")
add("instructions", "សូមបកប្រែពាក្យ «water» ជាភាសាខ្មែរ ហើយឆ្លើយតែពាក្យនោះប៉ុណ្ណោះ។", fmt(contains_all=["ទឹក"], max_chars=8), difficulty="easy")
add("instructions", "សូមសរសេរប្រយោគពីរ។ ប្រយោគទីមួយត្រូវមានពាក្យ «ឆ្មា» ហើយប្រយោគទីពីរត្រូវមានពាក្យ «ឆ្កែ»។", fmt(khmer_full_stops=2, ordered=["ឆ្មា", "ឆ្កែ"]), difficulty="hard")
add("instructions", "សូមរាយឈ្មោះថ្ងៃទាំងប្រាំពីរក្នុងមួយសប្តាហ៍ ជាភាសាខ្មែរ។", fmt(contains_all=["ច័ន្ទ", "អង្គារ", "ពុធ", "សុក្រ", "សៅរ៍", "អាទិត្យ"], contains_any=["ព្រហស្បតិ៍", "ព្រហស្បត្តិ៍"]), difficulty="hard")
add("instructions", "សូមរាយឈ្មោះខែទាំងបីដំបូងនៃឆ្នាំ ជាភាសាខ្មែរ។", fmt(contains_all=["មករា", "កុម្ភៈ", "មីនា"]), difficulty="hard")
add("instructions", "សូមឆ្លើយជាភាសាខ្មែរតែប៉ុណ្ណោះ ដោយគ្មានពាក្យអង់គ្លេស៖ តើកុំព្យូទ័រជាអ្វី?", fmt(no_latin=True, min_khmer_chars=20), difficulty="medium")
add("instructions", "តើពាក្យណាដែលមានន័យផ្ទុយនឹងពាក្យ «ធំ»? ឆ្លើយតែមួយពាក្យ។", fmt(contains_all=["តូច"], max_chars=10), difficulty="easy")
add("instructions", "តើពាក្យណាដែលមានន័យផ្ទុយនឹងពាក្យ «ក្តៅ»? ឆ្លើយតែមួយពាក្យ។", fmt(contains_all=["ត្រជាក់"], max_chars=12), difficulty="medium")
add("instructions", "សូមរៀបលេខទាំងនេះពីតូចទៅធំ៖ ៩, ២, ៧, ៤។ ឆ្លើយតែលេខ ដោយបំបែកដោយសញ្ញាក្បៀស។", fmt(number_sequence=[2, 4, 7, 9]), difficulty="medium")

# ---------------------------------------------------------------- G. reasoning in Khmer
add("reasoning", "សុខាខ្ពស់ជាងដារ៉ា។ ដារ៉ាខ្ពស់ជាងវណ្ណា។ តើនរណាទាបជាងគេ? សូមឆ្លើយជាភាសាខ្មែរ។", answer("វណ្ណា"), difficulty="medium")
add("reasoning", "បើថ្ងៃស្អែកជាថ្ងៃសុក្រ តើម្សិលមិញជាថ្ងៃអ្វី? សូមឆ្លើយជាភាសាខ្មែរ។", answer("ពុធ"), difficulty="hard")
add("reasoning", "ក្នុងប្រអប់មានបាល់ក្រហម ៣ គ្រាប់ និងបាល់ខៀវ ៥ គ្រាប់។ បើយកបាល់ខៀវចេញ ២ គ្រាប់ តើនៅសល់បាល់សរុបប៉ុន្មានគ្រាប់? សូមឆ្លើយជាភាសាខ្មែរ។", number(6), difficulty="easy")
add("reasoning", "ចាន់ជាក្មេងស្រី។ គាត់មានប្អូនប្រុសបីនាក់។ ប្អូនប្រុសម្នាក់ៗមានបងស្រីតែម្នាក់ គឺចាន់។ តើគ្រួសារនោះមានកូនប៉ុន្មាននាក់? សូមឆ្លើយជាភាសាខ្មែរ។", number(4), difficulty="hard")
add("reasoning", "ម៉ោងឥឡូវគឺ ១០:៣០ ព្រឹក។ តើ ៩០ នាទីទៀត ជាម៉ោងប៉ុន្មាន? សូមឆ្លើយជាភាសាខ្មែរ។", answer("12:00", "១២:០០", "ថ្ងៃត្រង់", "ម៉ោង ១២", "ម៉ោង 12", "ដប់ពីរ"), difficulty="hard")
add("reasoning", "លេខមួយគុណនឹង ៤ រួចបូក ៧ ទទួលបាន ៣១។ តើលេខនោះជាលេខអ្វី? សូមឆ្លើយជាភាសាខ្មែរ។", number(6), difficulty="medium")
add("reasoning", "ផ្លែប៉ោម ១២ ផ្លែ ត្រូវចែកស្មើគ្នាឲ្យក្មេង ៤ នាក់។ ក្មេងម្នាក់ញ៉ាំអស់ ២ ផ្លែ។ តើក្មេងនោះនៅសល់ផ្លែប៉ោមប៉ុន្មានផ្លែ? សូមឆ្លើយជាភាសាខ្មែរ។", number(1), difficulty="hard")
add("reasoning", "សត្វទាំងអស់ដែលហើរបាន សុទ្ធតែមានស្លាប។ សត្វភេនឃ្វីនមានស្លាប។ តើយើងអាចសន្និដ្ឋានបានថា សត្វភេនឃ្វីនហើរបាន ឬទេ? ឆ្លើយ «បាន» ឬ «ទេ»។", starts("ទេ", "មិនអាច", "មិនបាន", max_chars=40), difficulty="hard")

# ---------------------------------------------------------------- H. English control questions
add("english", "What is 17 × 23?", number(391, khmer=False), lang="en", difficulty="medium")
add("english", "A train leaves at 2:45 pm and arrives at 5:10 pm. How many minutes does the trip take?", number(145, khmer=False), lang="en", difficulty="hard")
add("english", "What is the capital of Australia?", answer("Canberra", khmer=False), lang="en", difficulty="medium")
add("english", "If all bloops are razzies and all razzies are lazzies, are all bloops lazzies? Answer yes or no.", starts("yes", max_chars=60, khmer=False), lang="en", difficulty="medium")
add("english", "How many prime numbers are there between 10 and 30?", number(6, khmer=False), lang="en", difficulty="hard")
add("english", "What is the next number: 1, 1, 2, 3, 5, 8, 13, …?", number(21, khmer=False), lang="en", difficulty="easy")
add("english", "A shirt costs $80 after a 20% discount. What was the original price in dollars?", number(100, khmer=False), lang="en", difficulty="hard")
add("english", "Who wrote the play 'Romeo and Juliet'?", answer("Shakespeare", khmer=False), lang="en", difficulty="easy")


# ---------------------------------------------------------------- I. basics (single words, simple sums, yes/no)
for khmer, english in [("ឆ្កែ", ["dog"]), ("ឆ្មា", ["cat"]), ("ផ្ទះ", ["house", "home"]), ("ទឹក", ["water"]), ("បាយ", ["rice"]),
                       ("សៀវភៅ", ["book"]), ("ព្រះអាទិត្យ", ["sun"]), ("ឡាន", ["car"]), ("គ្រូ", ["teacher"]), ("ផ្កា", ["flower"])]:
    add("basics", f"តើពាក្យ «{khmer}» ជាភាសាអង់គ្លេសគឺអ្វី?", answer(*english, khmer=False), difficulty="easy")
for english, khmer in [("mother", ["ម្តាយ", "ម្ដាយ", "ម៉ាក់"]), ("father", ["ឪពុក", "ប៉ា", "បិតា"]), ("fish", ["ត្រី"]), ("school", ["សាលា"]),
                       ("red", ["ក្រហម"]), ("big", ["ធំ"]), ("thank you", ["អរគុណ"]), ("good morning", ["អរុណសួស្តី"]),
                       ("rice field", ["ស្រែ"]), ("teacher", ["គ្រូ"])]:
    add("basics", f"What is the Khmer word for '{english}'? Write it in Khmer script.", answer(*khmer, khmer=False), lang="en", difficulty="easy")
for prompt, value in [("២ + ៣", 5), ("១០ - ៤", 6), ("៦ × ៧", 42), ("២០ ÷ ៤", 5), ("១០០ - ២៥", 75)]:
    add("basics", f"តើ {prompt} ស្មើប៉ុន្មាន? សូមឆ្លើយជាភាសាខ្មែរ។", number(value), difficulty="easy")
for prompt, aliases in [("តើទឹកសមុទ្រមានរសជាតិប្រៃមែនទេ?", ("បាទ", "ចាស", "មែន", "ប្រៃ")),
                        ("តើត្រីរស់នៅក្នុងទឹកមែនទេ?", ("បាទ", "ចាស", "មែន")),
                        ("តើព្រះច័ន្ទក្តៅជាងព្រះអាទិត្យមែនទេ?", ("ទេ", "មិន")),
                        ("តើភ្នំពេញជារាជធានីនៃប្រទេសកម្ពុជាមែនទេ?", ("បាទ", "ចាស", "មែន")),
                        ("តើមួយសប្តាហ៍មានប្រាំពីរថ្ងៃមែនទេ?", ("បាទ", "ចាស", "មែន"))]:
    add("basics", prompt + " ឆ្លើយ «បាទ» ឬ «ទេ»។", starts(*aliases, max_chars=60), difficulty="easy")


def main() -> None:
    questions, keys = [], []
    for number_, item in enumerate(ITEMS, 1):
        item_id = f"SKB-{number_:03d}"
        questions.append({"id": item_id, "section": item["section"], "lang": item["lang"], "difficulty": item["difficulty"], "prompt": item["prompt"]})
        keys.append({"id": item_id, "check": item["check"]})
    write = lambda name, rows: (HERE / name).write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    write("questions.jsonl", questions)
    write("answer_key.private.jsonl", keys)
    from collections import Counter
    manifest = {"name": "Sulvana Khmer Benchmark", "version": VERSION, "items": len(ITEMS), "license": "CC0-1.0",
                "provenance": "Original items written for this project; no scraped text.",
                "sections": dict(Counter(i["section"] for i in ITEMS)), "difficulty": dict(Counter(i["difficulty"] for i in ITEMS))}
    (HERE / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False))


if __name__ == "__main__":
    main()
