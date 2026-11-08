"""
In-Memory Biometric Embedding Cache & Batch Matrix Matcher — BioSecure AI.

Stores student 512D ArcFace embeddings in a contiguous NumPy array (float32)
to perform ultra-fast BLAS matrix dot product matching in < 1ms on CPU,
completely bypassing network latency to Supabase pgvector.
"""

import _thread
import logging
import threading
from typing import Any, Dict, List, Optional

import numpy as np

from src import config
from src.utils.db import supabase_admin, fetch_all_records
from src.utils.face import normalize_embedding

logger = logging.getLogger(__name__)


class _InitRLock(_thread.RLock):
    def locked(self) -> bool:
        if self._is_owned():
            return True
        if self.acquire(blocking=False):
            self.release()
            return False
        return True


_cache_lock = threading.Lock()
_init_lock = _InitRLock()
_student_ids: List[str] = []
_student_metadata: Dict[str, Dict[str, Any]] = {}
_embeddings_matrix: Optional[np.ndarray] = None  # Shape: (M, 512)
_is_initialized: bool = False


def reload_face_cache() -> int:
    """
    Fetch all student records and 512D embeddings from Supabase
    and load them into an in-memory NumPy matrix for instant BLAS matching.
    """
    global _student_ids, _student_metadata, _embeddings_matrix, _is_initialized

    with _init_lock:
        try:
            logger.info("Initializing/Reloading in-memory face embedding cache...")
            rows = fetch_all_records(
                client=supabase_admin,
                table_name='students',
                select_fields='id, name, program, branch, enrollment_year, academic_year, gmail, current_ewma_drift, drift_alert_level, embedding',
                order_field='id',
                batch_size=500
            )

            new_ids: List[str] = []
            new_meta: Dict[str, Dict[str, Any]] = {}
            emb_list: List[np.ndarray] = []

            for r in rows:
                sid = r.get('id')
                if not sid:
                    continue

                sid_clean = str(sid).strip()
                new_meta[sid_clean] = {
                    'id': sid_clean,
                    'name': r.get('name', 'Unknown'),
                    'program': r.get('program'),
                    'branch': r.get('branch'),
                    'enrollment_year': r.get('enrollment_year'),
                    'academic_year': r.get('academic_year'),
                    'gmail': r.get('gmail'),
                    'current_ewma_drift': float(r.get('current_ewma_drift') or 0.0),
                    'drift_alert_level': r.get('drift_alert_level') or 'HEALTHY'
                }

                raw_emb = r.get('embedding')
                if not raw_emb:
                    continue

                try:
                    norm_emb = normalize_embedding(raw_emb)
                    if norm_emb is None or norm_emb.shape != (512,):
                        continue

                    new_ids.append(sid_clean)
                    emb_list.append(norm_emb)
                except Exception as err:
                    logger.warning("Skipping invalid embedding for student %s: %s", sid, err)

            new_matrix = np.vstack(emb_list).astype(np.float32) if emb_list else None

            with _cache_lock:
                _embeddings_matrix = new_matrix
                _student_ids = new_ids
                _student_metadata = new_meta
                _is_initialized = True

            if new_matrix is not None:
                logger.info("Face cache reloaded successfully: %d students in matrix memory.", len(new_ids))
            else:
                logger.warning("Face cache reloaded: 0 valid student embeddings found.")

            return len(new_ids)
        except Exception as e:
            logger.error("Failed to reload in-memory face cache from Supabase: %s", e, exc_info=True)
            with _cache_lock:
                return len(_student_ids)


def ensure_cache_initialized():
    """Ensure the cache has been loaded at least once without thundering herd."""
    if _is_initialized:
        return
    with _init_lock:
        if not _is_initialized:
            reload_face_cache()


