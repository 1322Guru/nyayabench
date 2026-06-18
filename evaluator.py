#!/usr/bin/env python3
"""
NyayaBench v1.0 Evaluator
=========================
Evaluates AI model responses against the NyayaBench epistemic reasoning benchmark.

Usage:
    python evaluator.py                           # run against default model (iyra-v6)
    python evaluator.py --model iyra-v7           # specify model
    python evaluator.py --output my_results.json  # custom output path
    python evaluator.py --dry-run results.json    # score a saved results JSON
    python evaluator.py --questions q.json        # custom questions file
    python evaluator.py --ids NB-001 NB-002       # run only specific question IDs
"""

import argparse
import json
import os
import re
import subprocess
import sys
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

NYAYA_STEPS = {
    "pratijña": [
        "pratijña", "pratijñā", "pratijna", r"\bthesis\b", r"\bclaim:\b",
        # Devanagari
        "प्रतिज्ञा", "प्रतिज्ञ",
        # Gurmukhi
        "ਪ੍ਰਤਿਗਿਆ", "ਦਾਅਵਾ",
        # Tamil
        "முன்மொழிவு",
    ],
    "hetu": [
        r"h[eē]t[uū]", r"\breason:\b",
        "हेतु", "ਕਾਰਨ", "காரணம்",
    ],
    "udaharana": [
        r"ud[aā]hara[nṇ][aā]?", r"\bexample:\b",
        "उदाहरण", "ਉਦਾਹਰਣ", "உதாரணம்",
    ],
    "upanaya": [
        r"upanaya", r"\bapplication:\b",
        "उपनय", "ਉਪਨਯ", "பயன்பாடு",
    ],
    "nigamana": [
        r"nigamana", r"\bconclusion:\b",
        "निगमन", "ਨਿਗਮਨ", "முடிவு",
    ],
    "purvapaksha": [
        r"p[uū]rvapak[sṣ]a", "purvapaksha", "purvapaksa",
        r"counter.?argument", r"\bobjection:\b",
        "पूर्वपक्ष", "ਪੂਰਵਪੱਖ", "எதிர்வாதம்",
    ],
    "siddhanta": [
    r"siddh[aā]nta", r"\bsiddhanta\b", r"\bestablished view\b", r"சித்தாந்தம்", r"பிரதிஞ்ஞா", r"ஹேது", r"உதாரணம்", r"உபநயம்", r"நிகமனம்", r"பூர்வபக்ஷம்",
    r"ਸਿੱਧਾਂਤ", r"ਸਿਧਾਂਤ",          # Gurmukhi
    r"सिद्धांत", r"सिद्धान्त",        # Devanagari/Hindi
    r"சித்தாந்தம்", r"சித்தாந்த",    # Tamil
        r"\bresponse:\b", r"\brefutation:\b",
        "सिद्धान्त", "सिद्धांत", "ਸਿੱਧਾਂਤ", "சித்தாந்தம்",
    ],
}

GENERIC_PHRASES = re.compile(
    r"some argue|critics say|opponents claim|many believe|it is argued"
    r"|some philosophers|one might object|some would say"
    # Hindi (Devanagari) vague, un-attributed objections
    r"|कुछ\s*लोग\s*कहते\s*हैं|कुछ\s*तर्क\s*देते\s*हैं|आलोचक\s*कहते\s*हैं"
    r"|कई\s*मानते\s*हैं|कुछ\s*दार्शनिक"
    # Punjabi (Gurmukhi)
    r"|ਕੁਝ\s*ਲੋਕ\s*ਕਹਿੰਦੇ\s*ਹਨ|ਕੁਝ\s*ਦਲੀਲ\s*ਦਿੰਦੇ\s*ਹਨ|ਆਲੋਚਕ\s*ਕਹਿੰਦੇ\s*ਹਨ"
    r"|ਬਹੁਤ\s*ਮੰਨਦੇ\s*ਹਨ"
    # Tamil
    r"|சிலர்\s*வாதிடுகின்றனர்|சிலர்\s*கூறுகின்றனர்|விமர்சகர்கள்\s*கூறுகின்றனர்"
    r"|பலர்\s*நம்புகின்றனர்",
    re.IGNORECASE,
)

