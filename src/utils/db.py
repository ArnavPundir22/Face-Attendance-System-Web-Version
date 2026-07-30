"""
Database utility — BioSecure AI.

Provides two Supabase clients:
  supabase       — uses the ANON key for least-privilege public/RLS operations.
                   Falls back to the service-role key if SUPABASE_ANON_KEY is unset.
  supabase_admin — uses the SERVICE ROLE key; bypasses Row Level Security.
                   Only use for admin-only routes (blueprints/admin.py).

Also exports:
  is_valid_email(email) -> bool
"""

import logging
import os

from dotenv import load_dotenv
from supabase import Client, create_client

logger = logging.getLogger(__name__)

load_dotenv()

SUPABASE_URL: str = os.environ.get("SUPABASE_URL", "")
SUPABASE_SERVICE_ROLE_KEY: str = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
SUPABASE_ANON_KEY: str = os.environ.get("SUPABASE_ANON_KEY", "")

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    raise ValueError(
        "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set. "
        "Copy .env.example to .env and fill in your Supabase credentials."
    )

# ---------------------------------------------------------------------------
# Admin client — full access, bypasses RLS.  Use only in /admin/* routes.
# ---------------------------------------------------------------------------
supabase_admin: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
logger.debug("Supabase admin client initialised.")

# ---------------------------------------------------------------------------
# Standard client — anon key preferred; falls back to service role if not set.
# ---------------------------------------------------------------------------
_public_key = SUPABASE_ANON_KEY or SUPABASE_SERVICE_ROLE_KEY
if not SUPABASE_ANON_KEY:
    logger.warning(
        "SUPABASE_ANON_KEY is not set. The standard Supabase client will use "
        "the service-role key. Set SUPABASE_ANON_KEY for proper least-privilege access."
    )

supabase: Client = create_client(SUPABASE_URL, _public_key)
logger.debug("Supabase standard client initialised.")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def is_valid_email(email: str) -> bool:
    """Return True if *email* passes a basic structural check."""
    from email.utils import parseaddr

    _, addr = parseaddr(email)
    if not addr or "@" not in addr:
        return False
    local, domain = addr.rsplit("@", 1)
    return bool(local) and bool(domain) and "." in domain