def match_faces_batch(
    query_embeddings: List[np.ndarray],
    match_threshold: float = config.FACE_MATCH_THRESHOLD
) -> List[Optional[Dict[str, Any]]]:
    """
    Perform batch matrix dot product matching for a list of query embeddings against the cached student matrix.
    
    Returns a list of best match dicts (or None if score < threshold) for each query embedding.
    Runs in < 1ms on CPU using BLAS matrix operations.
    """
    ensure_cache_initialized()

    if not query_embeddings:
        return []

    norm_queries = []
    valid_indices = []
    for idx, q in enumerate(query_embeddings):
        nq = normalize_embedding(q)
        if nq is not None and nq.shape == (512,):
            norm_queries.append(nq)
            valid_indices.append(idx)

    if not norm_queries:
        return [None] * len(query_embeddings)

    with _cache_lock:
        matrix = _embeddings_matrix
        student_ids = list(_student_ids)
        metadata = dict(_student_metadata)

    if matrix is None or len(student_ids) == 0:
        return [None] * len(query_embeddings)

    try:
        Q = np.vstack(norm_queries).astype(np.float32)  # Shape: (N, 512)

        # Matrix multiplication outside _cache_lock:
        # Q (N x 512) . M^T (512 x M) => Cosine Similarity Matrix (N x M)
        sim_matrix = np.dot(Q, matrix.T)

        results: List[Optional[Dict[str, Any]]] = [None] * len(query_embeddings)

        for i, orig_idx in enumerate(valid_indices):
            best_m_idx = int(np.argmax(sim_matrix[i]))
            best_score = float(sim_matrix[i, best_m_idx])

            if best_score >= match_threshold:
                matched_id = student_ids[best_m_idx]
                meta = metadata.get(matched_id, {})
                results[orig_idx] = {
                    'id': matched_id,
                    'name': meta.get('name', 'Unknown'),
                    'similarity': best_score,
                    'program': meta.get('program'),
                    'branch': meta.get('branch'),
                    'enrollment_year': meta.get('enrollment_year')
                }

        return results
    except Exception as e:
        logger.error("Error during in-memory batch face matching: %s", e, exc_info=True)
        return [None] * len(query_embeddings)


def add_student_to_cache(
    student_id: str,
    name: str,
    program: str,
    branch: str,
    embedding: np.ndarray,
    enrollment_year: Optional[int] = None,
    academic_year: Optional[str] = None,
    gmail: Optional[str] = None,
):
    """Dynamically append a new student to the in-memory matrix without reloading full DB."""
    global _student_ids, _embeddings_matrix

    ensure_cache_initialized()

    norm_emb = normalize_embedding(embedding)
    if norm_emb is None or norm_emb.shape != (512,):
        return

    with _cache_lock:
        sid_clean = str(student_id).strip()
        new_row = norm_emb.reshape(1, 512).astype(np.float32)

        if _embeddings_matrix is None or len(_student_ids) == 0:
            _embeddings_matrix = new_row
            _student_ids = [sid_clean]
        else:
            if sid_clean in _student_ids:
                idx = _student_ids.index(sid_clean)
                new_matrix = _embeddings_matrix.copy()
                new_matrix[idx] = norm_emb
                _embeddings_matrix = new_matrix
            else:
                _embeddings_matrix = np.vstack([_embeddings_matrix, new_row])
                _student_ids.append(sid_clean)

        existing_meta = _student_metadata.get(sid_clean, {})
        _student_metadata[sid_clean] = {
            'id': sid_clean,
            'name': name or existing_meta.get('name', 'Unknown'),
            'program': program or existing_meta.get('program'),
            'branch': branch or existing_meta.get('branch'),
            'enrollment_year': (
                enrollment_year
                if enrollment_year is not None
                else existing_meta.get('enrollment_year')
            ),
            'academic_year': (
                academic_year
                if academic_year is not None
                else existing_meta.get('academic_year')
            ),
            'gmail': (
                gmail
                if gmail is not None
                else existing_meta.get('gmail')
            ),
            'current_ewma_drift': 0.0,
            'drift_alert_level': 'HEALTHY'
        }
        logger.info(
            "Added/updated student %s in memory face cache (Total: %d).",
            sid_clean, len(_student_ids)
        )


