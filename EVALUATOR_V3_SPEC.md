# NyayaBench Evaluator v3: Specification

**Status: APPROVED by Gursimran Singh on 12 November 2026. No v3 code exists. Drafted 11 November 2026 and amended on 12 November 2026 with his decisions. No open item blocks approval (section 11).**
This file is a specification only. It contains no code and no v3 scores.

Sign-off: Gursimran Singh   Date: 12 November 2026   Commit of approved spec: `441edf07d4be284f363cccb7d99f8b0cd80e11cc` (tag `evaluator-v3-spec-approved`)

---

## 1. Purpose

Evaluator v3 corrects text-matching defects in `evaluator.py` (called v2 below). It does not change what the benchmark claims to measure, the 0 to 9 scale, or the pass threshold of 6/9.

v3 is a second scorer that sits beside v2. It never replaces v2 and never rescores published results in place: every published v2 number stays as published and stays reproducible.

## 2. Frozen inputs

`evaluator.py` stays byte-identical. v3 goes in a new file, `evaluator_v3.py`, written only after this spec is approved and committed.

| Input | Path (repo-relative) | SHA-256 |
|---|---|---|
| v2 scorer | `evaluator.py` | `02fd0f27b2b4d5a7419e5b242fe8ff2d53eb6d86f3aa658fe2f702bcf8474c51` |
| Questions | `questions.json` | `343bfcd054725e8cb8581dc39d10dad10514b1f9b54fea4fadbb7ba55a06f2a2` |
| v2 golden cases | `golden_cases.json` | `9b29d230dd47282f63a462237aa169c0704c5321ec7e4fef8de0e797deb793f2` |
| v2 golden tests | `tests/test_scorer_golden.py` | `383aa3afa4686fdb103e3eaa8dbc6fc423f1c3bea28b8b603c18365c554cd124` |
| Response file (5 models x 52 questions, greedy, 8,192 tokens) | `results/baseline_run_8192_20260621_191310.json` | `af9a55eb43a314f40f5b3fad734fa0462713a9e14ac936fa05d080ac9fafc884` |
| v2 scores of the frozen response file | `results/scored_20260621_221729.json` | `424497bc8d6e8f8aef291e4584d0a0f9ab8e7cd336337becee74e026dc7ec81f` |
| IYRA v10 replication response file | `results/v3_run1_iyra_v10_replication.json` | `858b14bcac4fd33c08b6bea516139e5a3d3949a35e801874720a80677d24c1b4` |
| IYRA v11 response file | `results/v3_run2_iyra_v11.json` | `674f630623bb356632d086311f38b47afde98dc5dd18b7b8a5663576627aae65` |
| Base weights at Q6_K | `Qwen3-14B-Q6_K.gguf` from the Hugging Face repository `Qwen/Qwen3-14B-GGUF`, revision `530227a7d994db8eca5ab5ced2fb692b614357fd`, 12,121,937,248 bytes | `ec1f1d1421d7636a23e17645cac6fda39ee4b5f1f11e42eb09238089705ef699` (as published; the copy in `models/gguf/` matched it on 12 November 2026) |
| Base Q6_K response file, IYRA system prompt | `results/v3_run3_qwen3_14b_q6k_iyra_system.json` | `90d929ea286bc0882c979506efdc50925132d3ef9430d9d83dd5402d6eacb928` |
| Base Q6_K response file | `results/v3_run4_qwen3_14b_q6k.json` | `cb74faf923c9bb4b0b7bcfc5de5c1b3b2fb397582edf1422ffec6c682c6fd9c4` |

v3 scores five files and nothing else: the frozen response file, the v10 replication file, the declared v11 file and the two base files of runs 3 and 4, in one single run (section 13, step 10). The IYRA version in the frozen file is v10.

**Two facts about the frozen file.**

- Gemini key. The Gemini rows carry the key `gemini-1.5-pro`. The model string sent was `google/gemini-2.5-pro`. `run_baselines.py` has a single commit in its history (18 June 2026); that commit maps the key `gemini-1.5-pro` to `google/gemini-2.5-pro` with the label "Gemini 2.5 Pro", the working file is identical to it, and the frozen file's own metadata records the same string. The key and one docstring line are left over from an earlier model choice. Git confirms the string the script sent. It cannot confirm what the provider served, because the provider's response model field was not saved.
- Runner. The frozen file's metadata records 8,192 new tokens and a context of 12,288. The tracked `run_baselines.py` sends 2,048 new tokens and no context setting, and writes a different file name. The runner that produced the frozen file is not in git and is not on disk. Its settings are known only from the file's metadata.

**The stored v11 number.** The stored summary (`results/bench_greedy_v11.json`, bench 81.6) was produced on 5 July 2026 by `bench_greedy_v11.py`, an untracked script. It imports the system prompt, endpoint and timeout from `run_baselines.py`, builds the same prompt string with thinking off, and sends the settings recorded in the frozen file (temperature 0.0, top_p 1.0, 8,192 new tokens, context 12,288). It differs from the tracked `run_baselines.py` call path in four ways:

1. New tokens: 8,192, where the tracked script sends 2,048.
2. Context: 12,288 sent explicitly, where the tracked script sends none and the model file default (4,096) would apply.
3. No retry: one call per question, where the tracked script retries twice and records an error.
4. Output: per-question v2 totals in `results/bench_greedy_v11.log` and a summary; no raw responses, token counts or latencies.

**Four declared generation runs, one runner.** All four runs use the reconstructed runner: the `run_baselines.py` call path (prompt string, system prompt, endpoint, thinking off, retry wrapper, record fields) with the settings recorded in the frozen file's metadata (temperature 0.0, top_p 1.0, 8,192 new tokens, context 12,288). The reconstructed runner is committed before run 1 and is not changed between the runs. All four runs are made under one Ollama version, which is recorded for each. The frozen file does not record the Ollama version used on 21 June 2026.

**Run 1: runner replication check (IYRA v10).** Made after the spec commit and before run 2.

