# NyayaBench Scorer — Known Issues

Tracked limitations in `evaluator.py`. These are **not** Latin-only script bias
(that family was swept and fixed); they are residual matching limitations that
can still cost a correct answer points.

---

## KI-1 — Tamil inflected philosopher/school names don't match nominative regex

**Severity:** medium (silently costs the citation point on real Tamil output)
**Status:** open
**Affects:** `NAMED_PHILOSOPHERS`, `NAMED_SCHOOLS` → dimensions D2 (purvapaksha) and D5 (siddhanta)

### What happens
`NAMED_PHILOSOPHERS` / `NAMED_SCHOOLS` list philosopher and school names in their
**nominative (citation) form**, e.g. Tamil `திக்நாகர்`. Tamil is heavily
inflected, so real model output routinely uses case-marked forms:

| form | meaning | matches `திக்நாகர்`? |
|------|---------|----------------------|
| `திக்நாகர்`   | Dignaga (nominative)        | ✅ yes |
| `திக்நாகரால்` | by Dignaga (instrumental)   | ❌ no — `ர`+ā-matra ≠ `ர்`+virama |
| `திக்நாகருக்கு` | to Dignaga (dative)       | ❌ no |
| `திக்நாகரின்` | of Dignaga (genitive)       | ❌ no |

The same applies to Devanagari/Gurmukhi case endings to a lesser degree. When the
name appears only in an inflected form, the citation is **correct** but scores as
if absent — D2 drops 3→2 (or lower) and/or D5 drops 2→1.

### Why it's not in the fixed bug family
This is not English/Latin-only bias — the Indic names *are* present in the regex.
It's an exact-form vs. morphology gap. It was discovered while building the
parity twins (GB-04): the golden answer deliberately uses the bare nominative
`திக்நாகர்` in the siddhanta to sidestep it.

### Workaround (current)
Authoring guidance only: cite names in nominative form. Not enforceable on real
model output.

### Proposed fix (future work)
Match on **stem/prefix** rather than exact nominative — e.g. allow an optional
inflectional tail after the name root (`திக்நாகர்[ஆ-ஃ஀-௿]*`), or
normalise/transliterate before matching. Must be validated against false
positives (a stem too short could match unrelated words). Add golden cases with
inflected forms (instrumental/dative/genitive) once implemented; they should
score identically to the nominative twin.

### Guard
`tests/test_scorer_golden.py::test_sweep_*` lock the nominative path. There is
**no** test asserting inflected forms pass yet — add one with the fix so this
issue closes with evidence.

---

## KI-2: D2 scores the presence of an attribution, not its truth

**Severity:** medium (awards points for citations that may be fabricated)
**Status:** open, recorded for a future benchmark version
**Affects:** dimension D2 (purvapaksha), the "named philosopher cited" and "source text
identified" sub-points

### What happens
D2 awards 1 point for naming a philosopher and 1 point for identifying a source text. The
scorer checks that a name and a title are **present and well-formed**. It does not check
that the philosopher wrote that text, that the text exists, or that it argues what the
response claims. A response that invents a plausible philosopher-text pairing scores the
same as one that cites correctly.

### Why it matters, measured
This is not hypothetical. When the deployed IYRA RAG server was instructed to name a
philosopher and a text in every Purvapaksha, a 10-run sample produced a named text in
**9 of 10** runs and a century in 10 of 10, including two verifiably false attributions:

- "Jayanta Bhatta (11th century CE) argues in Tattvachintamani". The Tattvacintamani is
  Gangesha Upadhyaya's (14th century); Jayanta Bhatta wrote the Nyayamanjari.
- "John Searle argues in Minds, Brains and Science (1980)". Searle's 1980 work is the paper
  "Minds, Brains, and Programs"; "Minds, Brains and Science" is his 1984 book.

Neither pairing occurs anywhere in the v10 training data. A deterministic scan of that
dataset (`argument_audit/verify_training_citations.py` in the GuruAI repo) finds all 12
Tattvacintamani mentions correctly crediting Gangesha or a real commentator, and 10 of 10
sampled philosopher-text pairs factually correct. The model was not reproducing bad
citations from training; it was inventing new ones to satisfy a required slot.

### What changed outside the benchmark
On 27 July 2026 the IYRA server was changed to name no philosopher, text, or century unless
that name appears in a retrieved passage. Measured after the change, named text and century
fell to 0 of 10 with all seven Nyaya steps intact. That fix is server-side only.

**The rubric has not been revised and no results have been rescored.** Published scores
stand as computed.

### Proposed fix (future work)
Split D2's citation point into presence and verifiability: award the structural point as
now, and gate a second point on the cited pairing matching an authority list or appearing
in a retrieved source. Requires an authority table for philosopher-text pairs and a
decision on how to score models that decline to cite rather than cite falsely, which under
the current rubric are penalised identically.

### Guard
No test asserts citation correctness today, only presence. Any fix should add golden cases
with a correct pairing and a fabricated one that must score differently.

### Reference
Argument Audit, 27 July 2026: https://nyayabench.com/argument-audit.html
