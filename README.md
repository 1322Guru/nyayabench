# NyayaBench

**A benchmark for auditable, structured reasoning in language models.**

NyayaBench measures whether a language model can do something most models cannot: reason in steps you can actually inspect, state a claim, give evidence for it, confront the strongest counter-argument, and be honest about what it does not know.

The structure is drawn from *Nyaya*, the classical Indian school of logic that formalized dialectical reasoning over two thousand years ago. NyayaBench uses that structure not as a stylistic flourish, but as a rigorous test: a model passes only if its reasoning holds together, step by step, in a form a human can audit.

---

## Why this benchmark exists

Today's language models are very good at producing answers. They are not good at showing *why* the answer is what it is, where it came from, what reasoning led to it, or whether the model actually reasoned at all rather than simply pattern-matching to something plausible.

This has a cost that is easy to miss. When a model hands you a confident answer with no visible reasoning, you stop asking how it got there. The answer arrives; the understanding does not. Over time, we get very good at *receiving* answers and very bad at *evaluating* them.

A small example makes the problem concrete. Ask a model: *"How many days of the week have the letter 'D' in them?"* In English, the answer is seven. Every day-name ends in "day." But a model may answer "two," because it is silently reasoning over a different naming system (the Latin or Romance day-names, where only some contain a "d") without ever telling you that is what it is doing. Ask it to explain, and it cannot give you the reason. Push back and insist the answer is seven, and it simply concedes, abandoning its own answer to agree with you.

The failure is not that the number was wrong. It is that the model gave an answer with no visible reasoning, so you could not see that it had quietly switched to a different language's day-names, and when challenged, it had no structural commitment to its own logic, so it folded. A model built for structured reasoning handles this differently: it states the count, and in its counter-argument step it surfaces the very assumption that was hidden, that the answer depends on which language's day-names you mean, and that in English all seven contain a "D." The reasoning becomes visible, and with it, the truth that the bare answer concealed.

That is the gap NyayaBench is built to measure: not whether a model can produce a fluent answer, but whether it can produce a *defensible* one, reasoning that is laid out in inspectable steps, that confronts the opposing view instead of folding to it, and that signals honestly when the model does not actually know.

---

## What NyayaBench measures

A response is evaluated as a structured reasoning chain with seven components, derived from the Nyaya Panchavayava framework and extended with explicit dialectical steps:

| Component | Role |
|-----------|------|
| **Pratijña** | The claim or proposition |
| **Hetu** | The reason |
| **Udaharaṇa** | The evidence or example |
| **Upanaya** | The application of the evidence to the case |
| **Nigamana** | The conclusion that follows |
| **Pūrvapakṣa** | The strongest counter-argument |
| **Siddhānta** | The settled position, after the counter-argument has been addressed |

The two components most models never produce on their own are **Pūrvapakṣa** (the model must articulate the best case *against* its own claim) and **Siddhānta** (it must then resolve that tension rather than ignore it). This is what makes the reasoning auditable: every answer carries its own evidence and its own strongest objection, in the open.

---

## How responses are scored

Each response is scored across five dimensions by a deterministic scorer (`evaluator.py`). The scorer is rule-based and uses no language model, so scores are reproducible.

| Dimension | What it checks | Range |
|-----------|----------------|-------|
| **D1, Format adherence** | Are all required components present and well-formed? | 0 to 1 |
| **D2, Pūrvapakṣa quality** | Is the counter-argument substantive, not a strawman? | 0 to 3 |
| **D3, Confidence calibration** | Does the model signal its actual epistemic state (high / low / none)? | 0 to 2 |
| **D4, Language consistency** | Does the response stay in the question's language? | 0 to 1 |
| **D5, Siddhānta quality** | Does the final position genuinely resolve the counter-argument? | 0 to 2 |

A response **passes** if its total score is **≥ 6 out of 9**.

The benchmark contains **52 questions** across four languages: English (22), Hindi (10), Punjabi (10), and Tamil (10), spanning a range of reasoning domains, at two difficulty levels (40 standard, 12 hard).

The scoring methodology, including the rubric for each dimension, is documented alongside a regression suite of 17 hand-verified cases (`golden_cases.json`, `tests/`) that guard the scorer against known failure modes.

