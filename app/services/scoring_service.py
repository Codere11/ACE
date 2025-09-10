from typing import Dict, Any, Tuple, List
from app.core.config import FLOW

DEFAULT_THRESHOLDS = {"High": 70, "Medium": 40, "Low": 0}
DEFAULT_WEIGHTS = {
    "fit":        {"good": 40, "close": 25, "low": 8},
    "finance":    {"cash": 25, "preapproved": 20, "in_progress": 10},
    "when":       {"this_week": 25, "next_week": 20, "weekend": 20, "later": 8},
    "motivation": {"high": 25, "medium": 15, "low": 8},
    "reason_penalty": {"price_high": -20, "location": -15, "size": -10},
}

def _cfg() -> Tuple[Dict[str, Any], Dict[str, int]]:
    sc = (FLOW.get("scoring") or {})
    thresholds = sc.get("thresholds") or DEFAULT_THRESHOLDS
    weights = sc.get("weights") or DEFAULT_WEIGHTS
    return weights, {k: int(v) for k, v in thresholds.items()}

def _interest_from_score(score: int, th: Dict[str, int]) -> str:
    if score >= th.get("High", 70): return "High"
    if score >= th.get("Medium", 40): return "Medium"
    return "Low"

def _category_from_score(score: int, th: Dict[str, int]) -> str:
    # slightly stricter than interest
    if score >= max(th.get("High", 70), 75): return "good_fit"
    if score < max(0, th.get("Medium", 40) - 10): return "bad_fit"
    return "could_fit"

def score_from_qual(qual: Dict[str, Any]) -> Dict[str, Any]:
    weights, th = _cfg()
    points = 0
    reasons: List[str] = []
    tags: List[str] = []

    # Positive signals
    fit = (qual.get("fit") or "").lower()
    if fit in weights["fit"]:
        points += int(weights["fit"][fit]); reasons.append(f"Ujemanje: {fit}"); tags.append(f"fit:{fit}")

    finance = (qual.get("finance") or "").lower()
    if finance in weights["finance"]:
        points += int(weights["finance"][finance]); reasons.append(f"Finance: {finance}"); tags.append(f"finance:{finance}")

    when = (qual.get("when") or "").lower()
    if when in weights["when"]:
        points += int(weights["when"][when]); reasons.append(f"Čas: {when}"); tags.append(f"when:{when}")

    motivation = (qual.get("motivation") or "").lower()
    if motivation in weights["motivation"]:
        points += int(weights["motivation"][motivation]); reasons.append(f"Motivacija: {motivation}"); tags.append(f"motivation:{motivation}")

    # Penalties
    reason = (qual.get("reason") or "").lower()
    if reason in weights["reason_penalty"]:
        points += int(weights["reason_penalty"][reason]); reasons.append(f"Razlog: {reason}"); tags.append(f"reason:{reason}")

    # Clamp 0..100
    score = max(0, min(100, points))
    interest = _interest_from_score(score, th)
    category = _category_from_score(score, th)

    # Simple pitch copy (deterministic)
    if when in ("this_week", "next_week", "weekend"):
        pitch = "Predlagam, da uskladimo termin ogleda."
    elif finance in ("cash", "preapproved"):
        pitch = "Zveni odlično – lahko takoj predlagam termin za ogled."
    else:
        pitch = "Lahko pošljem več informacij in predlog terminov."

    return {
        "category": category,
        "interest": interest,
        "compatibility": score,
        "reasons": "; ".join(reasons),
        "pitch": pitch,
        "tags": tags
    }
