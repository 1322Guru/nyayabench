#!/usr/bin/env python3
"""
run_declared_v3.py: the reconstructed runner for the four declared generation
runs of EVALUATOR_V3_SPEC.md, section 2.

Approved spec commit: 441edf07d4be284f363cccb7d99f8b0cd80e11cc
(tag evaluator-v3-spec-approved).

What it reproduces
    The Ollama call path of the tracked run_baselines.py: the same system
    prompt, the same prompt string, the same endpoint, thinking off, the same
    retry delays and the same record fields. The system prompt, endpoint,
    timeout and retry delays are read from run_baselines.py itself, without
    importing it, so they cannot drift.
    Generation settings are the ones recorded in the metadata of the frozen
    response file results/baseline_run_8192_20260621_191310.json:
    temperature 0.0, top_p 1.0, 8,192 new tokens, context 12,288.

What it adds, and why
    Each response is appended to a partial file as it completes, so a crashed
    job resumes without repeating a finished question.
    One difference from the tracked main loop: when the retry wrapper gives
    up on a question, the job stops instead of storing an empty answer. The
    question has no stored response and is tried again on resume. A declared
    run therefore never contains an error row.
    Each run ends with a final JSON file in the layout of the frozen file, a
    done marker and a SHA-256 file.
    The Ollama version is read before every run. A run does not start if the
    version differs from the one recorded for the first run.
    A STOP file in the repo root, or in its parent folder, stops the job
    cleanly before the next question.

Usage
    python3 run_declared_v3.py                 run 1 to 4 in order
    python3 run_declared_v3.py --runs 3,4      only these runs, in this order
    python3 run_declared_v3.py --status        print progress, call no model

This script scores nothing.
"""
import argparse
import ast
import fcntl
import hashlib
import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import requests

REPO_DIR = Path(__file__).resolve().parent
RESULTS = REPO_DIR / "results"
QUESTIONS_PATH = REPO_DIR / "questions.json"
TRACKED_RUNNER = REPO_DIR / "run_baselines.py"
FROZEN_FILE = RESULTS / "baseline_run_8192_20260621_191310.json"
MODEL_MANIFEST = RESULTS / "v3_declared_models.json"
STATE_PATH = RESULTS / "v3_declared_runs.state.json"
LOG_PATH = RESULTS / "v3_declared_runs.log"
LOCK_PATH = RESULTS / "v3_declared_runs.lock"

SPEC_COMMIT = "441edf07d4be284f363cccb7d99f8b0cd80e11cc"
SYSTEM_PROMPT_SHA256 = "70f1562d8c8fa69b291bb52903f4a136d6a27d65b1be3469b89eca3e94c0c2bc"

# Settings recorded in the frozen file's metadata. Same keys, same values.
GENERATION_PARAMS = {"temperature": 0.0, "max_tokens": 8192, "top_p": 1.0, "num_ctx": 12288}

RUNS = {
    1: {"model_key": "iyra-v10", "ollama_model": "iyra-v10-q6", "label": "IYRA v10",
        "stem": "v3_run1_iyra_v10_replication",
        "note": "declared run 1: runner replication check, IYRA v10 served as iyra-v10-q6"},
    2: {"model_key": "iyra-v11", "ollama_model": "iyra-v11-cont2-2ep-q6", "label": "IYRA v11",
        "stem": "v3_run2_iyra_v11",
        "note": "declared run 2: IYRA v11 served as iyra-v11-cont2-2ep-q6"},
    3: {"model_key": "qwen3-14b-q6k-iyra-system", "ollama_model": "qwen3-14b-q6k-iyra-system",
        "label": "Qwen3-14B base Q6_K, IYRA system prompt",
        "stem": "v3_run3_qwen3_14b_q6k_iyra_system",
        "note": "declared run 3: base at Q6_K with the system prompt and repeat penalty of the IYRA v10 model file"},
    4: {"model_key": "qwen3-14b-q6k", "ollama_model": "qwen3-14b-q6k", "label": "Qwen3-14B base Q6_K",
        "stem": "v3_run4_qwen3_14b_q6k",
        "note": "declared run 4: base at Q6_K, no system prompt in the model file, repeat penalty 1"},
}

log = logging.getLogger("run_declared_v3")


def tracked_constants():
    """Read SYSTEM_PROMPT, OLLAMA_URL, CALL_TIMEOUT and RETRY_DELAYS from run_baselines.py without importing it."""
    tree = ast.parse(TRACKED_RUNNER.read_text(encoding="utf-8"))
    want = {"SYSTEM_PROMPT", "OLLAMA_URL", "CALL_TIMEOUT", "RETRY_DELAYS"}
    found = {}
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if getattr(t, "id", None) in want:
                    found[t.id] = ast.literal_eval(node.value)
    missing = want - set(found)
    if missing:
        raise SystemExit(f"run_baselines.py lacks {sorted(missing)}")
    got = hashlib.sha256(found["SYSTEM_PROMPT"].encode("utf-8")).hexdigest()
    if got != SYSTEM_PROMPT_SHA256:
        raise SystemExit("the system prompt in run_baselines.py is not the one stored in the frozen file")
    return found


