# NyayaBench v1.0 — Specification

## Overview

NyayaBench is a standardized benchmark for measuring the quality of **structured epistemic reasoning** in AI systems. It is grounded in the Nyaya philosophical reasoning framework (न्यायदर्शन), the oldest systematic logic school in Indian philosophy, attributed to Aksapada Gautama's *Nyaya Sutras* (c. 2nd century BCE).

Any AI system claiming structured reasoning capability can be evaluated against NyayaBench. The benchmark is model-agnostic, language-agnostic (questions span English, Hindi, Punjabi, Tamil), and domain-agnostic (philosophy, science, ethics, aesthetics).

---

## The Nyaya Reasoning Framework

A complete Nyaya argument consists of five members (*avayava*) of the syllogism (*anumana*), augmented by two dialectical steps:

| Step | Sanskrit | Role |
|------|----------|------|
| 1 | **Pratijña** (प्रतिज्ञा) | The thesis / claim to be proved |
| 2 | **Hetu** (हेतु) | The reason / logical ground |
| 3 | **Udaharana** (उदाहरण) | The general rule illustrated by example |
| 4 | **Upanaya** (उपनय) | Application of the rule to the present case |
| 5 | **Nigamana** (निगमन) | The conclusion / restatement of the thesis |
| 6 | **Purvapaksha** (पूर्वपक्ष) | The prior view / strongest counter-argument |
| 7 | **Siddhanta** (सिद्धान्त) | The established doctrine / refutation of Purvapaksha |

The dialectical pair (Purvapaksha → Siddhanta) distinguishes Nyaya reasoning from bare syllogistic: the arguer must engage the strongest objection before declaring a conclusion.

---

## Scoring Dimensions

Total score: **0–9 per question**. Pass threshold: **≥ 6**.

---

### Dimension 1 — Format Adherence (0–1)

**What is measured:** Whether the response contains all seven Nyaya steps in the correct order, correctly labeled.

**Scoring:**
- **1 point:** All seven steps (Pratijña, Hetu, Udaharana, Upanaya, Nigamana, Purvapaksha, Siddhanta) are present, labeled by name or clear transliteration, and appear in the canonical order (1→2→3→4→5→6→7, with Purvapaksha before Siddhanta).
- **0 points:** Any step is missing, mislabeled, or the order is violated.

**Automated scoring heuristics:**
- Search the response string (case-insensitive) for the following keyword sets:
  - Pratijña: `pratijña`, `pratijñā`, `pratijna`, `thesis`, `claim:`
  - Hetu: `hetu`, `reason:`
  - Udaharana: `udaharana`, `udāharaṇa`, `udaharaṇa`, `example:`
  - Upanaya: `upanaya`, `upanaya`, `application:`
  - Nigamana: `nigamana`, `conclusion:`
  - Purvapaksha: `purvapaksha`, `pūrvapakṣa`, `purvapaksa`, `counter-argument`, `objection:`
  - Siddhanta: `siddhanta`, `siddhānta`, `siddha`, `established view`, `response:`
- All seven keyword sets must match at least once.
- Check positional order: the character index of Purvapaksha match must precede Siddhanta match.
- Award 1 if all conditions met, else 0.

---

### Dimension 2 — Purvapaksha Quality (0–3)

**What is measured:** The depth, specificity, and scholarly grounding of the counter-argument presented.

**Scoring:**
- **0:** No counter-argument present, or the Purvapaksha section is empty / placeholder.
- **1:** Generic counter-argument using phrases like "some argue", "critics say", "opponents claim", "many philosophers believe" — without naming a source, school, or tradition.
- **2:** Named philosophical school or tradition cited (e.g., "Buddhist epistemologists argue...", "The Carvaka school holds...", "Kantian ethics objects...", "The Mimamsa view is...") — without naming a specific philosopher or text.
- **3:** Named philosopher + named text + technical vocabulary from that tradition (e.g., "Dignaga in the *Pramanasamuccaya* argues via *apoha* theory that universals are conceptual constructs, not real entities"). Full scholarly citation at this level earns maximum score.

**Automated scoring heuristics:**
- Check for **generic phrases** (regex): `some argue|critics say|opponents claim|many believe|it is argued|some philosophers`
  - If matched and no named source found → score 1.
- Check for **named schools** (regex, case-insensitive): `buddhist|carvaka|charvaka|mimamsa|mimāṃsā|vedanta|vedānta|nyaya|vaisesika|vaisheshika|jain|advaita|dvaita|kantian|utilitarian|cartesian|stoic|epicurean|analytic|continental`
  - If matched and no named philosopher found → score 2.
- Check for **named philosophers** from `expected_purvapaksha_sources` list in the question JSON, plus a broad list: `dignaga|dharmakirti|nagarjuna|shankara|śaṅkara|ramanuja|rāmānuja|gangesa|gangeśa|udayana|vatsyayana|kant|hegel|mill|hume|descartes|chalmers|nagel|quine|kripke|aristotle|plato|nietzsche|wittgenstein|russell|frege|locke|berkeley|spinoza|leibniz|buddha|jayarasi|kumarila|prabhakara`
  - If matched → score 3 (maximum).
