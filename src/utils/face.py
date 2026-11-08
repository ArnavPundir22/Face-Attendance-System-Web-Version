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

# ---------------------------------------------------------------------------
# Thread-safe inference serialization (R3)
# ---------------------------------------------------------------------------
import _thread


class _InferenceRLock(_thread.RLock):
    """Re-entrant lock with explicit locked() state query support."""
    def locked(self) -> bool:
        if self._is_owned():
            return True
        if self.acquire(blocking=False):
            self.release()
            return False
        return True


_inference_lock = _InferenceRLock()
_raw_model_get = model.get


def _threadsafe_model_get(*args, **kwargs):
    """Instance wrapper guaranteeing any direct model.get call is serialized."""
    with _inference_lock:
        return _raw_model_get(*args, **kwargs)


# Wrap model.get directly on the instance as defense-in-depth
model.get = _threadsafe_model_get


def extract_faces(image):
    """
    Thread-safe face detection and feature extraction using InsightFace.
    Serializes ONNX Runtime inference to prevent OpenMP CPU starvation.
    """
    if image is None:
        return []
    with _inference_lock:
        return model.get(image)


get_faces_threadsafe = extract_faces

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
            try:
                cleaned = arr.strip('[] \t\n\r')
                if not cleaned:
                    return None
                arr = [float(x.strip()) for x in cleaned.split(',') if x.strip()]
            except Exception:
                return None
    try:
        arr = np.array(arr, dtype=np.float32)
    except Exception:
        return None
    if arr.size == 0 or np.any(np.isnan(arr)) or np.any(np.isinf(arr)):
        return None
    norm = np.linalg.norm(arr)
    if norm == 0 or np.isnan(norm) or np.isinf(norm):
        return None
    return arr / norm