- `iyra-v10-q6` is not registered in Ollama as of 12 November 2026. It is re-created from the stored files in `models/gguf/`: the GGUF `iyra-v10-q6_k.gguf` and the model file `Modelfile.iyra-v10-q6`, both dated 14 June 2026. The SHA-256 of each is recorded with the result.
- The reconstructed runner is run once on the 52 questions for IYRA v10. The raw responses are saved to a new file, and its SHA-256 is recorded in the table above.
- Reported in every case: the number of the 52 responses that are byte-identical to the IYRA v10 responses in the frozen file.
- The word "replicated" is used only if 52 of 52 responses are byte-identical. Otherwise the report gives the byte-identical count, the v2 bench of the replication file beside 80.3, and the number of pass or fail changes, with no label. For every response that is not byte-identical, its v2 per-question total from unchanged `evaluator.py` is listed beside the total stored in `results/scored_20260621_221729.json`.
- The result is reported whatever it is and is printed with the v3 tables (section 10).
- The v10 replication file is an input to v3 and is scored in the same single run as the other four files (section 13, step 10). The v10 against v11 comparison uses the replication file and the v11 file, which share a runner and an Ollama version. The frozen v10 row stays in the table beside the baselines, and both v10 rows are printed.

**Run 2: declared v11 generation run.** After run 1, under the same Ollama version, and before any v3 scoring, IYRA v11 (`iyra-v11-cont2-2ep-q6`) is run once on the 52 questions with the same reconstructed runner. Then:

- The raw responses are saved to a new file. Its SHA-256 is recorded in the table above before scoring.
- The v2 bench on the new file is computed with unchanged `evaluator.py` and compared with the stored 81.6, and the per-question v2 totals are compared with the stored log. Every difference is reported, whatever it is.
- v11 is scored by v3 in the same single run as the other four files (section 13, step 10).

**Run 3: base at matched quantisation, with IYRA's system prompt.** Made after run 2, with the same reconstructed runner, settings and Ollama version as runs 1 and 2.

- Weights: `Qwen3-14B-Q6_K.gguf` from `Qwen/Qwen3-14B-GGUF`, identified by the SHA-256 in the table above.
- An Ollama model is created from those weights with the template and parameters of Ollama's `qwen3:14b` (as registered on 12 November 2026: repeat penalty 1, temperature 0.6, top_k 20, top_p 0.95, stop tokens `<|im_start|>` and `<|im_end|>`), except that the system prompt and the repeat penalty (1.1) are taken from `Modelfile.iyra-v10-q6`. Thinking is switched off by the request, as for the frozen base rows. The model file used is saved with the response file, and its SHA-256 is recorded.
- The v10 and v11 model files carry the same system prompt, parameters and template; they differ only in the weights file they name (checked on 12 November 2026). Run 3 therefore matches the system prompt of both IYRA rows.
- The reconstructed runner is run once on the 52 questions. The raw responses are saved to a new file, and its SHA-256 is recorded in the table above before scoring.
- The file is scored by v3 in the same single run as the other four files, as the row "Qwen3-14B base Q6_K, IYRA system prompt".

**Run 4: base at matched quantisation, without IYRA's system prompt.** Made after run 3, with the same reconstructed runner, settings and Ollama version.

- The same weights, template and parameters as run 3, with no system prompt in the model file and with repeat penalty 1. The model file used is saved with the response file, and its SHA-256 is recorded.
- The reconstructed runner is run once on the 52 questions. The raw responses are saved to a new file, and its SHA-256 is recorded in the table above before scoring.
- The file is scored by v3 in the same single run as the other four files, as the row "Qwen3-14B base Q6_K".

For runs 3 and 4, the number of responses that contain a think block is reported.

Purpose of runs 3 and 4: the IYRA v10 replication row against the run 3 row shows the effect of the fine-tune, at the same quantisation type and with the same system prompt. The run 3 row against the run 4 row shows the effect of IYRA's system prompt and repeat penalty.

Runs 1 to 4 are the only generation runs that are part of v3.

## 3. Scope

Matching defects, numbered as in the 11 November 2026 audit. Each was reproduced against unchanged `evaluator.py`.

| ID | Defect in v2 | Where | In v3 |
|---|---|---|---|
| B2 | Indic-script name lists are short and were taken from one model's answers. Correct citations such as a Devanagari, Gurmukhi or Tamil spelling of Kant, Hume, Shankara, Kumarila or Aristotle do not match. Inflected Tamil forms do not match (KI-1). | `NAMED_PHILOSOPHERS`, `NAMED_SCHOOLS` | yes in Latin script; in Devanagari and Gurmukhi, by full label for every listed person and by short form for the reviewed set (4.3); in Tamil, by full label and benchmark string only. Inflected Tamil forms (KI-1) and Tamil short forms are **deferred to v3.1** |
| B3 | Latin-script names match inside other words ("chosen", "lessen", "windmill", "exhume") and as ordinary words ("street", "ruse", "crane"). | `NAMED_PHILOSOPHERS` | yes |
| B4 | D4 for Hindi, Punjabi and Tamil divides by non-ASCII characters only, so an English answer containing one Indic word scores 1. | `score_language_consistency` | yes |
| B5 | Six Tamil step names sit inside the Siddhanta list, so Siddhanta is reported present when it is absent, and an answer with transliterated Tamil headers scores D1 = 0. | `NYAYA_STEPS` | yes |
| B6a | No Unicode normalisation: the same answer in NFD form scores differently. | module level | yes |
| B6b | Eight label patterns of the form `\bword:\b` cannot match "Word: text". | `NYAYA_STEPS` | yes |
| B6c | The Tamil back-reference list matches almost no Tamil Siddhanta: on the frozen file the Siddhanta header is found in 10 of 10 Tamil answers for every model, and a back-reference pattern in at most 1 of 10. | `SIDDHANTA_BACKREF` | **deferred to v3.1** |
| B7 | The Hindi and Punjabi back-reference lists do not cover the same slots as the English list (the English list contains "however"; the Hindi and Punjabi lists contain no equivalent of the common word for "but"), and their entries coincide with opener phrases in one model's training data. | `SIDDHANTA_BACKREF` | yes, new in scope |

Not in scope: any change to D3 logic (section 5), to the D2 score ladder, to thresholds, or to the questions.

## 4. Name lists (B2, B3)

### 4.1 One canonical list, from a stated source (decided: Wikidata)

v3 uses a single canonical table with three parts: persons, schools or traditions, and texts. Every entry records its Wikidata identifier. Nothing in the table is taken from any answer file, any model output, or any earlier ad hoc list.

**Rule 1.** A dated Wikidata export.

