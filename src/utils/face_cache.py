"""
In-Memory Biometric Embedding Cache & Batch Matrix Matcher — BioSecure AI.

Stores student 512D ArcFace embeddings in a contiguous NumPy array (float32)
to perform ultra-fast BLAS matrix dot product matching in < 1ms on CPU,
completely bypassing network latency to Supabase pgvector.
"""

import logging
import threading
from typing import Any, Dict, List, Optional

import numpy as np

from src import config
from src.utils.db import supabase_admin
from src.utils.face import normalize_embedding

logger = logging.getLogger(__name__)

_cache_lock = threading.Lock()
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

    with _cache_lock:
        try:
            logger.info("Initializing/Reloading in-memory face embedding cache...")
            response = supabase_admin.table('students') \
                .select('id, name, program, branch, enrollment_year, academic_year, embedding') \
                .execute()
            
            rows = response.data or []
            new_ids: List[str] = []
            new_meta: Dict[str, Dict[str, Any]] = {}
            emb_list: List[np.ndarray] = []

            for r in rows:
                sid = r.get('id')
                raw_emb = r.get('embedding')
                if not sid or not raw_emb:
                    continue

                try:
                    emb_arr = np.array(raw_emb, dtype=np.float32)
                    if emb_arr.shape != (512,):
                        continue
                    norm_emb = normalize_embedding(emb_arr)
                    if norm_emb is None:
                        continue
                    
                    sid_clean = str(sid).strip()
                    new_ids.append(sid_clean)
                    new_meta[sid_clean] = {
                        'id': sid_clean,
                        'name': r.get('name', 'Unknown'),
                        'program': r.get('program'),
                        'branch': r.get('branch'),
                        'enrollment_year': r.get('enrollment_year'),
                        'academic_year': r.get('academic_year')
                    }
                    emb_list.append(norm_emb)
                except Exception as err:
                    logger.warning("Skipping invalid embedding for student %s: %s", sid, err)

            if emb_list:
                _embeddings_matrix = np.vstack(emb_list).astype(np.float32)
                _student_ids = new_ids
                _student_metadata = new_meta
                _is_initialized = True
                logger.info("Face cache reloaded successfully: %d students in matrix memory.", len(_student_ids))
            else:
                _embeddings_matrix = None
                _student_ids = []
                _student_metadata = {}
                _is_initialized = True
                logger.warning("Face cache reloaded: 0 valid student embeddings found.")

            return len(_student_ids)
        except Exception as e:
            logger.error("Failed to reload in-memory face cache from Supabase: %s", e, exc_info=True)
            return len(_student_ids)


def ensure_cache_initialized():
    """Ensure the cache has been loaded at least once."""
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

    if not query_embeddings or _embeddings_matrix is None or len(_student_ids) == 0:
        return [None] * len(query_embeddings)

    with _cache_lock:
        try:
            norm_queries = []
            valid_indices = []
            for idx, q in enumerate(query_embeddings):
                nq = normalize_embedding(q)
                if nq is not None:
                    norm_queries.append(nq)
                    valid_indices.append(idx)

            if not norm_queries:
                return [None] * len(query_embeddings)

            Q = np.vstack(norm_queries).astype(np.float32)  # Shape: (N, 512)
            
            # Matrix multiplication: Q (N x 512) . M^T (512 x M) => Cosine Similarity Matrix (N x M)
            sim_matrix = np.dot(Q, _embeddings_matrix.T)

            results: List[Optional[Dict[str, Any]]] = [None] * len(query_embeddings)

            for i, orig_idx in enumerate(valid_indices):
                best_m_idx = int(np.argmax(sim_matrix[i]))
                best_score = float(sim_matrix[i, best_m_idx])

                if best_score >= match_threshold:
                    matched_id = _student_ids[best_m_idx]
                    meta = _student_metadata.get(matched_id, {})
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


def add_student_to_cache(student_id: str, name: str, program: str, branch: str, embedding: np.ndarray, enrollment_year: Optional[int] = None, academic_year: Optional[str] = None):
    """Dynamically append a new student to the in-memory matrix without reloading full DB."""
    global _student_ids, _student_metadata, _embeddings_matrix

    norm_emb = normalize_embedding(embedding)
    if norm_emb is None:
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
                _embeddings_matrix[idx] = norm_emb
            else:
                _embeddings_matrix = np.vstack([_embeddings_matrix, new_row])
                _student_ids.append(sid_clean)

        _student_metadata[sid_clean] = {
            'id': sid_clean,
            'name': name,
            'program': program,
            'branch': branch,
            'enrollment_year': enrollment_year,
            'academic_year': academic_year
        }
        logger.info("Added/updated student %s in memory face cache (Total: %d).", sid_clean, len(_student_ids))
