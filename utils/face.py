"""
Face recognition state and helpers.

Migrated to pgvector. This module now only handles the InsightFace model loading.
"""

import logging
import insightface
import numpy as np

import config

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# InsightFace model (loaded once at import time)
# ---------------------------------------------------------------------------
model = insightface.app.FaceAnalysis(name='buffalo_l')
model.prepare(ctx_id=config.INSIGHTFACE_CTX_ID)

def normalize_embedding(arr: np.ndarray) -> np.ndarray | None:
    """Return an L2-normalised copy of *arr*, or ``None`` if the norm is zero."""
    arr = np.array(arr, dtype=np.float32)
    norm = np.linalg.norm(arr)
    if norm == 0:
        return None
    return arr / norm