def remove_student_from_cache(student_id: str) -> bool:
    """
    Remove a student from the in-memory matrix and metadata cache.
    Returns True if the student was present and removed, False otherwise.
    """
    global _embeddings_matrix

    if not student_id or not str(student_id).strip():
        return False

    ensure_cache_initialized()
    sid_clean = str(student_id).strip()

    with _cache_lock:
        removed = False

        if sid_clean in _student_ids:
            idx = _student_ids.index(sid_clean)
            _student_ids.pop(idx)
            if _embeddings_matrix is not None:
                if len(_student_ids) == 0:
                    _embeddings_matrix = None
                else:
                    _embeddings_matrix = np.delete(
                        _embeddings_matrix, idx, axis=0
                    )
            removed = True

        if sid_clean in _student_metadata:
            _student_metadata.pop(sid_clean, None)
            removed = True

        if removed:
            logger.info(
                "Removed student %s from memory face cache (Total: %d).",
                sid_clean, len(_student_ids)
            )

        return removed


def clear_face_cache() -> None:
    """
    Completely clear the in-memory face embedding cache and reset matrix state.
    """
    global _student_ids, _student_metadata, _embeddings_matrix, _is_initialized

    with _cache_lock:
        _student_ids = []
        _student_metadata = {}
        _embeddings_matrix = None
        _is_initialized = False
        logger.info("In-memory face cache cleared.")


def get_student_ewma(student_id: str) -> float:
    """Get the cached EWMA drift score for a student without database queries."""
    ensure_cache_initialized()
    sid = str(student_id).strip()
    with _cache_lock:
        meta = _student_metadata.get(sid, {})
        return float(meta.get('current_ewma_drift') or 0.0)


def update_cached_student_drift(student_id: str, new_ewma: float, alert_level: str):
    """Update in-memory EWMA drift score and alert level for a student."""
    sid = str(student_id).strip()
    with _cache_lock:
        if sid in _student_metadata:
            _student_metadata[sid]['current_ewma_drift'] = new_ewma
            _student_metadata[sid]['drift_alert_level'] = alert_level


def update_student_metadata_cache(
    student_id: str,
    name: str,
    program: str,
    branch: str,
    enrollment_year: Optional[int] = None,
    academic_year: Optional[str] = None,
    gmail: Optional[str] = None,
) -> bool:
    """Update metadata for an existing student in cache without recalculating embedding."""
    ensure_cache_initialized()
    sid_clean = str(student_id).strip()
    with _cache_lock:
        if sid_clean in _student_metadata:
            _student_metadata[sid_clean]['name'] = name
            _student_metadata[sid_clean]['program'] = program
            _student_metadata[sid_clean]['branch'] = branch
            if enrollment_year is not None:
                _student_metadata[sid_clean]['enrollment_year'] = enrollment_year
            if academic_year is not None:
                _student_metadata[sid_clean]['academic_year'] = academic_year
            if gmail is not None:
                _student_metadata[sid_clean]['gmail'] = gmail
            return True
        return False


def get_cached_students() -> List[Dict[str, Any]]:
    """Return a thread-safe snapshot list of all cached student metadata dictionaries."""
    ensure_cache_initialized()
    with _cache_lock:
        return [dict(v) for v in _student_metadata.values()]


def get_cached_student_metadata(student_id: str) -> Optional[Dict[str, Any]]:
    """Return a thread-safe copy of cached metadata for a single student."""
    ensure_cache_initialized()
    sid = str(student_id).strip()
    with _cache_lock:
        meta = _student_metadata.get(sid)
        return dict(meta) if meta else None


def is_cache_populated() -> bool:
    """Check if the in-memory cache has been initialized and contains records."""
    with _cache_lock:
        return _is_initialized and len(_student_metadata) > 0