# Objection-verb patterns used by the D2 substance gate.
# A named-philosopher match must be accompanied by an argumentation verb
# (in any of the four benchmark languages) OR ≥25 words in the PP section
# before it earns D2=3.  Bare name-drops (< 25 words, no verb) score D2=2.
OBJECTION_VERB = re.compile(
    # English — present and past tense
    r"argues?|argued|contends?|contended|holds?\s+that|held\s+that"
    r"|maintains?\s+that|maintained\s+that|posits?|posited"
    r"|claims?\s+that|claimed\s+that|asserts?\s+that|asserted\s+that"
    r"|object(?:s|ed)?\s+that|rejects?\s+that|rejected\s+that"
    r"|according\s+to|would\s+say|would\s+argue|counter(?:s|ed)?\s+that"
    # Hindi (Devanagari)
    r"|मानते\s+हैं|कहते\s+हैं|तर्क\s+देते\s+हैं|खण्डन|खंडन|के\s+अनुसार"
    # Punjabi (Gurmukhi)
    r"|ਕਹਿਣਾ\s+ਹੈ|ਦਾ\s+ਤਰਕ\s+ਹੈ|ਅਨੁਸਾਰ|ਦਲੀਲ\s+ਦਿੰਦੇ|ਮੰਨਦੇ\s+ਹਨ"
    # Tamil
    r"|வலியுறுத்துகிறது|வலியுறுத்துகிறார்|கூறுகிறார்|வாதிடுகிறார்"
    r"|கருதுகிறார்|படி|என்று\s+கூறுகிறார்",
    re.IGNORECASE,
)

D2_SUBSTANCE_MIN_WORDS = 25  # fallback word-count gate when no verb matched

NAMED_SCHOOLS = re.compile(
    r"buddhist|b[oō]dhist|carvaka|ch[aā]rv[aā]ka|m[iī]m[aā][mṃ]s[aā]|mimamsa"
    r"|ved[aā]nta|vedanta|ny[aā]ya|nyaya|vai[sṣ]e[sṣ]ika|vaisheshika|vaisesika"
    r"|jain|advaita|dvaita|s[aā][mṃ]khya|samkhya|kant[i]?an|utilitarian"
    r"|cartesian|stoic|epicurean|analytic philosophy|continental philosophy"
    r"|pragmatist|empiricist|rationalist|idealist|materialist|dualist"
    r"|existentialist|phenomenolog"
    # Devanagari (Hindi) school names — confirmed from IYRA baseline responses
    r"|चार्वाक|बौद्ध|मध्यमक"
    # Tamil school names — confirmed from IYRA baseline responses
    r"|சார்வாக|சார்வாகன்|பௌத்த|மாத்யமிக|நவ்ய"
    # Gurmukhi (Punjabi) school names — confirmed from IYRA baseline responses
    r"|ਚਾਰਵਾਕ|ਬੌਧ",
    re.IGNORECASE,
)

NAMED_PHILOSOPHERS = re.compile(
    r"dign[aā]ga|dharmak[iī]rti|n[aā]g[aā]rjuna|[sṣ]a[mṃ]kara|shankara|shan?kara"
    r"|r[aā]m[aā]nuja|ramanuja|ga[mṃ]ge[sṣ]a|gangesa|udayana|v[aā]tsy[aā]yana"
    r"|vatsyayana|gautama|jayar[aā][sṣ]i|kum[aā]rila|prabh[aā]kara|jay[aā]nta"
    r"|kant\b|hegel|mill\b|hume\b|descartes|chalmers|nagel\b|quine\b|kripke"
    r"|aristotle|plato|nietzsche|wittgenstein|russell\b|frege\b|locke\b"
    r"|berkeley\b|spinoza|leibniz|buddha\b|parfit\b|rawls\b|nozick\b"
    r"|sandel\b|sen\b|mill\b|moore\b|mackie\b|blackburn|street\b|ruse\b"
    r"|brouwer|g[öo]del|hilbert|penrose\b|chomsky|whorf\b|sapir\b|pinker\b"
    r"|boroditsky|bhartrihari|bhartr[iī]hari|anselm|swinburne|frankfurt\b"
    r"|chalmers|kim\b|jaegwon|mctaggart|davidson|dennett|searle\b|nagel"
    r"|kautilya|kautily|tiruvalluvar|tolkappiyar|bharata\b|abhinavagupta"
    r"|crane\b|parmenides|heraclitus|thales"
    # Devanagari (Hindi) philosopher names — confirmed from IYRA baseline responses
    r"|दिग्नाग|धर्मकीर्ति|नागार्जुन|बृहस्पति|अम्बेडकर"
    # Tamil philosopher names — confirmed from IYRA baseline responses
    r"|திக்நாகர்|தர்மகீர்த்தி|நாகார்ஜுன|பிரஹஸ்பதி|அம்பேத்கர்"
    # Gurmukhi (Punjabi) philosopher names — confirmed from IYRA baseline responses
    r"|ਦਿਗਨਾਗ|ਨਾਗਾਰਜੁਨ|ਅੰਬੇਡਕਰ",
    re.IGNORECASE,
)

