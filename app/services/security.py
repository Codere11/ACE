# app/services/security.py
"""
Robust password hashing utilities:
- Prefer passlib (bcrypt)
- Fallback to python-bcrypt if passlib isn't available
- Dev-only final fallback (sha256) so the app can still boot
"""
from __future__ import annotations
import hashlib
import hmac

# Try passlib
try:
    from passlib.context import CryptContext  # type: ignore
    _PASSLIB = True
except Exception:
    _PASSLIB = False

# Try python-bcrypt
try:
    import bcrypt as _bcrypt  # type: ignore
    _BCRYPT = True
except Exception:
    _BCRYPT = False


def _is_bcrypt_hash(h: str) -> bool:
    return isinstance(h, str) and h.startswith("$2")


if _PASSLIB:
    # Best option
    _pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")

    def hash_password(raw: str) -> str:
        return _pwd.hash(raw)

    def verify_password(raw: str, hashed: str) -> bool:
        try:
            return _pwd.verify(raw, hashed)
        except Exception:
            return False

else:
    # Fallbacks
    def hash_password(raw: str) -> str:
        if _BCRYPT:
            return _bcrypt.hashpw(raw.encode("utf-8"), _bcrypt.gensalt()).decode("utf-8")
        # DEV-ONLY weak fallback so app still runs
        return "sha256$" + hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def verify_password(raw: str, hashed: str) -> bool:
        if not isinstance(hashed, str):
            return False
        # If we have bcrypt and stored hash is bcrypt -> verify properly
        if _BCRYPT and _is_bcrypt_hash(hashed):
            try:
                return _bcrypt.checkpw(raw.encode("utf-8"), hashed.encode("utf-8"))
            except Exception:
                return False
        # Dev-only sha256 fallback
        if hashed.startswith("sha256$"):
            want = hashed.split("$", 1)[1]
            got = hashlib.sha256(raw.encode("utf-8")).hexdigest()
            return hmac.compare_digest(want, got)
        # Last resort: support legacy plaintext (not recommended)
        return hmac.compare_digest(raw, hashed)


def looks_like_hash(s: str) -> bool:
    return isinstance(s, str) and (s.startswith("$2") or s.startswith("sha256$"))