- Persons: every item that is an instance of (P31) human (Q5), has occupation (P106) philosopher (Q4964182), and has at least N sitelinks. The occupation set is philosopher only (decided). Sitelinks are counted as Wikidata's own `wikibase:sitelinks` value, which covers all Wikimedia projects.
- Schools: every value of movement (P135) on an included person.
- Works: every value of notable work (P800) on an included person. Works are recorded for a later version and are not matched by v3 (see 4.3).
- The six identifiers above were checked against live Wikidata on 12 November 2026.
- The export is one dated query result, saved to disk with its query text and row counts, and fetched with a descriptive User-Agent. The table is built from that saved file only.

**Rule 2.** Every name in the `expected_purvapaksha_sources` field of `questions.json`, which was published with the benchmark at v1.0. That field holds 127 distinct strings: 103 person strings for 63 distinct persons, and the rest schools and one text. A name that enters by rule 2 is in the table for every question, not only for the question that lists it.

- The 63-row mapping from the expected strings to Wikidata items is approved by Gursimran as shown on 12 November 2026 (mapping file SHA-256 `587daa73d570c573c0105b083bf0e127b0952c3ff13a98f7fdbc8d11d0cf83c3`; it is published with the provenance file). Labels of rows marked H or D are reviewed with the Hindi and Punjabi forms in step 7 of section 13.
- H marks a row where the item was selected by hand: Q287357, Q2743779, Q774847, Q107348453, Q9391, Q189725, Q1741798. D marks a row whose item data needs a check: Q2671506, Q107348453.
- **Author-supplied forms.** For the 63 expected persons, where a script has neither a benchmark string nor a Wikidata label, Gursimran may supply a Hindi or Punjabi form. Each such form is marked author-supplied in the coverage table, and it is proposed by a session with no access to any answer file. No Tamil form is supplied this way.

**N = 10.**

| N | Persons on the list (rule 1) | Expected persons included by rule 1 alone, of all 63 | Of the 54 who carry the occupation |
|---|---|---|---|
| 5 | 9,053 | 53 (84.1%) | 53 (98.1%) |
| 10 | 4,980 | 51 (81.0%) | 51 (94.4%) |
| 20 | 2,447 | 46 (73.0%) | 46 (85.2%) |
| 40 | 1,033 | 31 (49.2%) | 31 (57.4%) |

Counts were taken on 12 November 2026 without printing or inspecting any name for inclusion. All humans with the occupation philosopher, at any sitelink count: 45,384. Counts of schools and works were not obtained and are recorded in the provenance file at export time.

- Original rule (12 November 2026): N is the largest value in {5, 10, 20, 40} at which rule 1 alone includes at least 90% of the 63 expected persons. It produced no N. The best was 84.1% at N = 5, and only 54 of the 63 carry the occupation philosopher at any sitelink count.
- Amendment (12 November 2026, Gursimran Singh): the 90% test is computed over the 54 expected persons who carry the occupation, because N cannot recover a person the occupation filter excludes. Result: N = 10, which includes 51 of 54 (94.4%). N = 20 includes 46 of 54 (85.2%).
- List size at N = 10: 4,980 persons. The dated export fixes the final number.
- The 12 expected persons that rule 1 misses at N = 10 enter by rule 2 and match on any question.

The v2 Latin-script list is not carried over as a source. Its entries survive only where rule 1 or 2 produces them. The list of v2 names that rules 1 and 2 drop is not computed, printed or inspected before the table is built (section 13, step 7).

### 4.2 Forms (decided: Wikidata labels only)

Forms come from Wikidata labels only. No alias is used, in any language: some Wikidata aliases are descriptions, not names (Q774847 and Q9045 carry such aliases).

For each entry:

1. Latin script: the English label and the "mul" label, each used verbatim.
2. Devanagari: the Hindi label. Gurmukhi: the Punjabi label. Tamil: the Tamil label. Each is used verbatim.
3. Where the item has no label in a script's language, no form is created in that script from Wikidata. The name matches there only by a benchmark string (4.1, rule 2) or an author-supplied form (4.1), and otherwise in Latin script only. Every such gap is listed in a coverage table published with the results.

**Transliteration by tool is removed from v3.** An earlier draft transliterated a Hindi or Sanskrit label into a missing script with a pinned tool. On 12 November 2026 the proposed tool (Aksharamukha 2.3) was run at default settings on the 63 expected persons and produced 14 forms, 9 in Gurmukhi and 5 in Tamil. None of the 14 matched an expected string. Four could be compared with a benchmark string for the same person and script, and all four differed from it; the Gurmukhi output kept conjuncts that ordinary Punjabi spelling does not write, and two of the five Tamil forms carried superscript digits. v3 therefore contains no transliteration, by tool or by rule, in any direction. The only forms that come neither from Wikidata nor from the benchmark are the author-supplied forms of 4.1.

Spelling variants are then generated by fixed rules, for Devanagari and Gurmukhi forms only:

- Devanagari: anusvara and the homorganic nasal with virama are interchangeable; chandrabindu and anusvara are interchangeable; nukta is optional; dental and retroflex stops are interchangeable in names of non-Indic origin.
- Gurmukhi: tippi and bindi are interchangeable; addak is optional; the subscript dot is optional; dental and retroflex stops are interchangeable in names of non-Indic origin.

**Tamil: no hand-written linguistic rule in v3.** Tamil forms are the Wikidata Tamil labels, verbatim, and the benchmark's own Tamil strings. Nothing else: no aliases, no short forms (4.3) and no author-supplied forms, because no fluent reader reviews them. The Tamil variant rules (Grantha substitutes, the three n letters, the optional honorific or gender ending, and case-suffix stem handling) are deferred to v3.1 under the tie-break rule (section 13). KI-1 stays open and is footnoted on every table.

Review:

- Hindi and Punjabi forms, short forms (4.3) and variants are reviewed by Gursimran, without reference to any answer file. The reviewer may remove a wrong form. The reviewer may not add a form because a model wrote it.
- Tamil forms are not reviewed by a fluent reader in v3. Every v3 table says so (section 10).

### 4.3 Matching rules

