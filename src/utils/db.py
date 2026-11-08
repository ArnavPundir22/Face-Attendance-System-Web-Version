"""
Database utility — BioSecure AI.

Provides two Supabase clients:
  supabase       — uses the ANON key for least-privilege public/RLS operations.
                   Falls back to the service-role key if SUPABASE_ANON_KEY is unset.
  supabase_admin — uses the SERVICE ROLE key; bypasses Row Level Security.
                   Only use for admin-only routes (blueprints/admin.py).

Also exports:
  fetch_all_records(client, table_name, ...) -> list[dict]
  is_valid_email(email) -> bool
"""

import logging
import os
from typing import Any, Dict, List, Optional

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


def fetch_all_records(
    client: Client,
    table_name: str,
    select_fields: Optional[str] = None,
    order_field: Optional[str] = None,
    batch_size: int = 1000,
    desc: bool = False,
) -> List[Dict[str, Any]]:
    """
    Fetch all records from a Supabase table using range-based pagination.
    Overcomes the PostgREST 1,000-row limit without statement timeouts.

    :param client: Initialized Supabase Client (supabase or supabase_admin)
    :param table_name: Database table name (e.g. 'students')
    :param select_fields: Explicit comma-separated columns to project (e.g. 'id, name').
                         Wildcard '*' and empty projections are prohibited to prevent unbounded egress.
    :param order_field: Column or comma-separated columns for deterministic ordering
    :param batch_size: Number of records to fetch per page (defaults to 1000)
    :param desc: Whether to sort descending (defaults to False, ascending)
    :return: List of all record dictionaries
    """
    tokens = [f.strip() for f in select_fields.split(',') if f.strip()] if select_fields else []
    if not tokens or any('*' in t for t in tokens):
        raise ValueError("Explicit select_fields required; '*' or empty projections are prohibited.")

    records: List[Dict[str, Any]] = []
    start = 0

    while True:
        end = start + batch_size - 1
        query = client.table(table_name).select(select_fields)

        if order_field:
            for field in [f.strip() for f in order_field.split(',') if f.strip()]:
                query = query.order(field, desc=desc)

        res = query.range(start, end).execute()
        data = res.data or []
        records.extend(data)

        if len(data) < batch_size:
            break

        start += batch_size

    return records
