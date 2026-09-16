"""
Face recognition state and helpers.

Migrated to pgvector. This module now only handles the InsightFace model loading.
"""

import logging
import insightface
import numpy as np

from src import config

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# InsightFace model (loaded once at import time)
# ---------------------------------------------------------------------------
try:
    model.prepare(ctx_id=config.INSIGHTFACE_CTX_ID)
    logger.info(f"InsightFace model initialized with ctx_id={config.INSIGHTFACE_CTX_ID}")
except Exception as e:
    logger.warning(f"Failed to initialize InsightFace with ctx_id={config.INSIGHTFACE_CTX_ID} ({e}). Falling back to CPU (ctx_id=-1).")
    model.prepare(ctx_id=-1)

def normalize_embedding(arr: np.ndarray) -> np.ndarray | None:
    """Return an L2-normalised copy of *arr*, or ``None`` if the norm is zero."""
    arr = np.array(arr, dtype=np.float32)
    norm = np.linalg.norm(arr)
    if norm == 0:
        return None
    return arr / norm
