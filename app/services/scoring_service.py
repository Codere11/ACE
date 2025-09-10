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

def score_from_qual(qual: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deterministic scoring from structured 'qual' signals.
    Keys we understand (all optional):
      - fit           : 'good'|'close'|'low'           (often set by budget step)
      - finance       : 'cash'|'preapproved'|'in_progress'
      - when          : 'this_week'|'next_week'|'weekend'|'later'
      - motivation    : 'high'|'medium'|'low'
      - reason        : 'price_high'|'location'|'size'  (why not a fit)
      - fit_intent    : 'yes'|'maybe'|'no'              (user explicitly said yes/maybe/no)

    Returns:
      { compatibility: int(0..100), interest: 'High'|'Medium'|'Low',
        pitch: str, reasons: str }   (reasons is INTERNAL ONLY)
    """

    reasons: list[str] = []

    # ---- HARD OVERRIDES ----
    if (qual.get("fit_intent") or "").lower() == "no":
        score = 0
        reasons.append("Intent: no")
        interest = _interest_from(score)
        pitch = "Razumem. Lahko predlagam alternative, če želite."
        return {
            "compatibility": score,
            "interest": interest,
            "pitch": pitch,
            "reasons": "; ".join(reasons),
        }

    # ---- BASELINE ----
    score = 50.0

    # Fit (often mapped from budget step)
    fit = (qual.get("fit") or "").lower()
    if fit == "good":
        score += 25; reasons.append("Ujemanje: good")
    elif fit == "close":
        score += 10; reasons.append("Ujemanje: close")
    elif fit == "low":
        score -= 25; reasons.append("Ujemanje: low")

    # Finance
    finance = (qual.get("finance") or "").lower()
    if finance == "cash":
        score += 20; reasons.append("Finance: cash")
    elif finance == "preapproved":
        score += 15; reasons.append("Finance: preapproved")
    elif finance == "in_progress":
        score += 5; reasons.append("Finance: in_progress")

    # Timeline
    when = (qual.get("when") or "").lower()
    if when == "this_week":
        score += 15; reasons.append("Čas: this_week")
    elif when == "next_week":
        score += 10; reasons.append("Čas: next_week")
    elif when == "weekend":
        score += 8; reasons.append("Čas: weekend")
    elif when == "later":
        score -= 10; reasons.append("Čas: later")

    # Motivation
    motivation = (qual.get("motivation") or "").lower()
    if motivation == "high":
        score += 15; reasons.append("Motivacija: high")
    elif motivation == "medium":
        score += 5; reasons.append("Motivacija: medium")
    elif motivation == "low":
        score -= 10; reasons.append("Motivacija: low")

    # Negative reasons (from alternative path)
    alt_reason = (qual.get("reason") or "").lower()
    if alt_reason == "price_high":
        score -= 25; reasons.append("Razlog: price_high")
    elif alt_reason in ("location", "size"):
        score -= 15; reasons.append(f"Razlog: {alt_reason}")

    # Soft intent (yes/maybe)
    fit_intent = (qual.get("fit_intent") or "").lower()
    if fit_intent == "yes":
        score += 10; reasons.append("Intent: yes")
    elif fit_intent == "maybe":
        score += 0; reasons.append("Intent: maybe")

    score_i = _clamp(score)
    interest = _interest_from(score_i)

    # User-facing pitch (no numbers; dashboard sees numbers/interest directly)
    if interest == "High":
        pitch = "Predlagam, da uskladimo termin ogleda."
    elif interest == "Medium":
        pitch = "Lahko pošljem več informacij ali predlagam ogled."
    else:
        pitch = "Lahko predlagam alternative ali dodatna pojasnila."

    return {
        "compatibility": score_i,
        "interest": interest,
        "pitch": pitch,
        "reasons": "; ".join(reasons),
    }