- A bracketed part of a label is dropped in every script before any form is taken from it.
- Latin-script names match on whole words only, with a word boundary on both sides.
- For Latin matching only, diacritics are folded on both the form and the answer: the text is decomposed (NFD) and combining marks are removed, so "Gödel" and "Godel" match. Letters that do not decompose, such as "ø", stay as they are. Indic matching uses the answer without folding.
- **Short forms, Latin.** For every listed person, the last word of each Latin label is also a form. A label that contains " of " or " the " gets no short form. A Latin short form must have at least three letters and contain a lowercase letter; otherwise the label gets no short form. The ambiguity rule in the next line applies to short forms.
- A Latin-script surname that is also in the English word list below is ambiguous. It matches only when preceded by a given name or initials from its source record, or when capitalised and not sentence-initial.
- The English word list is SCOWL size 60: the union of the `english-words` and `american-words` lists at sizes 10, 20, 35, 40, 50, 55 and 60 from the Ubuntu `scowl` package, version 2020.12.07-2 (package file SHA-256 `e7982d627a52b45c254e41ebbb7c937321d232988f2c8264917cc7ae793aeba0`). Lowercase entries only, meaning entries made only of the letters a to z: 77,092 entries. The Ubuntu `wamerican` package was checked and is not used: version 2020.12.07-2 is built from sizes 10 to 50 only.
- Indic forms match at a word start. Forms shorter than four letters match only as a complete word. This rule is the same for all three scripts and is the only matching rule applied to Tamil forms. A Tamil name whose case ending alters the last letter of the label does not match (KI-1, open).
- **Short forms, Devanagari and Gurmukhi.** The last word of the Hindi label, and of the Punjabi label, is also a form, but only for the reviewed set: the 63 expected persons and the 150 listed persons with the most sitelinks in the dated export (ties at the cut are broken by the lower Wikidata identifier number). Every such form is read by Gursimran, who may strike a form and may not add one because a model wrote it. Every other listed person matches in these scripts by verbatim label only.
- **Tamil has no short forms in v3.** A Tamil citation matches by the verbatim Tamil label or by one of the benchmark's own strings, and by nothing else.
- Each `expected_purvapaksha_sources` entry carries the forms of its person in all four scripts under 4.1, 4.2 and this section, so a correct citation scores the same in any script where a form exists.
- **Texts are credited exactly where v2 credits them. No tier change.** In v2 a text earns D2 credit only when its title is one of the question's own `expected_purvapaksha_sources` strings (`evaluator.py` lines 268 to 270). Any expected string found in the Purvapaksha section, whether a person, a school or a text, counts at the named tier (line 277). v2 has no general text list, and D5 does not use texts. v3 keeps all of this.

## 5. D3: name and reporting only

- The scoring logic of D3 is unchanged from v2 (the D3 function, `evaluator.py` lines 305 to 347). v3 D3 must equal v2 D3 on every input.
- D3 is renamed **"Confidence tag"**. The v2 name, and the word it contains, are not used in v3 output, tables, documentation or identifiers. The v3 output key is `confidence_tag`.
- The legend printed under every table states exactly what the three values mean:
  - 0: no confidence tag and no hedge word.
  - 1: a hedge word with no tag; or the tag HIGH on a question in a domain the scorer lists as speculative; or the tag LOW on a question in a domain the scorer lists as evidence-based.
  - 2: any other tag (HIGH, MEDIUM, LOW or NONE).
- The legend also states: a model that writes the same tag on every answer can score 2 on every answer; D3 does not test whether the stated confidence is right.
- Every v3 table shows bench with D3 (out of 9) and bench without D3 (out of 7), side by side.
- The 0 to 2 scale and the 6/9 pass threshold stay as published. Pass is always computed with D3 included.

## 6. D4: language ratio over all letters (B4)

- A letter is a code point with Unicode general category L or M, counted after normalisation (section 8). Marks are counted because Brahmic vowel signs and the virama are marks. Digits, punctuation, symbols and whitespace are not letters.
- Hindi, Punjabi, Tamil: score 1 when letters in the expected script block are at least **0.50** of all letters.
- English: score 1 when Latin-script letters (including the diacritics used in IAST) are at least **0.70** of all letters.
- An answer with zero letters scores 0 in every language.
- Both thresholds were fixed on 11 November 2026 without reference to any answer file. They may be changed before approval and not after.
- Limitation: this checks script, not language.

## 7. Tamil, and the Hindi and Punjabi back-reference lists

### 7.1 Tamil step names (B5): in v3, as a restructure only

- Each of the seven steps has its own Tamil list. The six step names now inside the Siddhanta list are removed from it and placed under their own steps.
- Each step accepts: the Tamil translation already in v2; the transliterated step name already in v2 (the six moved entries, and the existing Siddhanta entries); and the Latin or IAST form as in v2. No new Tamil form is written by hand.
- The same per-step Tamil lists are used for D1 presence and for the D2 section boundaries, so a header that counts for D1 also delimits a section.
- Tamil names and Tamil header lists stay in v3. They are not reviewed by a fluent reader, and every v3 table carries the footnote "Tamil names and headers: not reviewed by a fluent reader."

### 7.2 Tamil D5: deferred to v3.1

- The Tamil back-reference patterns (B6c) and the variant rules for the Tamil D5 vocabulary are deferred to v3.1, pending a fluent Tamil reviewer.
- In v3, D5 for Tamil questions is computed by the unchanged v2 D5 function on the raw answer, with the v2 patterns and the v2 name lists. v3 Tamil D5 therefore equals v2 Tamil D5 for every answer.
- Every table in a v3 report carries the footnote "Tamil D5 is not valid for any model."

### 7.3 Hindi and Punjabi back-reference lists (B7): in v3, new in scope

- The v2 Hindi and Punjabi back-reference lists are replaced, not extended.
- The new lists are built by translating the published English back-reference list slot by slot into Hindi and into Punjabi, then applying the variant rules in 4.2. A v2 entry survives only where the translation produces it.
- Translation, variants and golden cases are reviewed by Gursimran, without reference to any answer file.

## 8. Normalisation and label patterns (B6a, B6b)

- Every answer and every pattern source string is converted to Unicode NFC before matching.
- Zero-width characters (U+200B, U+200C, U+200D, U+2060, U+FEFF) are removed from both, for matching only. Approved.
- Exception: Tamil D5 runs the v2 function on the raw answer (7.2).
- The eight label patterns (`claim`, `reason`, `example`, `application`, `conclusion`, `objection`, `response`, `refutation`) become: the label as a whole word, optional whitespace, then a colon, with no boundary required after the colon.