CONFIDENCE_PATTERN = re.compile(
    r"\[CONFIDENCE:\s*(HIGH|MEDIUM|LOW|NONE)\]"
    r"|confidence[:\s]+(high|medium|low|none)"
    r"|\bI am (uncertain|unsure|not sure|confident)\b"
    r"|\b(likely|probably|certainly|speculatively|tentatively)\b"
    # Hindi (Devanagari) natural-language hedging — partial-credit signal only
    r"|शायद|संभवतः|संभव\s*है|हो\s*सकता\s*है|निश्चित\s*(?:रूप\s*से\s*)?नहीं"
    r"|पक्का\s*नहीं|संदेह|स्पष्ट\s*नहीं"
    # Punjabi (Gurmukhi) natural-language hedging
    r"|ਸ਼ਾਇਦ|ਸੰਭਵ\s*ਹੈ|ਹੋ\s*ਸਕਦਾ\s*ਹੈ|ਪੱਕਾ\s*ਨਹੀਂ|ਯਕੀਨ\s*ਨਾਲ\s*ਨਹੀਂ"
    r"|ਸ਼ੱਕ|ਸਪੱਸ਼ਟ\s*ਨਹੀਂ"
    # Tamil natural-language hedging
    r"|ஒருவேளை|இருக்கலாம்|உறுதியில்லை|நிச்சயமில்லை|தெளிவில்லை|சந்தேகம்"
    r"|சொல்ல\s*முடியாது",
    re.IGNORECASE,
)

CONFIDENCE_LEVEL_PATTERN = re.compile(
    r"\[CONFIDENCE:\s*(HIGH|MEDIUM|LOW|NONE)\]|confidence[:\s]+(high|medium|low|none)",
    re.IGNORECASE,
)

SIDDHANTA_BACKREF = re.compile(
    r"this objection|the objection|however\b|nevertheless\b|despite this"
    r"|in response|against this view|refut|the counter.?argument"
    r"|purvapaksha argues|the objector|while.*argue|even if.*grant"
    # Hindi (Devanagari) — refer-back / rebuttal connectives
    r"|तथापि|फिर\s*भी|यह\s*आपत्ति|इस\s*आपत्ति|इसके\s*विरुद्ध|खण्डन|खंडन|उत्तर\s*में"
    # Punjabi (Gurmukhi)
    r"|ਤਾਂ\s*ਵੀ|ਫਿਰ\s*ਵੀ|ਇਹ\s*ਇਤਰਾਜ਼|ਇਸ\s*ਇਤਰਾਜ਼|ਇਸ\s*ਦੇ\s*ਵਿਰੁੱਧ|ਖੰਡਨ|ਜਵਾਬ\s*ਵਿੱਚ"
    # Tamil
    r"|ஆயினும்|எனினும்|இந்த\s*எதிர்வாதம்|இந்த\s*ஆட்சேபனை|இதற்கு\s*எதிராக|மறுப்பு",
    re.IGNORECASE,
)

TECHNICAL_VOCAB = re.compile(
    r"anum[aā]na|vy[aā]pti|pak[sṣ]a|s[aā]dhya|apoha|sv[aā]bh[aā]vahetu"
    r"|pras[aā][mṃ]ga|pram[aā][nṇ]a|praty[aā]k[sṣ]a|sab[dḍ]a\b"
    r"|reductio|modus ponens|syllogism|valid argument|logical fallacy"
    r"|inference rule|dialetheism|paraconsistent|tautology|contradiction"
    r"|supervenience|epiphenomen|qualia|intentionality|functionalism"
    r"|physicalism|dualism|emergenc"
    # Hindi (Devanagari) core Nyaya / pramana vocabulary
    r"|अनुमान|व्याप्ति|प्रमाण|प्रत्यक्ष|साध्य|अपोह|पक्ष"
    # Punjabi (Gurmukhi)
    r"|ਅਨੁਮਾਨ|ਵਿਆਪਤੀ|ਪ੍ਰਮਾਣ|ਪ੍ਰਤੱਖ|ਸਾਧ੍ਯ|ਅਪੋਹ|ਪੱਖ"
    # Tamil
    r"|அனுமானம்|வியாப்தி|பிரமாணம்|பிரத்யக்ஷம்|சாத்யம்|அபோஹம்|பக்ஷம்",
    re.IGNORECASE,
)

