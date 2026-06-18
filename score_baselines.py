#!/usr/bin/env python3
"""
Score the full NyayaBench baseline run and produce a comparison table.
Reuses exact scoring logic from evaluator.py — no new dimensions invented.

Usage:
    python3 score_baselines.py                          # scores nyayabench_full_baseline.json
    python3 score_baselines.py --input <path>           # score a specific baseline JSON
"""

import argparse, csv, json, sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

# Import the exact scoring pipeline from evaluator.py
sys.path.insert(0, str(Path(__file__).parent))
from evaluator import score_response, build_summary

RESULTS_DIR = Path(__file__).parent / "results"
QUESTIONS_PATH = Path(__file__).parent / "questions.json"

MODEL_ORDER = [
    "iyra-v10",
    "qwen3-14b-base",
    "gpt-4o",
    "claude-sonnet-4-6",
    "gemini-1.5-pro",
]

MODEL_LABELS = {
    "iyra-v10":          "IYRA v10",
    "qwen3-14b-base":    "Qwen3-14B",
    "gpt-4o":            "GPT-4o",
    "claude-sonnet-4-6": "Claude Sonnet 4.6",
    "gemini-1.5-pro":    "Gemini 2.5 Pro",
}

LANG_ORDER = ["english", "hindi", "punjabi", "tamil"]
LANG_SHORT  = {"english": "EN", "hindi": "HI", "punjabi": "PA", "tamil": "TA"}


