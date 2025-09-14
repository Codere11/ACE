from typing import Dict, Any

def _clamp(v: float, lo: float = 0, hi: float = 100) -> int:
    try:
        return int(max(lo, min(hi, round(float(v)))))
    except Exception:
        return 0

def _interest_from(score: int) -> str:
    if score >= 80:
        return "High"
    if score >= 55:
        return "Medium"
    return "Low"

def _normalize_clinic_to_legacy(qual: Dict[str, Any]) -> Dict[str, Any]:
    """
    Map clinic keys -> legacy scoring keys (without breaking existing callers).
    Input may contain any of:
      service: 'emergency'|'preventive'|'aesthetic'
      urgency: 'p1'|'p2'|'p3'
      time_pref: 'am'|'pm'|'weekend'|'flex'
      payment: 'zzzs'|'private'|'unknown'
      med: 'pregnancy'|'anticoagulants'|'allergies'|'none'
      history: 'ours'|'other'|'none'
    Legacy keys we synthesize when missing:
      finance, when, motivation
    """
    out = dict(qual)  # shallow copy

    # urgency -> when/motivation
    urg = (qual.get("urgency") or "").lower()
    if "when" not in out:
        if urg == "p1":
            out["when"] = "this_week"
        elif urg == "p2":
            out["when"] = "next_week"
        elif urg == "p3":
            out["when"] = "later"
    if "motivation" not in out:
        if urg == "p1":
            out["motivation"] = "high"
        elif urg == "p2":
            out["motivation"] = "medium"
        elif urg == "p3":
            out["motivation"] = "low"

    # payment -> finance (approximation for scoring consistency)
    pay = (qual.get("payment") or "").lower()
    if "finance" not in out:
        if pay == "private":
            out["finance"] = "cash"          # ready to pay
        elif pay == "zzzs":
            out["finance"] = "in_progress"   # may require admin/limits
        else:
            out["finance"] = ""              # unknown/neutral

    return out

def score_from_qual(qual: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deterministic scoring from structured 'qual' signals.

    Supported (optional) legacy keys (real-estate era):
      - fit           : 'good'|'close'|'low'
      - finance       : 'cash'|'preapproved'|'in_progress'
      - when          : 'this_week'|'next_week'|'weekend'|'later'
      - motivation    : 'high'|'medium'|'low'
      - reason        : 'price_high'|'location'|'size'
      - fit_intent    : 'yes'|'maybe'|'no'

    New clinic keys (MVP):
      - service       : 'emergency'|'preventive'|'aesthetic'
      - urgency       : 'p1'|'p2'|'p3'
      - time_pref     : 'am'|'pm'|'weekend'|'flex'
      - payment       : 'zzzs'|'private'|'unknown'
      - med           : 'pregnancy'|'anticoagulants'|'allergies'|'none'
      - history       : 'ours'|'other'|'none'

    Returns:
      { compatibility: 0..100, interest: 'High'|'Medium'|'Low', pitch: str, reasons: str }
    """
    # First, adapt clinic payloads to legacy signals (non-destructive)
    qual = _normalize_clinic_to_legacy(qual)

    reasons: list[str] = []

    # ---- HARD OVERRIDES ----
    if (qual.get("fit_intent") or "").lower() == "no":
        score = 0
        reasons.append("Intent: no")
        interest = _interest_from(0)
        pitch = "Razumem. Lahko predlagam alternative, če želite."
        return {
            "compatibility": 0,
            "interest": interest,
            "pitch": pitch,
            "reasons": "; ".join(reasons),
        }

    # ---- BASELINE ----
    score = 50.0

    # Clinic-specific nudges (do not exist in real-estate scorer)
    service = (qual.get("service") or "").lower()
    if service == "emergency":
        score += 10; reasons.append("Storitev: emergency")
    elif service == "aesthetic":
        score += 5; reasons.append("Storitev: aesthetic")
    elif service == "preventive":
        score += 0; reasons.append("Storitev: preventive")

    # Time preference: small, neutral nudges
    tpref = (qual.get("time_pref") or "").lower()
    if tpref == "weekend":
        score += 3; reasons.append("Časovna preferenca: weekend")
    elif tpref in ("am", "pm"):
        score += 2; reasons.append(f"Časovna preferenca: {tpref}")
    elif tpref == "flex":
        score += 1; reasons.append("Časovna preferenca: flex")

    # Medical flags: tiny negative due to scheduling/complexity (not rejection)
    med = (qual.get("med") or "").lower()
    if med == "anticoagulants":
        score -= 5; reasons.append("Med: anticoagulants")
    elif med == "pregnancy":
        score -= 3; reasons.append("Med: pregnancy")
    elif med == "allergies":
        score -= 2; reasons.append("Med: allergies")
    elif med == "none":
        reasons.append("Med: none")

    # History: small positive if already a patient
    history = (qual.get("history") or "").lower()
    if history == "ours":
        score += 5; reasons.append("Zgodovina: ours")
    elif history == "other":
        score += 0; reasons.append("Zgodovina: other")
    elif history == "none":
        score += 0; reasons.append("Zgodovina: none")

    # ---- Legacy signals (kept for backward compatibility) ----
    fit = (qual.get("fit") or "").lower()
    if fit == "good":
        score += 25; reasons.append("Ujemanje: good")
    elif fit == "close":
        score += 10; reasons.append("Ujemanje: close")
    elif fit == "low":
        score -= 25; reasons.append("Ujemanje: low")

    finance = (qual.get("finance") or "").lower()
    if finance == "cash":
        score += 20; reasons.append("Finance: cash")
    elif finance == "preapproved":
        score += 15; reasons.append("Finance: preapproved")
    elif finance == "in_progress":
        score += 5; reasons.append("Finance: in_progress")

    when = (qual.get("when") or "").lower()
    if when == "this_week":
        score += 15; reasons.append("Čas: this_week")
    elif when == "next_week":
        score += 10; reasons.append("Čas: next_week")
    elif when == "weekend":
        score += 8; reasons.append("Čas: weekend")
    elif when == "later":
        score -= 10; reasons.append("Čas: later")

    motivation = (qual.get("motivation") or "").lower()
    if motivation == "high":
        score += 15; reasons.append("Motivacija: high")
    elif motivation == "medium":
        score += 5; reasons.append("Motivacija: medium")
    elif motivation == "low":
        score -= 10; reasons.append("Motivacija: low")

    alt_reason = (qual.get("reason") or "").lower()
    if alt_reason == "price_high":
        score -= 25; reasons.append("Razlog: price_high")
    elif alt_reason in ("location", "size"):
        score -= 15; reasons.append(f"Razlog: {alt_reason}")

    fit_intent = (qual.get("fit_intent") or "").lower()
    if fit_intent == "yes":
        score += 10; reasons.append("Intent: yes")
    elif fit_intent == "maybe":
        score += 0; reasons.append("Intent: maybe")

    score_i = _clamp(score)
    interest = _interest_from(score_i)

    # User-facing pitch
    if interest == "High":
        # If emergency, suggest fast-track wording
        pitch = "Predlagam, da uskladimo najhitrejši možni termin."
    elif interest == "Medium":
        pitch = "Lahko pošljem več informacij ali predlagam termin."
    else:
        pitch = "Lahko predlagam alternative ali dodatna pojasnila."

    return {
        "compatibility": score_i,
        "interest": interest,
        "pitch": pitch,
        "reasons": "; ".join(reasons),
    }