# Unicode block ranges for language detection
UNICODE_BLOCKS = {
    "devanagari": (0x0900, 0x097F),   # Hindi
    "gurmukhi":   (0x0A00, 0x0A7F),   # Punjabi
    "tamil":      (0x0B80, 0x0BFF),
}

SPECULATIVE_DOMAINS = {
    "consciousness_identity", "god_existence", "free_will", "aesthetics_art"
}
EVIDENCE_DOMAINS = {
    "logic_mathematical_truth", "nyaya_epistemic", "language_thought"
}


# ---------------------------------------------------------------------------
# Scoring functions
# ---------------------------------------------------------------------------

def score_format_adherence(response: str) -> tuple[int, dict]:
    """
    Dimension 1: Format Adherence (0–1).
    Returns (score, details).
    """
    text = response.lower()
    found = {}
    positions = {}

    for step, patterns in NYAYA_STEPS.items():
        for pattern in patterns:
            m = re.search(pattern, text, re.IGNORECASE)
            if m:
                found[step] = True
                positions[step] = m.start()
                break
        else:
            found[step] = False

    all_present = all(found.values())

    # Check Purvapaksha appears before Siddhanta
    order_ok = True
    if "purvapaksha" in positions and "siddhanta" in positions:
        order_ok = positions["purvapaksha"] < positions["siddhanta"]
    else:
        order_ok = False

    score = 1 if (all_present and order_ok) else 0
    details = {
        "steps_found": found,
        "order_correct": order_ok,
    }
    return score, details


def score_purvapaksha_quality(response: str, expected_sources: list[str]) -> tuple[int, dict]:
    """
    Dimension 2: Purvapaksha Quality (0–3).
    """
    # Extract purvapaksha section if possible
    pp_match = re.search(
        r"(p[uū]rvapak[sṣ]a|purvapaksha|objection:|counter.?argument|ਪੂਰਵਪੱਖ|पूर्वपक्ष|பூர்வபக்ஷம்|எதிர்வாதம்)(.*?)(siddh[aā]nta|siddhanta|established|response:|refut|ਸਿੱਧਾਂਤ|ਸਿਧਾਂਤ|सिद्धांत|सिद्धान्त|சித்தாந்தம்|சித்தாந்த)",
        response,
        re.IGNORECASE | re.DOTALL,
    )
    text = pp_match.group(2) if pp_match else response

    # Check for named philosophers from expected_sources list
    named_found = []
    for source in expected_sources:
        if re.search(re.escape(source), text, re.IGNORECASE):
            named_found.append(source)

    # Broad philosopher check
    broad_named = bool(NAMED_PHILOSOPHERS.search(text))
    school_found = bool(NAMED_SCHOOLS.search(text))
    generic_found = bool(GENERIC_PHRASES.search(text))

    if named_found or broad_named:
        # Substance gate: award D2=3 only when genuine argumentation is present.
        # A named entity alone is not enough — require either an objection verb
        # (in any of the four benchmark languages) or ≥ D2_SUBSTANCE_MIN_WORDS
        # words in the PP section (safety net for long paraphrase without a
        # canonical verb form).
        has_verb = bool(OBJECTION_VERB.search(text))
        has_substance = has_verb or (len(text.split()) >= D2_SUBSTANCE_MIN_WORDS)
        score = 3 if has_substance else 2
    elif school_found:
        score = 2
    elif generic_found:
        score = 1
    else:
        score = 0

    has_verb = bool(OBJECTION_VERB.search(text)) if (named_found or broad_named) else None
    details = {
        "expected_sources_cited": named_found,
        "broad_philosopher_found": broad_named,
        "named_school_found": school_found,
        "generic_only": generic_found and not school_found,
        "substance_verb_found": has_verb,
        "pp_word_count": len(text.split()),
    }
    return score, details