def load_questions(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        d = json.load(f)
    qs = d["questions"] if isinstance(d, dict) and "questions" in d else d
    return {q["id"]: q for q in qs}


def load_baseline(path: Path) -> list:
    with open(path, encoding="utf-8") as f:
        d = json.load(f)
    return d["responses"]


def score_all(responses: list, questions: dict) -> dict:
    """Score every response; return results keyed by model_key."""
    by_model = defaultdict(list)
    skipped = 0
    for r in responses:
        if r.get("error") or not r.get("response"):
            skipped += 1
            continue
        qid = r["question_id"]
        q = questions.get(qid)
        if q is None:
            print(f"  WARN: question {qid} not found in questions.json — skipping", file=sys.stderr)
            skipped += 1
            continue
        scored = score_response(q, r["response"])
        scored["model_key"] = r["model_key"]
        scored["language"]  = r["language"]
        by_model[r["model_key"]].append(scored)
    if skipped:
        print(f"  Skipped {skipped} responses (errors / missing)", file=sys.stderr)
    return dict(by_model)


def model_stats(results: list) -> dict:
    n = len(results)
    if n == 0:
        return {}
    passed  = sum(1 for r in results if r["passed"])
    d = lambda k: sum(r["scores"][k] for r in results)
    by_lang = defaultdict(lambda: {"n": 0, "passed": 0})
    for r in results:
        lang = r.get("language", "unknown")
        by_lang[lang]["n"] += 1
        by_lang[lang]["passed"] += int(r["passed"])
    return {
        "n":           n,
        "pass_rate":   round(passed / n * 100, 1),
        "passed":      passed,
        "d1_avg":      round(d("format_adherence")       / n, 3),
        "d2_avg":      round(d("purvapaksha_quality")    / n, 3),
        "d3_avg":      round(d("confidence_calibration") / n, 3),
        "d4_avg":      round(d("language_consistency")   / n, 3),
        "d5_avg":      round(d("siddhanta_quality")      / n, 3),
        "total_avg":   round(sum(r["scores"]["total"] for r in results) / n, 3),
        "bench_score": round(sum(r["scores"]["total"] for r in results) / (9 * n) * 100, 1),
        "by_lang":     {k: round(v["passed"] / v["n"] * 100, 1)
                        for k, v in by_lang.items() if v["n"] > 0},
    }


def print_comparison_table(stats: dict, model_order: list) -> None:
    header_cols = ["Model", "Pass%", "Bench%", "D1 Fmt", "D2 Pūrva", "D3 Conf",
                   "D4 Lang", "D5 Siddh"] + [LANG_SHORT[l] for l in LANG_ORDER]
    col_w = [18, 6, 7, 7, 9, 7, 7, 8] + [5] * 4
    sep = "  "

    def fmt_row(vals):
        return sep.join(str(v).rjust(w) for v, w in zip(vals, col_w))

    line = "─" * (sum(col_w) + len(sep) * (len(col_w) - 1))
    print()
    print("NyayaBench Full Baseline — Model Comparison")
    print(line)
    print(fmt_row(header_cols))
    print(line)

    for mk in model_order:
        if mk not in stats:
            continue
        s = stats[mk]
        label = MODEL_LABELS.get(mk, mk)
        lang_cols = [f"{s['by_lang'].get(l, 0.0):.0f}" for l in LANG_ORDER]
        row = [
            label,
            f"{s['pass_rate']:.1f}",
            f"{s['bench_score']:.1f}",
            f"{s['d1_avg']:.2f}",
            f"{s['d2_avg']:.2f}",
            f"{s['d3_avg']:.2f}",
            f"{s['d4_avg']:.2f}",
            f"{s['d5_avg']:.2f}",
        ] + lang_cols
        print(fmt_row(row))

    print(line)
    print(f"  Pass threshold: total ≥ 6/9 per question | Bench threshold: score ≥ 67% AND pass ≥ 70%")
    print(f"  D1=Format(0-1) D2=Pūrvapakṣa(0-3) D3=Confidence(0-2) D4=Language(0-1) D5=Siddhānta(0-2)")
    print()


def print_markdown_table(stats: dict, model_order: list) -> None:
    langs = [LANG_SHORT[l] for l in LANG_ORDER]
    header = "| Model | Pass% | Bench% | D1 Fmt | D2 Pūrva | D3 Conf | D4 Lang | D5 Siddh |" + \
             "".join(f" {l} |" for l in langs)
    sep_row = "|:------|------:|-------:|-------:|---------:|--------:|--------:|---------:|" + \
              "".join("----:|" for _ in langs)
    print()
    print("## NyayaBench — Full Baseline Comparison\n")
    print(header)
    print(sep_row)
    for mk in model_order:
        if mk not in stats:
            continue
        s = stats[mk]
        label = MODEL_LABELS.get(mk, mk)
        lang_cols = "".join(f" {s['by_lang'].get(l, 0.0):.0f} |" for l in LANG_ORDER)
        print(f"| {label} | {s['pass_rate']:.1f} | {s['bench_score']:.1f} | "
              f"{s['d1_avg']:.2f} | {s['d2_avg']:.2f} | {s['d3_avg']:.2f} | "
              f"{s['d4_avg']:.2f} | {s['d5_avg']:.2f} |{lang_cols}")
    print()


def write_csv(stats: dict, model_order: list, out_path: Path) -> None:
    fieldnames = ["model_key", "model_label", "n", "passed", "pass_rate_pct", "bench_score_pct",
                  "d1_format_avg", "d2_purvapaksha_avg", "d3_confidence_avg",
                  "d4_language_avg", "d5_siddhanta_avg", "total_avg"] + \
                 [f"pass_pct_{LANG_SHORT[l]}" for l in LANG_ORDER]
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for mk in model_order:
            if mk not in stats:
                continue
            s = stats[mk]
            row = {
                "model_key":            mk,
                "model_label":          MODEL_LABELS.get(mk, mk),
                "n":                    s["n"],
                "passed":               s["passed"],
                "pass_rate_pct":        s["pass_rate"],
                "bench_score_pct":      s["bench_score"],
                "d1_format_avg":        s["d1_avg"],
                "d2_purvapaksha_avg":   s["d2_avg"],
                "d3_confidence_avg":    s["d3_avg"],
                "d4_language_avg":      s["d4_avg"],
                "d5_siddhanta_avg":     s["d5_avg"],
                "total_avg":            s["total_avg"],
            }
            for l in LANG_ORDER:
                row[f"pass_pct_{LANG_SHORT[l]}"] = s["by_lang"].get(l, 0.0)
            w.writerow(row)
    print(f"CSV written: {out_path}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default=None, help="Baseline JSON path")
    args = ap.parse_args()

    if args.input:
        baseline_path = Path(args.input)
    else:
        # prefer the merged full-baseline, else most recent baseline_run_*.json
        merged = RESULTS_DIR / "nyayabench_full_baseline.json"
        if merged.exists():
            baseline_path = merged
        else:
            candidates = sorted(RESULTS_DIR.glob("baseline_run_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
            if not candidates:
                print("ERROR: No baseline JSON found in results/", file=sys.stderr)
                sys.exit(1)
            baseline_path = candidates[0]

    print(f"Scoring: {baseline_path}")
    questions = load_questions(QUESTIONS_PATH)
    print(f"Questions loaded: {len(questions)}")
    responses = load_baseline(baseline_path)
    print(f"Responses loaded: {len(responses)}")

    by_model = score_all(responses, questions)
    stats = {mk: model_stats(results) for mk, results in by_model.items()}

    print_comparison_table(stats, MODEL_ORDER)
    print_markdown_table(stats, MODEL_ORDER)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = RESULTS_DIR / f"comparison_{ts}.csv"
    write_csv(stats, MODEL_ORDER, csv_path)

    # Also dump full scored JSON
    scored_json_path = RESULTS_DIR / f"scored_{ts}.json"
    with open(scored_json_path, "w", encoding="utf-8") as f:
        json.dump({"scored_from": str(baseline_path),
                   "timestamp": ts,
                   "stats": stats,
                   "per_model_results": {mk: v for mk, v in by_model.items()}},
                  f, ensure_ascii=False, indent=2)
    print(f"Full scored JSON: {scored_json_path}")


if __name__ == "__main__":
    main()