## 9. Golden tests

Rules:

1. Expected scores are proposed with one line of reasoning each and are verified by hand by Gursimran before any assertion is written. Hindi and Punjabi cases are reviewed by Gursimran without reference to any answer file. Tamil cases are marked "not reviewed by a fluent reader".
2. Red first: each new test is run against unchanged `evaluator.py` and must fail. The command, the commit hash and the output are saved in `tests/red_logs/`. A test marked "v3-only" checks a guard that v2 already satisfies or cannot express; it is exempt from red first, and its v2 result is recorded all the same.
3. The existing 17 cases and 41 tests keep running against `evaluator.py` and must stay green.
4. v3 has its own test file. If any existing golden case scores differently under v3, the case, both scores and the reason are listed before v3 is run on real answers.

| Test | Defect | Case | v2 today | v3 expected |
|---|---|---|---|---|
| GV3-01 | B2 | Hindi, Punjabi and Tamil twins of one English answer, each citing the same listed philosopher in its own script; the Tamil twin uses the Wikidata Tamil label unchanged | Indic twins score lower on D2 than the Latin twin | all four twins equal on D2 |
| GV3-02 | B2 (KI-1) | Moved to v3.1 with the Tamil variant rules | n/a | n/a |
| GV3-03 | B3 | English Purvapaksha of 30 words containing "chosen", "street", "ruse", "lessen", "windmill", "exhume" and no philosopher | D2 = 3 | D2 per rubric with no named source |
| GV3-04 | B3 | Positive control: full names of three listed philosophers whose surnames are ordinary words | named | still named |
| GV3-05 | B4 | English answer to a Hindi question containing one Devanagari word; plus one case just above and one just below each threshold | D4 = 1 | D4 = 0; boundary cases as specified |
| GV3-06 | B5 | Tamil answer with all seven headers in the transliterated forms already present in v2 | D1 = 0 | D1 = 1 |
| GV3-07 | B5 | Tamil answer with six steps and no Siddhanta | Siddhanta reported present | Siddhanta absent, D1 = 0 |
| GV3-08 | B6a | One English answer stored in NFC and in NFD; one Hindi answer with and without zero-width characters | scores differ | scores equal |
| GV3-09 | B6b | English answer using only "Claim:", "Reason:", "Example:", "Application:", "Conclusion:", "Objection:", "Response:" | D1 = 0 | D1 = 1 |
| GV3-10 | B6c | Moved to v3.1 with Tamil D5 | n/a | n/a |
| GV3-11 | D3 | Invariance check, exempt from red first: v3 D3 equals v2 D3 on every golden case and on constant NONE, MEDIUM, HIGH, LOW, no tag, hedge word only | n/a | equal on every input |
| GV3-12 | Tamil D5 | Invariance check, exempt from red first: v3 D5 equals v2 D5 on every Tamil golden case | n/a | equal on every input |
| GV3-13 | B7 | Hindi and Punjabi Siddhanta that answers the objection using the translated equivalent of an English slot the v2 list lacks; twin with no back-reference | both D5 = 0 | first D5 at least 1, twin D5 = 0 |
| GV3-14 | B2, Latin short form | Red first. English Purvapaksha citing, by the last word of the label alone, a listed philosopher whose name is not in the v2 list | not named | named |
| GV3-15 | B2, diacritic folding | Red first. Twin answers citing a listed philosopher, not in the v2 list, whose label carries a diacritic: one twin writes the diacritic and one does not | neither named | both named, equal D2 |
| GV3-16 | Short form, " of " and " the " | v3-only. An answer whose only candidate is the last word of a label that contains " of " or " the ", with no philosopher cited | not named | not named |
| GV3-17 | Bracket dropping, Gurmukhi | v3-only. Two Punjabi answers built on a Punjabi label that has a bracketed part: one contains only the bracketed word, one cites the name without the bracket | recorded | first not named, second named |
| GV3-18 | Short form, minimum | v3-only. One answer whose only candidate is a one-letter or two-letter last word of a listed label, and one whose only candidate is a last word written wholly in capitals | not named | not named |
| GV3-19 | B2, Devanagari short form, reviewed set | Red first. Hindi answer citing, by the last word of the Hindi label alone, a person in the reviewed set whose Devanagari form is not in the v2 list | not named | named |
| GV3-20 | Devanagari short form, outside the reviewed set | Two answers about one listed person outside the reviewed set. Red first: the full Hindi label is cited. v3-only: only the last word of the label is cited | neither named | full label named; last word alone not named (section 12) |

The persons used in GV3-14 to GV3-20 are chosen when the golden cases are authored (section 13, step 8), from the built name table.

## 10. Reporting

