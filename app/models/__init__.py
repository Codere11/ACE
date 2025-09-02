# Make `from app.models import User, Tenant, ConversationFlow` work
from .core import Tenant, User, ConversationFlow  # re-export

# If someone imports Base from here, forward it (optional convenience)
try:
    from app.services.db import Base  # not required, but handy
except Exception:
    Base = None  # avoid import errors during tooling
