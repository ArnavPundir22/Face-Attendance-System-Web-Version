import json
import numpy as np
import pytest

from src.utils.face import normalize_embedding
from src.utils.face_cache import (
    reload_face_cache,
    match_faces_batch,
    add_student_to_cache,
    remove_student_from_cache,
    clear_face_cache,
    update_student_metadata_cache,
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


def test_update_student_metadata_cache():
    test_id = "TEST_UPDATE_1001"
    emb = np.zeros(512, dtype=np.float32)
    emb[15] = 1.0

    add_student_to_cache(
        student_id=test_id,
        name="Original Name",
        program="BCA",
        branch="General",
        embedding=emb,
        enrollment_year=2023,
        academic_year="2023-2026"
    )

    success = update_student_metadata_cache(
        student_id=test_id,
        name="Updated Name",
        program="B.Tech",
        branch="CSE",
        enrollment_year=2024,
        academic_year="2024-2028"
    )
    assert success is True

    matches = match_faces_batch([emb], match_threshold=0.5)
    assert len(matches) == 1
    assert matches[0] is not None
    assert matches[0]["id"] == test_id
    assert matches[0]["name"] == "Updated Name"
    assert matches[0]["program"] == "B.Tech"
    assert matches[0]["branch"] == "CSE"
    assert matches[0]["enrollment_year"] == 2024

    # Non-existent student update returns False
    assert update_student_metadata_cache("NON_EXISTENT_ID_XYZ", name="X", program="Y", branch="Z") is False


def test_remove_student_from_cache():
    id1, id2 = "TEST_REM_1", "TEST_REM_2"
    emb1 = np.zeros(512, dtype=np.float32)
    emb1[30] = 1.0
    emb2 = np.zeros(512, dtype=np.float32)
    emb2[40] = 1.0

    add_student_to_cache(student_id=id1, name="Student 1", program="B.Tech", branch="CSE", embedding=emb1)
    add_student_to_cache(student_id=id2, name="Student 2", program="B.Tech", branch="IT", embedding=emb2)

    # Both match
    m = match_faces_batch([emb1, emb2], match_threshold=0.5)
    assert m[0]["id"] == id1
    assert m[1]["id"] == id2

    # Remove student 1
    assert remove_student_from_cache(id1) is True
    # Second removal returns False
    assert remove_student_from_cache(id1) is False
    # Non-existent student removal returns False
    assert remove_student_from_cache("NON_EXISTENT_ID") is False
    assert remove_student_from_cache("") is False
    assert remove_student_from_cache(None) is False

    # Student 1 no longer matches, Student 2 still matches
    m2 = match_faces_batch([emb1, emb2], match_threshold=0.5)
    assert m2[0] is None
    assert m2[1] is not None
    assert m2[1]["id"] == id2

    # Remove student 2
    assert remove_student_from_cache(id2) is True
    m3 = match_faces_batch([emb2], match_threshold=0.5)
    assert m3[0] is None


def test_remove_student_from_cache_multi_index_shift():
    ids = ["STU_SHIFT_A", "STU_SHIFT_B", "STU_SHIFT_C"]
    embs = []
    for i, sid in enumerate(ids):
        emb = np.zeros(512, dtype=np.float32)
        emb[70 + i] = 1.0
        embs.append(emb)
        add_student_to_cache(sid, f"Student {sid}", "B.Tech", "CSE", emb, 2026)

    # Remove STU_SHIFT_B (middle element)
    assert remove_student_from_cache("STU_SHIFT_B") is True

    # STU_SHIFT_A and STU_SHIFT_C must still match with 1.0 similarity and correct metadata
    matches_ac = match_faces_batch([embs[0], embs[2]], match_threshold=0.5)
    assert matches_ac[0] is not None and matches_ac[0]["id"] == "STU_SHIFT_A"
    assert matches_ac[1] is not None and matches_ac[1]["id"] == "STU_SHIFT_C"

    # STU_SHIFT_B must not match
    match_b = match_faces_batch([embs[1]], match_threshold=0.5)
    assert match_b[0] is None

    # Clean up remaining test students
    remove_student_from_cache("STU_SHIFT_A")
    remove_student_from_cache("STU_SHIFT_C")


def test_clear_face_cache():
    test_id = "TEST_CLEAR_1"
    emb = np.zeros(512, dtype=np.float32)
    emb[50] = 1.0

    add_student_to_cache(student_id=test_id, name="Student Clear", program="MBA", branch="HR", embedding=emb)
    m = match_faces_batch([emb], match_threshold=0.5)
    assert m[0]["id"] == test_id

    clear_face_cache()
    from src.utils import face_cache
    assert face_cache._embeddings_matrix is None
    assert face_cache._student_ids == []
    assert face_cache._student_metadata == {}
    assert face_cache._is_initialized is False

