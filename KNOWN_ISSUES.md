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
