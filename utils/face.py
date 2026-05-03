"""
Face recognition state and helpers.

Encoding storage
----------------
Face embeddings are stored in two safe, pickle-free files:

  EncodeFile_Insight.npy          – float32 numpy matrix, shape (N, D)
  EncodeFile_Insight_names.json   – ordered JSON list of student names (length N)

A one-time migration from the legacy ``EncodeFile_Insight.pkl`` pickle file is
performed automatically on first load so existing deployments keep working.

In-memory structures
--------------------
  known_encoding_dict    – { name: np.ndarray }  — canonical store
  known_embeddings       – list of (embedding, name)  — kept for compatibility
  known_embedding_matrix – (N, D) float32 array of L2-normalised embeddings
  known_embedding_names  – list[str] parallel to matrix rows

Using a pre-built matrix replaces the O(N) Python loop with a single BLAS
matrix-vector multiply (matrix @ query), giving 10-100x speed-up via SIMD.
"""

import json
import logging
import os

import insightface
import numpy as np

import config

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# InsightFace model (loaded once at import time)
# ---------------------------------------------------------------------------
model = insightface.app.FaceAnalysis(name='buffalo_l')
model.prepare(ctx_id=config.INSIGHTFACE_CTX_ID)

# ---------------------------------------------------------------------------
# In-memory encoding state
# ---------------------------------------------------------------------------
known_encoding_dict: dict[str, np.ndarray] = {}
known_embeddings: list[tuple[np.ndarray, str]] = []
known_embedding_matrix: np.ndarray | None = None
known_embedding_names: list[str] = []

os.makedirs(config.KNOWN_FACES_DIR, exist_ok=True)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _rebuild_embedding_matrix() -> None:
    """Rebuild the fast-search matrix from *known_encoding_dict*.

    Called after any change to *known_encoding_dict* so the matrix stays in sync.
    """
    global known_embedding_matrix, known_embedding_names, known_embeddings
    if not known_encoding_dict:
        known_embedding_matrix = None
        known_embedding_names = []
        known_embeddings = []
        return

    names = list(known_encoding_dict.keys())
    matrix = np.array([known_encoding_dict[n] for n in names], dtype=np.float32)
    known_embedding_names = names
    known_embedding_matrix = matrix
    known_embeddings = [(known_encoding_dict[n], n) for n in names]


def _normalize(arr: np.ndarray) -> np.ndarray | None:
    """Return an L2-normalised copy of *arr*, or ``None`` if the norm is zero."""
    arr = np.array(arr, dtype=np.float32)
    norm = np.linalg.norm(arr)
    if norm == 0:
        return None
    return arr / norm


def _load_legacy_pickle() -> dict[str, np.ndarray]:
    """Load encodings from the old pickle file and return a clean dict.

    Only used during the one-time migration.  The pickle module is intentionally
    imported locally to make the security risk explicit and contained.
    """
    import pickle  # noqa: S403 -- only used for one-time migration of existing data

    try:
        with open(config.ENCODE_FILE_LEGACY, 'rb') as fh:
            data = pickle.load(fh)  # noqa: S301
    except Exception:
        logger.exception("Could not read legacy pickle file %s", config.ENCODE_FILE_LEGACY)
        return {}

    if isinstance(data, dict):
        raw = data
    elif isinstance(data, list):
        raw = {}
        for item in data:
            if isinstance(item, (list, tuple)) and len(item) == 2:
                emb, name = item
                try:
                    raw[name] = np.array(emb, dtype=np.float32)
                except Exception:
                    continue
    else:
        return {}

    cleaned: dict[str, np.ndarray] = {}
    for name, emb in raw.items():
        vec = _normalize(emb)
        if vec is not None:
            cleaned[name] = vec
    return cleaned


# ---------------------------------------------------------------------------
# Public load / save API
# ---------------------------------------------------------------------------

def load_encodings_from_file() -> None:
    """Load encodings from disk into the in-memory structures.

    Load order:
      1. New format (.npy matrix + _names.json) — preferred.
      2. Legacy pickle (.pkl) — migrated once, then saved in new format.
    """
    global known_encoding_dict

    matrix_path = config.ENCODE_MATRIX_FILE
    names_path = config.ENCODE_NAMES_FILE
    legacy_path = config.ENCODE_FILE_LEGACY

    enc_dict: dict[str, np.ndarray] = {}

    if os.path.exists(matrix_path) and os.path.exists(names_path):
        # --- New format ---
        try:
            matrix = np.load(matrix_path)
            with open(names_path, 'r', encoding='utf-8') as fh:
                names = json.load(fh)

            if matrix.ndim == 2 and len(names) == matrix.shape[0]:
                for i, name in enumerate(names):
                    vec = _normalize(matrix[i])
                    if vec is not None:
                        enc_dict[name] = vec
            else:
                logger.warning(
                    "Encoding file shape mismatch: matrix %s rows, names %d entries — resetting",
                    matrix.shape[0] if matrix.ndim == 2 else '?',
                    len(names),
                )
        except Exception:
            logger.exception("Failed to load encoding files — starting with empty encodings")
            enc_dict = {}

    elif os.path.exists(legacy_path):
        # --- One-time migration from pickle ---
        logger.info(
            "Migrating face encodings from legacy pickle %s to numpy format …",
            legacy_path,
        )
        enc_dict = _load_legacy_pickle()
        known_encoding_dict = enc_dict
        _rebuild_embedding_matrix()
        save_encodings_to_file()
        logger.info("Migration complete — %d encoding(s) saved in new format.", len(enc_dict))

    known_encoding_dict = enc_dict
    _rebuild_embedding_matrix()


def save_encodings_to_file() -> None:
    """Persist *known_encoding_dict* to disk in the safe numpy format."""
    try:
        names = list(known_encoding_dict.keys())
        if names:
            matrix = np.array(
                [known_encoding_dict[n] for n in names], dtype=np.float32
            )
            np.save(config.ENCODE_MATRIX_FILE, matrix)
        else:
            # Write an empty matrix so the file always exists after a save.
            np.save(config.ENCODE_MATRIX_FILE, np.empty((0, 512), dtype=np.float32))

        with open(config.ENCODE_NAMES_FILE, 'w', encoding='utf-8') as fh:
            json.dump(names, fh, ensure_ascii=False)

    except Exception:
        logger.exception("Failed to save encodings to disk")


def add_or_update_encoding(name: str, new_emb: np.ndarray) -> None:
    """Add or average-update the embedding for *name* in memory and on disk.

    If an embedding already exists for *name* the new one is averaged with the
    stored one (then re-normalised) so multiple photos improve accuracy.
    """
    global known_encoding_dict

    new_vec = _normalize(new_emb)
    if new_vec is None:
        raise ValueError("Embedding has zero norm — cannot store")

    if name in known_encoding_dict:
        existing = known_encoding_dict[name]
        combined = _normalize(existing + new_vec)
        known_encoding_dict[name] = combined if combined is not None else new_vec
    else:
        known_encoding_dict[name] = new_vec

    _rebuild_embedding_matrix()
    save_encodings_to_file()


# Load encodings when this module is first imported.
load_encodings_from_file()