def score_confidence_calibration(
    response: str, domain: str, difficulty: str
) -> tuple[int, dict]:
    """
    Dimension 3: Confidence Calibration (0–2).
    """
    has_signal = bool(CONFIDENCE_PATTERN.search(response))
    if not has_signal:
        return 0, {"signal_present": False}

    # Extract level if available
    level_match = CONFIDENCE_LEVEL_PATTERN.search(response)
    level = None
    if level_match:
        level = (level_match.group(1) or level_match.group(2)).upper()

    calibrated = True
    calibration_note = "default calibrated"

    if level:
        if domain in SPECULATIVE_DOMAINS and level == "HIGH":
            calibrated = False
            calibration_note = f"HIGH confidence inappropriate for speculative domain '{domain}'"
        elif domain in EVIDENCE_DOMAINS and level == "LOW":
            calibrated = False
            calibration_note = f"LOW confidence inappropriate for evidence domain '{domain}'"
        elif difficulty == "hard" and level in ("LOW", "MEDIUM"):
            calibration_note = "Appropriate caution on hard question"
        else:
            calibration_note = f"Level {level} appears appropriate"
    else:
        # Hedging language found but no explicit level
        calibration_note = "Hedging language found, no explicit level — partial credit"
        calibrated = False  # can't fully verify calibration

    score = 2 if calibrated else 1
    details = {
        "signal_present": True,
        "level_detected": level,
        "calibrated": calibrated,
        "note": calibration_note,
    }
    return score, details


def score_language_consistency(response: str, language: str) -> tuple[int, dict]:
    """
    Dimension 4: Language Consistency (0–1).
    """
    if language == "english":
        # For English, check that response isn't accidentally in another script
        non_ascii = sum(1 for c in response if ord(c) > 127)
        total = max(len(response), 1)
        score = 1 if (non_ascii / total < 0.3) else 0
        details = {
            "expected_language": "english",
            "non_ascii_ratio": round(non_ascii / total, 3),
        }
        return score, details

    block_range = {
        "hindi":   UNICODE_BLOCKS["devanagari"],
        "punjabi": UNICODE_BLOCKS["gurmukhi"],
        "tamil":   UNICODE_BLOCKS["tamil"],
    }.get(language)

    if block_range is None:
        return 1, {"note": f"Unknown language '{language}', skipping check"}

    block_chars = sum(
        1 for c in response
        if block_range[0] <= ord(c) <= block_range[1]
    )
    non_ascii_chars = sum(1 for c in response if ord(c) > 127)

    if non_ascii_chars == 0:
        # Response is entirely ASCII — wrong language
        return 0, {
            "expected_language": language,
            "script_chars": 0,
            "non_ascii_chars": 0,
            "ratio": 0.0,
            "note": "Response appears to be in ASCII/English only",
        }

    ratio = block_chars / non_ascii_chars
    score = 1 if ratio >= 0.40 else 0
    details = {
        "expected_language": language,
        "script_chars": block_chars,
        "non_ascii_chars": non_ascii_chars,
        "script_ratio": round(ratio, 3),
    }
    return score, details


def score_siddhanta_quality(response: str) -> tuple[int, dict]:
    """
    Dimension 5: Siddhanta Quality (0–2).
    """
    # Try to extract siddhanta section
    sd_match = re.search(
        r"(siddh[aā]nta|established view|response:|refutation:|ਸਿੱਧਾਂਤ|ਸਿਧਾਂਤ|सिद्धांत|सिद्धान्त|सिद्धान्त|सिद्धान्त|சித்தாந்தம்|சித்தாந்த|சித்தாந்தம்)(.*?)$",
        response,
        re.IGNORECASE | re.DOTALL,
    )
    text = sd_match.group(2).strip() if sd_match else response

    has_backref = bool(SIDDHANTA_BACKREF.search(text))
    if not has_backref:
        return 0, {"backref_found": False}

    has_named = bool(NAMED_PHILOSOPHERS.search(text))
    has_technical = bool(TECHNICAL_VOCAB.search(text))
    has_school = bool(NAMED_SCHOOLS.search(text))

    if has_named or has_technical or has_school:
        score = 2
    else:
        score = 1

    details = {
        "backref_found": True,
        "named_source_found": has_named,
        "technical_vocab_found": has_technical,
        "named_school_found": has_school,
    }
    return score, details