- Return the highest tier matched.

---

### Dimension 3 — Confidence Calibration (0–2)

**What is measured:** Whether the response signals its own epistemic confidence accurately.

**Scoring:**
- **0:** No confidence signal anywhere in the response.
- **1:** Confidence signal is present (e.g., `[CONFIDENCE: HIGH]`, `[CONFIDENCE: MEDIUM]`, `[CONFIDENCE: LOW]`, or hedging language like "I am uncertain", "evidence is sparse") but is not well-calibrated — e.g., HIGH confidence on speculative metaphysical claims, or LOW confidence on well-attested historical facts.
- **2:** Confidence signal is present and accurately calibrated:
  - HIGH only when the claim has textual/empirical evidence.
  - MEDIUM when the claim is philosophically contested but has mainstream support.
  - LOW when the claim is speculative or evidence is weak.

**Automated scoring heuristics:**
- Check for confidence marker pattern (regex): `\[CONFIDENCE:\s*(HIGH|MEDIUM|LOW)\]` or `confidence:\s*(high|medium|low)` (case-insensitive).
  - If no match → score 0.
  - If match found → score 1 (presence confirmed).
- For score 2 (calibration check): apply domain heuristic:
  - If question `domain` contains `history` or `logic` and confidence is HIGH → likely calibrated (score 2).
  - If question `domain` contains `metaphysics` or `consciousness` and confidence is HIGH → likely miscalibrated (score 1).
  - If question `difficulty` is `hard` and confidence is LOW → likely calibrated (score 2).
  - Default: if confidence marker found and domain is `philosophy_of_mind` or `metaphysics` and level is not HIGH → score 2; if HIGH → score 1.
- Note: Full calibration scoring benefits from human review; automated heuristic is approximate.

---

### Dimension 4 — Language Consistency (0–1)

**What is measured:** Whether the response is written in the same language as the question, without mid-response code-switching.

**Scoring:**
- **1:** Response language matches question language throughout (no unexpected switching).
- **0:** Response switches language mid-way (e.g., Hindi question answered partly in English), or response is in the wrong language entirely.

**Automated scoring heuristics:**
- For each question, the `language` field specifies: `english`, `hindi`, `punjabi`, `tamil`.
- Use Unicode block detection on the response text:
  - `english`: response should be predominantly ASCII + Latin (U+0000–U+024F).
  - `hindi`: response should contain Devanagari characters (U+0900–U+097F) comprising ≥ 40% of non-ASCII characters.
  - `punjabi`: response should contain Gurmukhi characters (U+0A00–U+0A7F) comprising ≥ 40% of non-ASCII characters.
  - `tamil`: response should contain Tamil characters (U+0B80–U+0BFF) comprising ≥ 40% of non-ASCII characters.
- Additionally check for **code-switching**: if a non-English question contains > 30% ASCII alphabetic characters (excluding transliterated technical terms), flag as language switch.
- Award 1 if language matches and no code-switching detected, else 0.

---

### Dimension 5 — Siddhanta Quality (0–2)

**What is measured:** Whether the Siddhanta (established doctrine / conclusion) directly engages with and refutes the Purvapaksha objection.

**Scoring:**
- **0:** Siddhanta simply repeats the original Pratijña (thesis) without acknowledging or engaging the Purvapaksha counter-argument.
- **1:** Siddhanta acknowledges the Purvapaksha in general terms ("while this objection has merit, ...") but does not specifically dismantle it with named sources or technical arguments.
- **2:** Siddhanta directly refutes the Purvapaksha with named sources, technical philosophical vocabulary, or logical dismantling of the specific objection raised.

**Automated scoring heuristics:**
- Extract the Siddhanta section (text following the Siddhanta label until end of response or next section).
- Check if Siddhanta text contains **back-reference** to the Purvapaksha objection:
  - Look for phrases: `this objection|the objection|however|nevertheless|despite this|in response|against this view|refuting|the counter-argument|purvapaksha argues|the objector`
  - If no back-reference found → score 0.
- If back-reference found, check for named philosopher or technical term:
  - Reuse the named philosopher regex from Dimension 2.
  - Also check for technical vocabulary: `anumana|vyapti|paksha|sadhya|apoha|svabhavahetu|prasanga|reductio|modus ponens|syllogism|pramana|pratyaksa|inference|valid|invalid|fallacy`
  - If named source or technical vocabulary found → score 2.
  - If only generic back-reference → score 1.

---

## Aggregate Scoring

```
Total Score = D1 + D2 + D3 + D4 + D5
            = (0–1) + (0–3) + (0–2) + (0–1) + (0–2)
            = 0–9 per question

NyayaBench Score = (sum of all question scores) / (9 × N) × 100
                 = percentage of maximum possible score across N questions

Pass threshold per question: ≥ 6 / 9
Pass rate = (questions scoring ≥ 6) / N × 100%
```

A model "passes" NyayaBench if:
1. NyayaBench Score ≥ 67% (average ≥ 6/9), AND
2. Pass rate ≥ 70% (at least 70% of individual questions score ≥ 6).

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-05-30 | Initial release — 50 questions, 5 dimensions, 4 languages |
