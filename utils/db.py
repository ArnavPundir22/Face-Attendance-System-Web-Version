"""
Database utility functions.

Provides connection helpers, schema initialisation, and user management.
All functions use parameterised queries to prevent SQL injection.
"""

"""
Database utility functions using Supabase SDK.
"""

import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Supabase credentials not found in environment variables.")

# Create the globally accessible Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
supabase_admin: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def is_valid_email(email: str) -> bool:
    """Return True if email is minimally valid."""
    from email.utils import parseaddr
    _, addr = parseaddr(email)
    if not addr or '@' not in addr:
        return False
    local, domain = addr.rsplit('@', 1)
    return bool(local) and bool(domain)