def score_response(question: dict, response: str) -> dict:
    """Score a single response against all 5 dimensions."""
    d1_score, d1_det = score_format_adherence(response)
    d2_score, d2_det = score_purvapaksha_quality(
        response, question.get("expected_purvapaksha_sources", [])
    )
    d3_score, d3_det = score_confidence_calibration(
        response, question.get("domain", ""), question.get("difficulty", "standard")
    )
    d4_score, d4_det = score_language_consistency(
        response, question.get("language", "english")
    )
    d5_score, d5_det = score_siddhanta_quality(response)

    total = d1_score + d2_score + d3_score + d4_score + d5_score
    passed = total >= 6

    return {
        "id": question["id"],
        "question": question["question"],
        "language": question.get("language"),
        "domain": question.get("domain"),
        "difficulty": question.get("difficulty", "standard"),
        "scores": {
            "format_adherence":         d1_score,
            "purvapaksha_quality":      d2_score,
            "confidence_calibration":   d3_score,
            "language_consistency":     d4_score,
            "siddhanta_quality":        d5_score,
            "total":                    total,
        },
        "passed": passed,
        "details": {
            "format_adherence":       d1_det,
            "purvapaksha_quality":    d2_det,
            "confidence_calibration": d3_det,
            "language_consistency":   d4_det,
            "siddhanta_quality":      d5_det,
        },
        "response_length": len(response),
    }


# ---------------------------------------------------------------------------
# Model interaction
# ---------------------------------------------------------------------------