- The published v2 table is copied exactly from the published source under the heading **"Published: evaluator v2, unchanged"**. It is always shown with the v3 tables and never merged with them.
- **Every v3 report prints three v3 tables, together:** all 52 questions; without tier 1 (37 questions); without tiers 1 and 2 (19 questions). The tiers are defined below.
- Rows in each v3 table: the five models of the frozen response file, with IYRA v10 as in that file; IYRA v10 from the replication file (section 2, run 1); IYRA v11 from the declared run (section 2, run 2); "Qwen3-14B base Q6_K, IYRA system prompt" (section 2, run 3); and "Qwen3-14B base Q6_K" (section 2, run 4). The number of run 3 and run 4 responses that contain a think block is printed with the tables. The frozen v10 row stays in the table beside the baselines, and both v10 rows are printed. The v10 against v11 comparison uses the replication row and the v11 row, which share a runner and an Ollama version.
- v3 table columns: pass as a fraction of the questions in the table; bench out of 9; bench without D3 out of 7; D1 to D5 means; per-language pass as fractions with the denominators that remain (table of remaining questions below). No per-language percentages. No per-language claim is made from the 19-question table; its per-language passes are still printed as fractions.
- **Exclusion tiers.** Both tiers are frozen on 12 November 2026 (Gursimran Singh) and are not changed after that.
  - **Tier 1, 15 questions.** Basis: a rule match, a translation of a rule match, or near-identical wording of a training question, confirmed by Gursimran.

    | Family | Bench IDs | Detail |
    |---|---|---|
    | Consciousness and brain states | NB-001, NB-011, NB-021, NB-031 | NB-001 matches by the rule (ratio 0.86). For v10 the matching training question sat in a field of the training file that the v10 training script does not read, so it was not shown to v10 as a question, though the answer in that row was trained. It is in the shipped v5 mix as a user turn (row index 428, counted from 0). The other three are its translations; on machine gloss they score 0.51 to 0.56 and do not match by the rule themselves |
    | Mathematical truth | NB-004, NB-030, NB-040 | NB-004 (0.81) and NB-030 (0.80, machine gloss) match by the rule. NB-040 is a translation (0.71, machine gloss) |
    | God by inference | NB-006, NB-013, NB-022, NB-032 | Three match by the rule: NB-013 in the same script (0.80); NB-022 (0.89) and NB-032 (Jaccard 0.64) on machine gloss. NB-006 (English) does not match by the rule (0.64, against the machine gloss of the training question) and is included as the same question |
    | Language and thought | NB-005, NB-014, NB-025, NB-035 | None matches by the rule (0.73 to 0.74). Included as near-identical wording of a training question |

  - **Tier 2, 18 more questions.** Basis: Gursimran judges that a training question asks the same or nearly the same thing, from the question texts alone.

    | Topic | Bench IDs |
    |---|---|
    | Moral realism | NB-003, NB-012, NB-023, NB-033 |
    | Free will | NB-008, NB-016, NB-024, NB-034 |
    | Aesthetic value | NB-010, NB-019, NB-029, NB-038 |
    | Time | NB-015, NB-027, NB-036 |
    | Inference and perception | NB-050 |
    | Vyapti and induction | NB-051 |
    | Padarthas and categories | NB-052 |

  - The stated rule: after normalisation (NFC, case folding, punctuation to spaces, whitespace collapsed), a difflib ratio of at least 0.80 or a word-set Jaccard of at least 0.60. Questions in the same script are compared directly. Across languages, an English gloss is compared; the glosses used so far are machine glosses, and the Tamil glosses are not reviewed.
  - The stated rule compares strings and ranks a paraphrase low. On 12 November 2026 a keyword search, not exhaustive, found a training question that asks the same or nearly the same thing for 18 of the 37 questions outside tier 1, and a related but different question for 10 more. The rule matches none of them. The 18 form tier 2.
  - `questions.json` has no field that links a question to its translations. Families are therefore listed here by ID and confirmed by Gursimran.
  - Questions that remain in each table:

    | Table | English | Hindi | Punjabi | Tamil | Total |
    |---|---|---|---|---|---|
    | All 52 | 22 | 10 | 10 | 10 | 52 |
    | Without tier 1 | 18 | 7 | 6 | 6 | 37 |
    | Without tiers 1 and 2 | 12 | 3 | 2 | 2 | 19 |

    The 19: English NB-002, NB-007, NB-009 and NB-041 to NB-049; Hindi NB-017, NB-018, NB-020; Punjabi NB-026, NB-028; Tamil NB-037, NB-039.
  - Training question text is not reproduced in this file.
- The result of the runner replication check is printed with the v3 tables, worded as section 2, run 1 requires.
- Footnotes on every table in a v3 report: the D3 legend (section 5); "Tamil D5 is not valid for any model."; "Tamil names and headers: not reviewed by a fluent reader."; "Tamil names with case endings may not match (KI-1, open)."
- Paired bootstrap on bench, for IYRA minus Gemini, IYRA minus Claude and IYRA minus Qwen3-14B, where IYRA is the frozen v10 row: resample the question IDs with replacement, use the same resampled IDs for both models, 10,000 resamples, seed 20261111, percentile 95% interval. Reported for all three v3 tables, with D3 and without D3, with the point estimate.
- The same paired bootstrap, with the same method and seed, is reported for IYRA v11 minus the IYRA v10 replication row, for all three v3 tables, with D3 and without D3, with the point estimate.
- The same paired bootstrap is reported for the IYRA v10 replication row minus the run 3 row (the effect of the fine-tune), and for the run 3 row minus the run 4 row (the effect of the system prompt), for all three v3 tables, with D3 and without D3, with the point estimate.
- The interval reflects sampling of questions only. It does not cover run-to-run generation variance (one greedy run per model) or scorer validity. This sentence is printed with the interval.
- **Noise floor.** The noise floor is the larger of 2 questions and the number of pass or fail changes between the frozen v10 row and the v10 replication row (section 2, run 1). A pass-count difference between two rows at or below the noise floor is reported and is not interpreted as a difference. The same count applies in all three tables.
- The coverage table from 4.2 and the list of dropped v2 names from 4.1 are published with the results. The coverage table marks every author-supplied form (4.1) and every short form that was struck in review (4.3).
- **The frozen response file is published with v3**, byte-identical and identified by its SHA-256. The scan of 12 November 2026 was clean: no keys, tokens, HTTP headers, file paths, e-mail addresses, URLs or host names; the stored system prompt is identical to the one in the tracked `run_baselines.py`; no response text is shared with the private results folder. The Gemini key (section 2) is published as it stands and explained in the README.

## 11. Decisions

Recorded on 12 November 2026 (Gursimran Singh):

