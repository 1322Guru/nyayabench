#!/usr/bin/env python3
"""
NyayaBench Baseline Runner
Queries IYRA + Qwen3-14B (local Ollama) + GPT-4o + Claude Sonnet 4.6
+ Gemini 1.5 Pro (OpenRouter) across the 52-question benchmark.
"""

import argparse, json, logging, os, sys, time
from datetime import datetime
from pathlib import Path
from typing import Any

import requests

# Resolve paths relative to this file so the benchmark runs from any clone location.
REPO_DIR = Path(__file__).resolve().parent
QUESTIONS_PATH = str(REPO_DIR / "questions.json")
OUTPUT_DIR = REPO_DIR / "results"

OLLAMA_URL = "http://localhost:11434/api/generate"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
OR_REFERER = "https://nyayabench.com"
OR_TITLE = "NyayaBench Baseline Run"

GENERATION_PARAMS = {"temperature": 0.0, "max_tokens": 2048, "top_p": 1.0}
CALL_TIMEOUT = 600   # generous timeout for large local models
RETRY_DELAYS = [5, 30]

MODELS = {
    "iyra-v10":          {"kind": "ollama",     "ollama_model": "iyra-v10:latest",             "label": "IYRA v10"},
    "qwen3-14b-base":    {"kind": "ollama",     "ollama_model": "qwen3:14b",                   "label": "Qwen3-14B (base)"},
    "gpt-4o":            {"kind": "openrouter", "or_model": "openai/gpt-4o",                   "label": "GPT-4o"},
    "claude-sonnet-4-6": {"kind": "openrouter", "or_model": "anthropic/claude-sonnet-4.6",     "label": "Claude Sonnet 4.6"},
    "gemini-1.5-pro":    {"kind": "openrouter", "or_model": "google/gemini-2.5-pro",           "label": "Gemini 2.5 Pro"},
}

SYSTEM_PROMPT = """You are a reasoning assistant. For every question, you must produce a response in the Nyāya Panchavayava 7-step structure:

1. Pratijñā — state the claim
2. Hetu — give the reason
3. Udāharaṇa — provide a sourced example
4. Upanaya — apply the example to the case
5. Nigamana — state the conclusion
6. Pūrvapakṣa — present a named philosopher's counter-argument
7. Siddhānta — defend your position against the counter-argument

End your response with a confidence signal on its own line:
CONFIDENCE: HIGH | LOW | NONE

If you have no grounded source for the claim, output CONFIDENCE: NONE and refuse to fabricate.

Answer in the language of the question."""

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
LOG_PATH = OUTPUT_DIR / f"baseline_run_{TIMESTAMP}.log"
logging.basicConfig(level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    handlers=[logging.FileHandler(LOG_PATH), logging.StreamHandler(sys.stdout)])
log = logging.getLogger(__name__)


def call_ollama(model_name, prompt):
    payload = {"model": model_name,
               "prompt": f"<|system|>\n{SYSTEM_PROMPT}\n<|user|>\n{prompt}\n<|assistant|>\n",
               "stream": False,
               "think": False,   # disable Qwen3 extended thinking — avoids empty final responses
               "options": {"temperature": GENERATION_PARAMS["temperature"],
                           "num_predict": GENERATION_PARAMS["max_tokens"],
                           "top_p": GENERATION_PARAMS["top_p"]}}
    t0 = time.time()
    r = requests.post(OLLAMA_URL, json=payload, timeout=CALL_TIMEOUT)
    r.raise_for_status()
    d = r.json()
    return {"text": d.get("response", "").strip(),
            "latency_s": round(time.time() - t0, 2),
            "input_tokens": d.get("prompt_eval_count"),
            "output_tokens": d.get("eval_count"),
            "raw": {"backend": "ollama"}}


def call_openrouter(or_model, prompt, api_key):
    headers = {"Authorization": f"Bearer {api_key}",
               "HTTP-Referer": OR_REFERER, "X-Title": OR_TITLE,
               "Content-Type": "application/json"}
    payload = {"model": or_model,
               "messages": [{"role": "system", "content": SYSTEM_PROMPT},
                            {"role": "user", "content": prompt}],
               "temperature": GENERATION_PARAMS["temperature"],
               "max_tokens": GENERATION_PARAMS["max_tokens"],
               "top_p": GENERATION_PARAMS["top_p"]}
    t0 = time.time()
    r = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=CALL_TIMEOUT)
    r.raise_for_status()
    d = r.json()
    msg = d["choices"][0]["message"]["content"].strip()
    usage = d.get("usage", {})
    return {"text": msg, "latency_s": round(time.time() - t0, 2),
            "input_tokens": usage.get("prompt_tokens"),
            "output_tokens": usage.get("completion_tokens"),
            "raw": {"backend": "openrouter", "id": d.get("id")}}