def call_model(model: str, question: str, timeout: int = 120) -> str:
    """Call ollama model via REST API with thinking disabled.

    Uses the ollama HTTP API (localhost:11434) rather than the subprocess CLI so
    we can pass `think: false` — required for Qwen3 models to skip extended
    chain-of-thought and return within a reasonable timeout.
    """
    import urllib.request
    import urllib.error

    payload = json.dumps({
        "model": model,
        "prompt": question,
        "think": False,
        "stream": False,
        "options": {
            "num_predict": 2048,   # cap output tokens so long answers don't stall
        },
    }).encode("utf-8")

    req = urllib.request.Request(
        "http://localhost:11434/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            return body.get("response", "").strip()
    except TimeoutError:
        raise RuntimeError(f"ollama API timed out after {timeout}s for: {question[:80]}")
    except urllib.error.URLError as e:
        raise RuntimeError(f"ollama API error: {e}")


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def print_summary_table(results: list[dict]) -> None:
    """Print a formatted summary table to stdout."""
    header = (
        f"{'ID':<10} {'Lang':<8} {'Domain':<25} {'D1':>3} {'D2':>3} "
        f"{'D3':>3} {'D4':>3} {'D5':>3} {'Tot':>4} {'Pass':>5}"
    )
    print("\n" + "=" * len(header))
    print("NyayaBench v1.0 — Results")
    print("=" * len(header))
    print(header)
    print("-" * len(header))

    for r in results:
        s = r["scores"]
        passed_str = "YES" if r["passed"] else "no"
        print(
            f"{r['id']:<10} {r['language']:<8} {r['domain']:<25} "
            f"{s['format_adherence']:>3} {s['purvapaksha_quality']:>3} "
            f"{s['confidence_calibration']:>3} {s['language_consistency']:>3} "
            f"{s['siddhanta_quality']:>3} {s['total']:>4} {passed_str:>5}"
        )

    print("-" * len(header))

    n = len(results)
    if n == 0:
        print("No results to summarize.")
        return

    pass_count = sum(1 for r in results if r["passed"])
    total_score = sum(r["scores"]["total"] for r in results)
    max_score = 9 * n
    nyaya_bench_score = (total_score / max_score * 100) if max_score > 0 else 0
    pass_rate = (pass_count / n * 100) if n > 0 else 0

    avg_d = {
        "D1": sum(r["scores"]["format_adherence"] for r in results) / n,
        "D2": sum(r["scores"]["purvapaksha_quality"] for r in results) / n,
        "D3": sum(r["scores"]["confidence_calibration"] for r in results) / n,
        "D4": sum(r["scores"]["language_consistency"] for r in results) / n,
        "D5": sum(r["scores"]["siddhanta_quality"] for r in results) / n,
    }

    print(f"\nQuestions evaluated : {n}")
    print(f"Questions passed    : {pass_count} / {n}  ({pass_rate:.1f}%)")
    print(f"Total score         : {total_score} / {max_score}")
    print(f"NyayaBench Score    : {nyaya_bench_score:.1f}%")
    print(f"Average by dim      : D1={avg_d['D1']:.2f} D2={avg_d['D2']:.2f} "
          f"D3={avg_d['D3']:.2f} D4={avg_d['D4']:.2f} D5={avg_d['D5']:.2f}")

    # Overall verdict
    passes_benchmark = (nyaya_bench_score >= 67.0 and pass_rate >= 70.0)
    print("\n" + ("=" * len(header)))
    if passes_benchmark:
        print("VERDICT: PASSES NyayaBench v1.0 (score >= 67%, pass rate >= 70%)")
    else:
        reasons = []
        if nyaya_bench_score < 67.0:
            reasons.append(f"score {nyaya_bench_score:.1f}% < 67%")
        if pass_rate < 70.0:
            reasons.append(f"pass rate {pass_rate:.1f}% < 70%")
        print(f"VERDICT: FAILS NyayaBench v1.0 — {'; '.join(reasons)}")
    print("=" * len(header) + "\n")


def build_summary(results: list[dict], model: str) -> dict:
    """Build a structured summary dict for the results JSON."""
    n = len(results)
    if n == 0:
        return {}
    pass_count = sum(1 for r in results if r["passed"])
    total_score = sum(r["scores"]["total"] for r in results)
    max_score = 9 * n
    nyaya_bench_score = round((total_score / max_score * 100), 2) if max_score > 0 else 0
    pass_rate = round((pass_count / n * 100), 2)

    by_language: dict[str, dict] = {}
    by_domain: dict[str, dict] = {}
    for r in results:
        for bucket, key in [(by_language, r["language"]), (by_domain, r["domain"])]:
            if key not in bucket:
                bucket[key] = {"count": 0, "total": 0, "passed": 0}
            bucket[key]["count"] += 1
            bucket[key]["total"] += r["scores"]["total"]
            bucket[key]["passed"] += int(r["passed"])

    return {
        "model": model,
        "questions_evaluated": n,
        "questions_passed": pass_count,
        "pass_rate_pct": pass_rate,
        "total_score": total_score,
        "max_score": max_score,
        "nyaya_bench_score_pct": nyaya_bench_score,
        "passes_benchmark": (nyaya_bench_score >= 67.0 and pass_rate >= 70.0),
        "averages": {
            "format_adherence":       round(sum(r["scores"]["format_adherence"] for r in results) / n, 3),
            "purvapaksha_quality":    round(sum(r["scores"]["purvapaksha_quality"] for r in results) / n, 3),
            "confidence_calibration": round(sum(r["scores"]["confidence_calibration"] for r in results) / n, 3),
            "language_consistency":   round(sum(r["scores"]["language_consistency"] for r in results) / n, 3),
            "siddhanta_quality":      round(sum(r["scores"]["siddhanta_quality"] for r in results) / n, 3),
        },
        "by_language": {
            k: {
                "avg_score": round(v["total"] / v["count"], 3),
                "pass_rate_pct": round(v["passed"] / v["count"] * 100, 1),
            }
            for k, v in by_language.items()
        },
        "by_domain": {
            k: {
                "avg_score": round(v["total"] / v["count"], 3),
                "pass_rate_pct": round(v["passed"] / v["count"] * 100, 1),
            }
            for k, v in by_domain.items()
        },
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="NyayaBench v1.0 — Epistemic Reasoning Evaluator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument(
        "--model", default="iyra-v6",
        help="Ollama model name to evaluate (default: iyra-v6)",
    )
    p.add_argument(
        "--questions",
        default=str(Path(__file__).parent / "questions.json"),
        help="Path to questions JSON file",
    )
    p.add_argument(
        "--output", default=None,
        help="Output JSON file path (default: results/results_<timestamp>.json)",
    )
    p.add_argument(
        "--dry-run", metavar="RESULTS_JSON", default=None,
        help="Score a saved results JSON instead of calling ollama. "
             "Pass a JSON with a 'raw_responses' key.",
    )
    p.add_argument(
        "--ids", nargs="*", default=None,
        help="Only evaluate specific question IDs (e.g. NB-001 NB-005)",
    )
    p.add_argument(
        "--timeout", type=int, default=120,
        help="Seconds to wait for each ollama response (default: 120)",
    )
    p.add_argument(
        "--verbose", action="store_true",
        help="Print each question and response as it is evaluated",
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()

    # Load questions
    questions_path = Path(args.questions)
    if not questions_path.exists():
        print(f"ERROR: Questions file not found: {questions_path}", file=sys.stderr)
        sys.exit(1)

    with open(questions_path, encoding="utf-8") as f:
        questions_data = json.load(f)

    all_questions: list[dict] = questions_data["questions"]

    # Filter by ID if requested
    if args.ids:
        id_set = set(args.ids)
        all_questions = [q for q in all_questions if q["id"] in id_set]
        if not all_questions:
            print(f"ERROR: No questions matched IDs: {args.ids}", file=sys.stderr)
            sys.exit(1)
        print(f"Evaluating {len(all_questions)} questions: {[q['id'] for q in all_questions]}")

    # Set up output path
    if args.output:
        output_path = Path(args.output)
    else:
        results_dir = Path(__file__).parent / "results"
        results_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = results_dir / f"results_{ts}.json"

    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Dry-run mode: load saved responses and re-score
    if args.dry_run:
        dry_path = Path(args.dry_run)
        if not dry_path.exists():
            print(f"ERROR: Dry-run file not found: {dry_path}", file=sys.stderr)
            sys.exit(1)
        with open(dry_path, encoding="utf-8") as f:
            saved = json.load(f)

        raw_responses: dict[str, str] = saved.get("raw_responses", {})
        if not raw_responses:
            print(
                "ERROR: dry-run JSON must have a 'raw_responses' key mapping question ID -> response string.",
                file=sys.stderr,
            )
            sys.exit(1)

        print(f"\nDry-run mode: re-scoring {len(raw_responses)} saved responses...")
        results = []
        for q in all_questions:
            if q["id"] not in raw_responses:
                continue
            response = raw_responses[q["id"]]
            result = score_response(q, response)
            result["response"] = response
            results.append(result)
    else:
        # Live evaluation
        print(f"\nNyayaBench v1.0 — Evaluating model: {args.model}")
        print(f"Questions: {len(all_questions)}")
        print(f"Output: {output_path}\n")

        results = []
        raw_responses: dict[str, str] = {}

        # Language instruction prefixes ensure the model responds in the
        # correct language regardless of the Modelfile's default bias.
        LANG_PREFIX = {
            "english": "Please respond in English. ",
            "hindi":   "कृपया हिंदी में उत्तर दें। ",
            "punjabi": "ਕਿਰਪਾ ਕਰਕੇ ਪੰਜਾਬੀ ਵਿੱਚ ਜਵਾਬ ਦਿਓ। ",
            "tamil":   "தயவுசெய்து தமிழில் பதிலளிக்கவும். ",
        }

        for i, q in enumerate(all_questions, 1):
            qid = q["id"]
            lang = q.get("language", "english")
            domain = q.get("domain", "unknown")
            prefix = LANG_PREFIX.get(lang, "")
            question_text = prefix + q["question"]

            print(f"[{i:3d}/{len(all_questions)}] {qid} ({lang}, {domain})... ", end="", flush=True)

            try:
                response = call_model(args.model, question_text, timeout=args.timeout)
            except RuntimeError as e:
                print(f"ERROR: {e}")
                response = ""

            raw_responses[qid] = response
            result = score_response(q, response)
            result["response"] = response
            results.append(result)

            total = result["scores"]["total"]
            passed = "PASS" if result["passed"] else "fail"
            print(f"score={total}/9 [{passed}]")

            if args.verbose:
                print(f"  Response ({len(response)} chars):\n  {response[:300]}...\n")

    # Save results
    output_data = {
        "meta": {
            "version": "NyayaBench v1.0",
            "model": args.model,
            "timestamp": datetime.now().isoformat(),
            "questions_file": str(questions_path),
            "total_evaluated": len(results),
        },
        "summary": build_summary(results, args.model),
        "raw_responses": {r["id"]: r.get("response", "") for r in results},
        "results": [
            {k: v for k, v in r.items() if k != "response"}
            for r in results
        ],
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    print(f"\nResults saved to: {output_path}")
    print_summary_table(results)


if __name__ == "__main__":
    main()