| Topic | Decision |
|---|---|
| Name source | Wikidata; one dated query result saved to disk, fetched with a descriptive User-Agent (4.1) |
| Occupation set | Philosopher (Q4964182) only (4.1) |
| N | 10. The original 90% test over all 63 expected persons produced no N; the amended test over the 54 who carry the occupation gives N = 10 (4.1) |
| Expected-string mapping | The 63-row mapping is approved as shown on 12 November 2026. Labels of rows marked H or D are reviewed with the Hindi and Punjabi forms in step 7 (4.1) |
| Forms | Wikidata labels only; no aliases in any language; Latin forms from the English and "mul" labels; transliteration by tool removed (4.2) |
| Short forms | A bracketed part of a label is dropped in every script. Latin: the last word of the label, for every listed person, with diacritics folded, no short form for a label containing " of " or " the ", at least three letters with a lowercase letter among them, and the ambiguity rule applied. Devanagari and Gurmukhi: the last word of the label, for the reviewed set only (the 63 expected persons and the 150 listed persons with the most sitelinks), each form read by Gursimran. Tamil: none (4.3) |
| Author-supplied forms | Hindi or Punjabi only, for the 63 expected persons only, where a script has neither a benchmark string nor a Wikidata label; marked in the coverage table; proposed by a session with no access to any answer file (4.1) |
| Tamil | No hand-written Tamil linguistic rule in v3. Labels verbatim, the benchmark's own strings, the script-general word-start match, the header restructure. No aliases, short forms or author-supplied forms. Variant rules and case-suffix handling deferred to v3.1; KI-1 open and footnoted; GV3-02 moved to v3.1 (4.2, 4.3, 7.1) |
| Texts | Credited exactly where v2 credits them; no tier change (4.3) |
| Ambiguous-surname word list | SCOWL size 60, lowercase entries only (4.3) |
| D3 | Renamed "Confidence tag", key `confidence_tag`; legend as drafted (5) |
| Tamil D5 | Deferred to v3.1; v3 Tamil D5 equals v2 Tamil D5; footnoted as not valid (7.2) |
| Hindi and Punjabi back-reference lists | Rebuilt by slot-by-slot translation of the English list; reviewer Gursimran (7.3) |
| Zero-width characters | Removed for matching (8) |
| IYRA v11 | Declared generation run after the spec commit, scored in the same single run (2) |
| Runner replication check | A second declared generation run, for IYRA v10, made before the v11 run with the same reconstructed runner; reported whatever the result and printed with the v3 tables (2, 10, 13) |
| Replication wording | "Replicated" is used only if 52 of 52 responses are byte-identical; otherwise counts are given with no label (2) |
| v10 replication file | An input to v3, scored in the same single run. The v10 against v11 comparison uses the replication file and the v11 file. Both v10 rows are printed (2, 10) |
| Base at matched quantisation | Runs 3 and 4 use `Qwen3-14B-Q6_K.gguf` from `Qwen/Qwen3-14B-GGUF`. Run 3 adds the system prompt and repeat penalty of the IYRA v10 model file ("Qwen3-14B base Q6_K, IYRA system prompt"); run 4 does not ("Qwen3-14B base Q6_K"). Both are scored by v3, and the number of responses with a think block is reported (2, 10) |
| Bootstrap | IYRA minus Qwen3-14B added; IYRA v11 minus the IYRA v10 replication row added; the IYRA v10 replication row minus the run 3 row (effect of the fine-tune) and the run 3 row minus the run 4 row (effect of the system prompt) added; same method, all three tables (10) |
| v2 tier tables | The three tier tables under evaluator v2, unchanged, are computed from the stored v2 scores straight after the spec commit, and again for the new files after the four runs. No v3 rule changes after the spec commit (13) |
| Exclusion tiers | Two tiers, both frozen on 12 November 2026: tier 1 (15 questions) and tier 2 (18 more). Three v3 tables: 52, 37 and 19 questions, with bootstrap intervals for all three (10) |
| Response file | Published with v3; scan clean (10) |
| Tie-break rule | Added, and applied to Tamil D5 and to the Tamil variant rules (13) |

Open:

1. **Reviewer for Tamil in v3.1.** Open. Does not block approval of this spec.

No blocking item remains.

Closed on 12 November 2026:

- The exclusion list (two tiers, section 10).
- **The short-form rule** (4.2, 4.3). Two names-only checks were run on 12 November 2026, with no answer file. Each took the 63 expected persons with Wikidata forms only, without the benchmark's own strings and without author-supplied forms, and tested the 103 expected person strings as if they were answer text.

  "Before" is labels and aliases with no short forms. "After" is the decided rule, before review.

  | Script | Before: persons with a single-word form | Before: strings matched | After: persons with any form | After: persons with a single-word form | After: strings matched |
  |---|---|---|---|---|---|
  | Latin | 30 | 22 of 58 | 63 | 61 | 51 of 58 |
  | Devanagari | 19 | 9 of 16 | 41 | 41 | 8 of 16 |
  | Gurmukhi | 15 | 3 of 13 | 34 | 34 | 3 of 13 |
  | Tamil | 11 | 6 of 16 | 38 | 11 | 6 of 16 |
  | All | | 40 of 103 | | | 68 of 103 |

  - With the benchmark's own strings, which enter by rule 2 of 4.1, all 103 match. The table shows what the Wikidata path gives alone, which is all that every other listed person has.
  - The strings still missed are cases where the label puts the cited name first ("Bharata Muni"), uses another name (Chanakya for Kautilya), is longer than the citation (a label ending in "acharya"), is spelled differently from the benchmark, or does not exist in that language.
  - Four Latin short forms among the 63 are English words (Crick, Pinker, Ruse, Street) and fall under the ambiguity rule.

## 12. Known limitations, listed and not fixed by v3