def generate_with_retry(key, cfg, prompt, api_key):
    last_err = None
    for attempt in range(len(RETRY_DELAYS) + 1):
        try:
            if cfg["kind"] == "ollama":
                return call_ollama(cfg["ollama_model"], prompt)
            elif cfg["kind"] == "openrouter":
                if not api_key:
                    raise RuntimeError("OPENROUTER_API_KEY not set")
                return call_openrouter(cfg["or_model"], prompt, api_key)
        except Exception as e:
            last_err = e
            if attempt < len(RETRY_DELAYS):
                d = RETRY_DELAYS[attempt]
                log.warning(f"  [{key}] {type(e).__name__}: {e}; retry in {d}s")
                time.sleep(d)
            else:
                log.error(f"  [{key}] FAILED after {attempt+1} attempts: {e}")
    return {"text": "", "latency_s": None, "input_tokens": None,
            "output_tokens": None, "error": f"{type(last_err).__name__}: {last_err}", "raw": {}}


PRICING = {
    "openai/gpt-4o": (2.50, 10.00),
    "anthropic/claude-sonnet-4.6": (3.00, 15.00),
    "google/gemini-2.5-pro": (1.25, 10.00),
}

def estimate_cost(n, models_to_run):
    SYS_TOK, Q_TOK, OUT_TOK = 250, 100, 1500
    log.info("─" * 60)
    log.info(f"DRY RUN — cost estimate for {n} questions")
    log.info("─" * 60)
    total = 0.0
    for k in models_to_run:
        cfg = MODELS[k]
        if cfg["kind"] != "openrouter":
            log.info(f"  {cfg['label']:25} (local) — $0.00")
            continue
        ti = (SYS_TOK + Q_TOK) * n / 1_000_000
        to = OUT_TOK * n / 1_000_000
        ip, op = PRICING.get(cfg["or_model"], (0, 0))
        c = ti * ip + to * op
        total += c
        log.info(f"  {cfg['label']:25} ~${c:.2f}")
    log.info("─" * 60)
    log.info(f"  {'ESTIMATED TOTAL':25} ~${total:.2f}")
    log.info("─" * 60)


def load_questions(path):
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Questions file not found: {path}")
    with open(p, "r", encoding="utf-8") as f:
        data = json.load(f)
    # questions.json is {"meta": {...}, "questions": [...]} — unwrap
    if isinstance(data, dict) and "questions" in data:
        data = data["questions"]
    if not isinstance(data, list):
        raise ValueError("Questions JSON must be a list of dicts")
    log.info(f"Loaded {len(data)} questions from {path}")
    return data


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", help="Comma-separated subset to run")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--questions", default=QUESTIONS_PATH)
    args = ap.parse_args()
    api_key = os.environ.get("OPENROUTER_API_KEY")
    questions = load_questions(args.questions)
    models_to_run = ([m.strip() for m in args.models.split(",")] if args.models
                     else list(MODELS.keys()))
    for m in models_to_run:
        if m not in MODELS:
            raise SystemExit(f"Unknown model: {m}. Known: {list(MODELS.keys())}")
    if args.dry_run:
        estimate_cost(len(questions), models_to_run)
        return
    if any(MODELS[m]["kind"] == "openrouter" for m in models_to_run) and not api_key:
        raise SystemExit('OPENROUTER_API_KEY not set. export OPENROUTER_API_KEY="sk-or-v1-..."')
    log.info("=" * 60)
    log.info(f"NyayaBench baseline — {len(questions)} questions × {len(models_to_run)} models")
    log.info("=" * 60)
    estimate_cost(len(questions), models_to_run)
    results = {"metadata": {"run_timestamp": TIMESTAMP, "num_questions": len(questions),
                            "system_prompt": SYSTEM_PROMPT, "generation_params": GENERATION_PARAMS,
                            "models": {k: MODELS[k] for k in models_to_run}},
               "responses": []}
    total_calls = len(questions) * len(models_to_run)
    done = 0
    for q_idx, q in enumerate(questions):
        qid = q.get("id", q_idx)
        prompt = q.get("prompt") or q.get("question") or q.get("text")
        if not prompt:
            log.warning(f"Question {qid} has no prompt; skipping")
            continue
        lang = q.get("language", "unknown")
        for mk in models_to_run:
            cfg = MODELS[mk]
            done += 1
            log.info(f"[{done}/{total_calls}] Q{qid} ({lang}) → {cfg['label']}")
            r = generate_with_retry(mk, cfg, prompt, api_key)
            results["responses"].append({
                "question_id": qid, "language": lang, "model_key": mk,
                "model_label": cfg["label"], "prompt": prompt,
                "response": r.get("text", ""), "latency_s": r.get("latency_s"),
                "input_tokens": r.get("input_tokens"),
                "output_tokens": r.get("output_tokens"),
                "error": r.get("error")})
            with open(OUTPUT_DIR / f"baseline_run_{TIMESTAMP}.json", "w", encoding="utf-8") as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
    log.info("=" * 60)
    log.info(f"Complete. Wrote {len(results['responses'])} responses.")
    log.info(f"  Output: {OUTPUT_DIR}/baseline_run_{TIMESTAMP}.json")
    log.info("=" * 60)


if __name__ == "__main__":
    main()