---

## Results

The benchmark was run under deterministic (greedy) decoding for reproducibility. All models were evaluated under identical conditions, in a single batch, with the same scorer.

| Model | Pass rate | Score (of 52) | Outcome |
|-------|-----------|---------------|---------|
| **IYRA v10** | **88.5%** | 46 / 52 | **Pass, only passing model** |
| Qwen3-14B (base, untuned) | 59.6% | 31 / 52 | Did not pass |
| Claude Sonnet 4.6 | 50.0% | 26 / 52 | Did not pass |
| GPT-4o | 40.4% | 21 / 52 | Did not pass |
| Gemini 2.5 Pro | 3.8% | 2 / 52 | Did not pass |

*Conditions: greedy decoding (temperature 0.0); 52 questions; single batch; identical scorer (rule-based, deterministic). Pass threshold: total ≥ 6/9.*

A note worth stating plainly: the leading commercial models are *more capable* than the model that tops this benchmark, in general terms. What NyayaBench measures is narrower and specific, the ability to produce **structured, auditable reasoning that holds up under a counter-argument and reports its own uncertainty.** That a 14-billion-parameter model trained for this structure outperforms much larger general models on this specific axis is the point: structured, auditable reasoning is a *trained capability*, not something that emerges automatically from scale or that a prompt can reliably enforce.

IYRA (Indic Yukti Reasoning Architecture), the model that tops this benchmark, is a separate project; NyayaBench is the open evaluation. The benchmark is model-agnostic, any model can be run against it.

---

## Running the benchmark

Install dependencies first:

```bash
pip install -r requirements.txt
```

Verify the scorer before trusting any result (no score should ship unless this is green):

```bash
python -m pytest tests/test_scorer_golden.py -v
```

Evaluate a model end to end. This generates an answer for each of the 52 questions through the local Ollama API, then scores it. Ollama must be running with the model pulled (`ollama pull <model-name>`):

```bash
python evaluator.py --model <model-name>
```

Evaluate only specific questions:

```bash
python evaluator.py --model <model-name> --ids NB-001 NB-005
```

Re-score a saved run without calling a model. The input JSON must contain a `raw_responses` object mapping each question id to the response text:

```bash
python evaluator.py --dry-run results/results_<timestamp>.json
```

Results are written to `results/results_<timestamp>.json`, and a summary table is printed to the terminal.

| File | Purpose |
|------|---------|
| `questions.json` | The 52 benchmark questions |
| `evaluator.py` | The five-dimension scorer |
| `golden_cases.json` | 17 hand-verified scorer regression cases |
| `tests/` | Test suite guarding the scorer |
| `spec.md` | Full benchmark specification |
| `KNOWN_ISSUES.md` | Documented scorer limitations |

---

## Status and limitations

NyayaBench is an early-stage benchmark, and it is honest about its scope:

- It measures structured-reasoning *form and discipline*, not general knowledge or task accuracy. A model can score well here and still be wrong about the world, or vice versa.
- The question set (52) is sized to demonstrate the methodology, not to be exhaustive.
- Single-run scores under non-deterministic decoding can vary; the results above use greedy decoding specifically to remove that variance. Reported numbers should be reproduced under the stated conditions.
- See `KNOWN_ISSUES.md` for documented edge cases in the scorer (e.g. handling of inflected proper names in some scripts).

Independent evaluation is welcome and encouraged. The questions, the scorer, and the methodology are all open precisely so that the results can be checked, criticized, and built on.

---

## License

Released under the **Apache License 2.0**. See [LICENSE](LICENSE).

## Citation

If you use NyayaBench in your work, please cite:

```bibtex
@misc{nyayabench2026,
  title  = {NyayaBench: A Benchmark for Auditable, Structured Reasoning in Language Models},
  author = {Gursimran Singh},
  year   = {2026},
  url    = {https://nyayabench.com}
}
```

---

*NyayaBench is part of ongoing work on reasoning architectures grounded in classical Indian epistemology. The aim is not to invoke that tradition as ornament, but to put it to work, as a rigorous, practical method for making machine reasoning something you can actually inspect.*