- **D2 does not verify citations (KI-2).** It scores the presence of a name, not whether the attribution is true.
- **There is no correctness measure.** No dimension checks whether the answer is right or whether the conclusion follows from the steps.
- D3 does not test whether the stated confidence is right (section 5).
- Tamil D5 is not valid for any model, in v2 or in v3 (7.2).
- Tamil names written with a case ending may not match (KI-1). Tamil names and headers are not reviewed by a fluent reader (4.2, 7.1).
- A person who is not a listed philosopher and is not among the 63 expected persons earns no named credit. A scientist cited as the source of an objection is the usual case.
- Sitelink counts under-cover less documented traditions. A philosopher with few Wikipedia articles falls below N whatever their standing in their own tradition.
- D1 looks for step words anywhere in the answer, not only in header position.
- The D2 substance gate is weak: 25 words in the section, or one verb from a short list, is enough.
- The D2 section is cut at the first occurrence of "refut" or "established", which can shorten it.
- An expected school or text found in the Purvapaksha section counts at the named tier, as in v2 (4.3).
- IYRA was fine-tuned on answers written to this rubric. The v2 Hindi and Punjabi back-reference patterns match opener phrases that are present in IYRA's training data. v3 rebuilds those lists from the English list (7.3), but a faithful translation still contains the equivalents of "this objection" and "in response", which that opener uses. Baseline models had no such training.
- Local models and API models were not called through the same message format, and the IYRA model file adds its own system prompt.
- The frozen Qwen3-14B row is Q4_K_M (`qwen3:14b` in Ollama); the IYRA v10 and v11 models are Q6_K. Only the rows of runs 3 and 4 compare IYRA with its base at the same quantisation type. Those runs use a Q6_K file published by the model's authors, while the IYRA files were converted and quantised locally (`scripts/export_v10_gguf.sh`), so the type matches and the conversion does not.
- Indian names match by their Wikidata romanisation. Another romanisation (sh for ś, ch for c), or a citation by the first word of a two-word name, does not match unless the benchmark lists it.
- Indic-script citations of listed persons outside the reviewed set match only by full label (4.3). In Tamil this holds for every person: a Tamil citation matches only by the full Tamil label or by one of the benchmark's own strings.
- Latin short forms are not reviewed. The last word of a label is sometimes a title or a place, not a name (for example the last words of "Bharata Muni" and "Gangesha Upadhyaya"), and it then earns named credit wherever that word appears.
- The runner that produced the frozen response file is not preserved (section 2).
- No v3 comparison of IYRA v10 with IYRA v11 is stronger than the runner replication check allows (section 2, run 1). The comparison uses the v10 replication file and the v11 file. Where the replication file is not byte-identical to the frozen file, the v10 that is compared with v11 is not the v10 whose scores were published, and the gap between the two v10 rows shows the size of the runner and serving effect.
- By the author's reading, 33 of 52 questions ask the same or nearly the same thing as a question in IYRA's training data (section 10, tiers 1 and 2). The baseline models were not fine-tuned on this answer format.
- The 19-question table is not a like-for-like sample of the 52. 9 of its 19 questions are marked hard, against 12 of 52. It has no `nyaya_epistemic` question. Political philosophy (5) and skepticism (4) make up 9 of the 19.
- Conclusions from the 37-question and 19-question tables are drawn from gaps between models on the same questions, not from one model's change in score between tables.
- One greedy run per model, 52 questions.

## 13. Freeze rule, tie-break rule and order of work

**Tie-break rule.** Where the effect of a rule on IYRA is known in advance and the rule cannot be independently reviewed, the rule is deferred to a later version. Applied: Tamil D5 (7.2), and the Tamil variant rules including case-suffix handling (4.2).

Order of work:

1. This spec is approved and signed (top of file).
2. The approved spec is committed. The commit hash is recorded before `evaluator_v3.py` exists. No v3 rule in this spec changes after this commit.
3. The three tier tables (52, 37 and 19 questions) are computed from the stored v2 scores in `results/scored_20260621_221729.json` and reported under the heading "evaluator v2, unchanged".
4. The reconstructed runner is committed. `iyra-v10-q6` is re-created in Ollama, and the runner replication check is made (section 2, run 1). Its result and the Ollama version are recorded before the v11 run.
5. The declared IYRA v11 generation run is made with the same runner (section 2, run 2). The response file is hashed, the Ollama version is recorded, and the v2 bench on the file is compared with the stored 81.6. Then the two base models are created from the Q6_K weights and runs 3 and 4 are made with the same runner (section 2); their model files and response files are hashed. After the four runs, the same three tier tables are computed with unchanged `evaluator.py` for the new files and reported under the heading "evaluator v2, unchanged".
6. The exclusion tiers in section 10 were frozen on 12 November 2026. Nothing is done at this step, and the tiers are not changed.
7. The dated export is saved. The labels of the mapping rows marked H or D, the Devanagari and Gurmukhi short forms of the reviewed set (4.3) and any author-supplied forms (4.1) are reviewed with the Hindi and Punjabi forms. The name table, variant rules and pattern lists are built from the stated sources, reviewed, and committed with the provenance file.
8. Golden cases are authored and their expected scores are verified by hand. The red run against `evaluator.py` is recorded.
9. `evaluator_v3.py` is written and iterated against the golden tests only.
10. When every golden test is green, v3 is run once on the frozen response file, the v10 replication file, the v11 file and the two base files of runs 3 and 4 together, and the three tables are published as produced with the result of the runner replication check. v3 scores of real answers are not viewed before this step.
11. After step 10, no list, pattern or threshold changes. Any later change is v3.1, with its own amendment to this spec, and all earlier tables stay published.

### Prior exposure, disclosed

Known before approval:

- On 11 November 2026 an exploratory rescoring with an ad hoc list of 32 Indic-script names was run on the frozen response file and its results were seen. Those numbers are not v3 results. That list is not an input to v3.
- The per-model D3 breakdown on the frozen file: IYRA v10 wrote NONE on 52 of 52 answers; Gemini 2.5 Pro and Claude Sonnet 4.6 wrote HIGH on 52 of 52; GPT-4o wrote HIGH on 48 and LOW on 4; Qwen3-14B wrote HIGH on 50.
- The Hindi and Punjabi opener overlap: the v2 Hindi and Punjabi back-reference patterns match the Siddhanta opener phrase used in IYRA's training data (present in 710 of 758 Hindi rows and 161 of 238 Punjabi rows of the v10 training file).
- IYRA's Tamil answers use a spelling of the word for "objection" that differs by one letter from the v2 pattern. This is one reason Tamil D5 is deferred.
- In the exploratory rescoring, one IYRA Tamil answer changed score through an inflected name form. This is why the Tamil case-suffix rule is deferred.
- Coverage of the 63 expected persons under rule 1 was computed for N = 5, 10, 20 and 40 before N was fixed (4.1), as counts without names. N was then fixed with those counts in view.
- Twelve surnames used as examples in the audit were checked against an English word list on 12 November 2026.
- The stored per-question v2 totals for IYRA v11 (`results/bench_greedy_v11.log`) exist and were seen on 12 November 2026.
- The exclusion tiers were drawn from question texts after per-question v2 scores on the frozen file had been seen on 11 November 2026.
- The short-form rule (4.3) was chosen on 12 November 2026 after two names-only checks on the 63 expected persons (section 11). No answer file was read for either check.
- Runs 3 and 4 were added on 12 November 2026, after the published v2 scores of every model on the frozen file were known.
- The stored v2 summary scores of the earlier runs (10 to 21 June 2026, each scored with the evaluator of its date) were seen on 12 November 2026, including the Qwen3-14B base at 59.6% pass in the 2,048-token run and IYRA v10 q8 at 80.8% at 8,192 tokens.
- The v2 tier tables (52, 37 and 19 questions) are seen before v3 is built: for the frozen file straight after the spec commit (step 3), and for the new files after the four runs (step 5). No v3 rule changes after the spec commit.