C = tracked_constants()
SYSTEM_PROMPT = C["SYSTEM_PROMPT"]
OLLAMA_URL = C["OLLAMA_URL"]
CALL_TIMEOUT = C["CALL_TIMEOUT"]
RETRY_DELAYS = C["RETRY_DELAYS"]
OLLAMA_BASE = OLLAMA_URL.rsplit("/api/", 1)[0]


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def call_ollama(model_name, prompt):
    """The tracked call_ollama, with the frozen file's two extra settings: 8,192 new tokens and num_ctx."""
    payload = {"model": model_name,
               "prompt": f"<|system|>\n{SYSTEM_PROMPT}\n<|user|>\n{prompt}\n<|assistant|>\n",
               "stream": False,
               "think": False,
               "options": {"temperature": GENERATION_PARAMS["temperature"],
                           "num_predict": GENERATION_PARAMS["max_tokens"],
                           "top_p": GENERATION_PARAMS["top_p"],
                           "num_ctx": GENERATION_PARAMS["num_ctx"]}}
    t0 = time.time()
    r = requests.post(OLLAMA_URL, json=payload, timeout=CALL_TIMEOUT)
    r.raise_for_status()
    d = r.json()
    return {"text": d.get("response", "").strip(),
            "latency_s": round(time.time() - t0, 2),
            "input_tokens": d.get("prompt_eval_count"),
            "output_tokens": d.get("eval_count"),
            "thinking_chars": len(d.get("thinking") or ""),
            "done_reason": d.get("done_reason")}


def generate_with_retry(key, model_name, prompt):
    """The tracked retry wrapper: same delays, same error record. Every retry is logged."""
    last_err = None
    for attempt in range(len(RETRY_DELAYS) + 1):
        try:
            out = call_ollama(model_name, prompt)
            out["attempts"] = attempt + 1
            return out
        except Exception as e:
            last_err = e
            if attempt < len(RETRY_DELAYS):
                d = RETRY_DELAYS[attempt]
                log.warning(f"  [{key}] {type(e).__name__}: {e}; retry in {d}s")
                time.sleep(d)
            else:
                log.error(f"  [{key}] FAILED after {attempt + 1} attempts: {e}")
    return {"text": "", "latency_s": None, "input_tokens": None, "output_tokens": None,
            "error": f"{type(last_err).__name__}: {last_err}", "attempts": len(RETRY_DELAYS) + 1}


def ollama_version():
    return requests.get(OLLAMA_BASE + "/api/version", timeout=30).json().get("version")


def model_info(name):
    """What Ollama reports for the registered model. Hashes only for the long fields."""
    tags = requests.get(OLLAMA_BASE + "/api/tags", timeout=30).json().get("models", [])
    hit = [m for m in tags if m.get("name") in (name, name + ":latest") or m.get("model") in (name, name + ":latest")]
    if not hit:
        raise SystemExit(f"model {name} is not registered in Ollama")
    show = requests.post(OLLAMA_BASE + "/api/show", json={"model": name}, timeout=60).json()
    system = show.get("system") or ""
    return {"name": hit[0].get("name"), "digest": hit[0].get("digest"), "size_bytes": hit[0].get("size"),
            "quantization": (show.get("details") or {}).get("quantization_level"),
            "parameters": show.get("parameters"),
            "system_prompt_chars": len(system),
            "system_prompt_sha256": hashlib.sha256(system.encode("utf-8")).hexdigest() if system else None,
            "template_sha256": hashlib.sha256((show.get("template") or "").encode("utf-8")).hexdigest()}


def load_questions():
    data = json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))
    if isinstance(data, dict) and "questions" in data:
        data = data["questions"]
    return data


def paths(run):
    stem = RUNS[run]["stem"]
    return {"partial": RESULTS / (stem + ".partial.jsonl"), "final": RESULTS / (stem + ".json"),
            "done": RESULTS / (stem + ".done"), "sha": RESULTS / (stem + ".json.sha256")}


def read_partial(path):
    """Finished records, in file order. A torn last line from a crash is dropped."""
    if not path.exists():
        return []
    recs, good = [], []
    lines = path.read_text(encoding="utf-8").split("\n")
    for i, line in enumerate(lines):
        if not line.strip():
            continue
        try:
            recs.append(json.loads(line))
            good.append(line)
        except json.JSONDecodeError:
            log.warning(f"dropping a torn line {i + 1} in {path.name}")
    if len(good) != len([x for x in lines if x.strip()]):
        path.write_text("\n".join(good) + ("\n" if good else ""), encoding="utf-8")
    return recs


