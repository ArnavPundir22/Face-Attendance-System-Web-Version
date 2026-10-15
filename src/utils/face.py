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
model = insightface.app.FaceAnalysis(name='buffalo_l')

det_size = (config.INSIGHTFACE_DET_SIZE, config.INSIGHTFACE_DET_SIZE)
try:
    model.prepare(ctx_id=config.INSIGHTFACE_CTX_ID, det_size=det_size)
    logger.info(f"InsightFace model initialized with ctx_id={config.INSIGHTFACE_CTX_ID}, det_size={det_size}")
except Exception as e:
    logger.warning(f"Failed to initialize InsightFace with ctx_id={config.INSIGHTFACE_CTX_ID} ({e}). Falling back to CPU (ctx_id=-1).")
    model.prepare(ctx_id=-1, det_size=det_size)

def normalize_embedding(arr: np.ndarray | list | str) -> np.ndarray | None:
    """Return an L2-normalised copy of *arr* (float32 ndarray), or ``None`` if invalid or zero norm."""
    if arr is None:
        return None
    if isinstance(arr, str):
        import json
        arr = arr.strip()
        if not arr:
            return None
        try:
            arr = json.loads(arr)
        except Exception:
            cleaned = arr.strip('[] \t\n\r')
            arr = [float(x.strip()) for x in cleaned.split(',') if x.strip()]
    try:
        arr = np.array(arr, dtype=np.float32)
    except Exception:
        return None
    norm = np.linalg.norm(arr)
    if norm == 0 or np.isnan(norm):
        return None
    return arr / norm

