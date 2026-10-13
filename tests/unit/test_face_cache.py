import json
import numpy as np
import pytest

from src.utils.face import normalize_embedding
from src.utils.face_cache import (
    reload_face_cache,
    match_faces_batch,
    add_student_to_cache
)

def test_normalize_embedding_with_array():
    # Unit vector along first dimension
    vec = np.zeros(512, dtype=np.float32)
    vec[0] = 5.0
    norm_vec = normalize_embedding(vec)
    assert norm_vec is not None
    assert norm_vec.shape == (512,)
    assert pytest.approx(np.linalg.norm(norm_vec), 1e-5) == 1.0
    assert pytest.approx(norm_vec[0], 1e-5) == 1.0

def test_normalize_embedding_with_zero_norm():
    vec = np.zeros(512, dtype=np.float32)
    assert normalize_embedding(vec) is None
    assert normalize_embedding(None) is None
    assert normalize_embedding("") is None

def test_normalize_embedding_with_json_string():
    # Test JSON string parsing
    raw_list = [0.0] * 512
    raw_list[1] = 3.0
    raw_list[2] = 4.0
    json_str = json.dumps(raw_list)
    
    norm_vec = normalize_embedding(json_str)
    assert norm_vec is not None
    assert norm_vec.shape == (512,)
    assert pytest.approx(np.linalg.norm(norm_vec), 1e-5) == 1.0
    assert pytest.approx(norm_vec[1], 1e-5) == 0.6
    assert pytest.approx(norm_vec[2], 1e-5) == 0.8

def test_normalize_embedding_with_bracket_string():
    # Test pgvector formatted comma string: '[1.0, 2.0, ...]'
    items = ["1.0"] + ["0.0"] * 511
    bracket_str = "[" + ", ".join(items) + "]"
    norm_vec = normalize_embedding(bracket_str)
    assert norm_vec is not None
    assert norm_vec.shape == (512,)
    assert pytest.approx(norm_vec[0], 1e-5) == 1.0

def test_add_student_to_cache_and_match():
    # Create synthetic orthogonal embeddings
    test_id = "TEST_STUDENT_9999"
    emb = np.zeros(512, dtype=np.float32)
    emb[10] = 1.0
    
    add_student_to_cache(
        student_id=test_id,
        name="Test Student",
        program="B.Tech",
        branch="CSE",
        embedding=emb,
        enrollment_year=2026
    )
    
    # Query with exact matching embedding
    matches = match_faces_batch([emb], match_threshold=0.5)
    assert len(matches) == 1
    assert matches[0] is not None
    assert matches[0]["id"] == test_id
    assert matches[0]["name"] == "Test Student"
    assert pytest.approx(matches[0]["similarity"], 1e-4) == 1.0

    # Query with orthogonal non-matching embedding
    other_emb = np.zeros(512, dtype=np.float32)
    other_emb[20] = 1.0
    no_matches = match_faces_batch([other_emb], match_threshold=0.5)
    assert len(no_matches) == 1
    # Orthogonal cosine similarity is 0.0 < 0.5 threshold
    assert no_matches[0] is None