def stop_requested():
    return (REPO_DIR / "STOP").exists() or (REPO_DIR.parent / "STOP").exists()


def load_state():
    return json.loads(STATE_PATH.read_text(encoding="utf-8")) if STATE_PATH.exists() else {}


def save_state(state):
    tmp = STATE_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=1) + "\n", encoding="utf-8")
    os.replace(tmp, STATE_PATH)


def run_one(run, questions):
    cfg = RUNS[run]
    p = paths(run)
    key = cfg["model_key"]
    if p["done"].exists() and p["final"].exists():
        done = json.loads(p["done"].read_text(encoding="utf-8"))
        if sha256_file(p["final"]) == done.get("sha256"):
            log.info(f"run {run} is already done: {p['final'].name} sha256 {done['sha256']}")
            return
        raise SystemExit(f"run {run}: the final file does not match its done marker")

    version = ollama_version()
    state = load_state()
    if state.get("ollama_version") and state["ollama_version"] != version:
        raise SystemExit(f"Ollama version is {version}, the first run recorded {state['ollama_version']}; not starting run {run}")
    state.setdefault("ollama_version", version)
    info = model_info(cfg["ollama_model"])
    rs = state.setdefault("runs", {}).setdefault(str(run), {"started_at": datetime.now().isoformat(timespec="seconds"), "starts": 0})
    rs["starts"] += 1
    save_state(state)

    recs = read_partial(p["partial"])
    finished = {r["question_id"] for r in recs}
    log.info("=" * 60)
    log.info(f"run {run}: {cfg['label']} as {cfg['ollama_model']}; Ollama {version}; "
             f"{len(finished)} of {len(questions)} already on disk; start number {rs['starts']}")
    log.info(f"run {run}: model digest {info['digest']}, quantization {info['quantization']}")
    log.info("=" * 60)

    with open(p["partial"], "a", encoding="utf-8") as fpart:
        for n, q in enumerate(questions, 1):
            qid = q.get("id", n - 1)
            if qid in finished:
                continue
            if stop_requested():
                log.info(f"STOP file found; stopping before {qid}. Run again to resume.")
                sys.exit(0)
            prompt = q.get("prompt") or q.get("question") or q.get("text")
            lang = q.get("language", "unknown")
            log.info(f"[run {run}] [{n}/{len(questions)}] Q{qid} {lang} -> {cfg['label']}")
            r = generate_with_retry(key, cfg["ollama_model"], prompt)
            if r.get("error"):
                log.error(f"[run {run}] Q{qid} has no answer after {r['attempts']} attempts: {r['error']}. "
                          f"Job stopped; nothing was stored for this question. Run again to resume.")
                sys.exit(3)
            rec = {"question_id": qid, "language": lang, "model_key": key, "model_label": cfg["label"],
                   "prompt": prompt, "response": r.get("text", ""), "latency_s": r.get("latency_s"),
                   "input_tokens": r.get("input_tokens"), "output_tokens": r.get("output_tokens"),
                   "error": r.get("error"),
                   "_meta": {"attempts": r["attempts"], "thinking_chars": r.get("thinking_chars", 0),
                             "done_reason": r.get("done_reason"), "ollama_version": version,
                             "finished_at": datetime.now().isoformat(timespec="seconds")}}
            fpart.write(json.dumps(rec, ensure_ascii=False) + "\n")
            fpart.flush()
            os.fsync(fpart.fileno())
            finished.add(qid)
            log.info(f"[run {run}] Q{qid} stored: {r.get('output_tokens')} tokens in {r.get('latency_s')}s"
                     + (f", attempts {r['attempts']}" if r["attempts"] > 1 else ""))

    # Every question has a stored answer: write the final file in the layout of the frozen file.
    recs = read_partial(p["partial"])
    by_id = {r["question_id"]: r for r in recs}
    order = [q.get("id", i) for i, q in enumerate(questions)]
    assert set(order) == set(by_id) and len(by_id) == len(questions), "partial file does not cover the questions"
    end_version = ollama_version()
    think = sum(1 for r in recs if "<think>" in r["response"] or "</think>" in r["response"]
                or r["_meta"].get("thinking_chars", 0) > 0)
    manifest = json.loads(MODEL_MANIFEST.read_text(encoding="utf-8")) if MODEL_MANIFEST.exists() else {}
    fields = ["question_id", "language", "model_key", "model_label", "prompt", "response",
              "latency_s", "input_tokens", "output_tokens", "error"]
    final = {"metadata": {
                 "run_timestamp": datetime.fromisoformat(rs["started_at"]).strftime("%Y%m%d_%H%M%S"),
                 "num_questions": len(questions),
                 "system_prompt": SYSTEM_PROMPT,
                 "generation_params": GENERATION_PARAMS,
                 "note": cfg["note"],
                 "models": {key: {"kind": "ollama", "ollama_model": cfg["ollama_model"], "label": cfg["label"]}},
                 "declared_run": {
                     "run": run, "spec_commit": SPEC_COMMIT,
                     "runner": {"file": Path(__file__).name, "sha256": sha256_file(Path(__file__).resolve())},
                     "ollama_version_start": version, "ollama_version_end": end_version,
                     "ollama_versions_seen": sorted({r["_meta"].get("ollama_version") for r in recs}),
                     "model": info, "model_file": manifest.get(cfg["ollama_model"]),
                     "started_at": rs["started_at"], "finished_at": datetime.now().isoformat(timespec="seconds"),
                     "starts": rs["starts"],
                     "answers_with_retries": [{"question_id": r["question_id"], "attempts": r["_meta"]["attempts"]}
                                              for r in recs if r["_meta"]["attempts"] > 1],
                     "answers_at_token_limit": sum(1 for r in recs if (r.get("output_tokens") or 0) >= GENERATION_PARAMS["max_tokens"]),
                     "responses_with_think_block": think}},
             "responses": [{k: by_id[i][k] for k in fields} for i in order]}
    tmp = p["final"].with_suffix(".json.tmp")
    tmp.write_text(json.dumps(final, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, p["final"])
    digest = sha256_file(p["final"])
    p["sha"].write_text(f"{digest}  {p['final'].name}\n", encoding="utf-8")
    p["done"].write_text(json.dumps({"run": run, "file": p["final"].name, "sha256": digest,
                                     "responses": len(final["responses"]), "ollama_version": version,
                                     "responses_with_think_block": think,
                                     "finished_at": final["metadata"]["declared_run"]["finished_at"]}, indent=1) + "\n",
                         encoding="utf-8")
    state = load_state()
    state["runs"][str(run)].update({"finished_at": final["metadata"]["declared_run"]["finished_at"], "sha256": digest})
    save_state(state)
    log.info(f"run {run} DONE: {p['final'].name} sha256 {digest}; {len(final['responses'])} responses; "
             f"think blocks {think}; at the token limit {final['metadata']['declared_run']['answers_at_token_limit']}")


def status():
    questions = load_questions()
    state = load_state()
    print(f"Ollama version recorded for the first run: {state.get('ollama_version', 'none yet')}")
    for run in sorted(RUNS):
        p = paths(run)
        if p["done"].exists():
            d = json.loads(p["done"].read_text(encoding="utf-8"))
            print(f"run {run}: DONE  {d['responses']} responses  sha256 {d['sha256']}  finished {d['finished_at']}")
        elif p["partial"].exists():
            n = sum(1 for line in p["partial"].read_text(encoding="utf-8").split("\n") if line.strip())
            print(f"run {run}: {n} of {len(questions)} answers on disk")
        else:
            print(f"run {run}: not started")
    if LOG_PATH.exists():
        tail = LOG_PATH.read_text(encoding="utf-8").strip().split("\n")[-3:]
        print("last log lines:")
        for line in tail:
            print("   " + line)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", default="1,2,3,4", help="comma separated run numbers, executed in the order given")
    ap.add_argument("--status", action="store_true", help="print progress and exit; calls no model")
    args = ap.parse_args()
    if args.status:
        status()
        return
    RESULTS.mkdir(exist_ok=True)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-7s  %(message)s",
                        handlers=[logging.FileHandler(LOG_PATH), logging.StreamHandler(sys.stdout)])
    lock = open(LOCK_PATH, "w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        raise SystemExit("another run_declared_v3.py job holds the lock")
    lock.write(str(os.getpid()))
    lock.flush()
    runs = [int(x) for x in args.runs.split(",") if x.strip()]
    for r in runs:
        if r not in RUNS:
            raise SystemExit(f"unknown run {r}")
    questions = load_questions()
    if len(questions) != 52:
        raise SystemExit(f"expected 52 questions, found {len(questions)}")
    log.info(f"job start, pid {os.getpid()}, runs {runs}, spec commit {SPEC_COMMIT}, "
             f"runner sha256 {sha256_file(Path(__file__).resolve())}")
    log.info(f"settings {GENERATION_PARAMS}; timeout {CALL_TIMEOUT}s; retry delays {RETRY_DELAYS}")
    for r in runs:
        if stop_requested():
            log.info("STOP file found; not starting the next run.")
            return
        run_one(r, questions)
    log.info("job complete: all requested runs are done")


if __name__ == "__main__":
    main()
