"""
Adversarial Stress Test Suite for Biometric In-Memory Cache (src/utils/face_cache.py).

Empirical verification of:
1. Matrix alignment and row integrity after multiple sequential/random deletions.
2. Clean transition of _embeddings_matrix to None upon deleting the final student.
3. Graceful handling of non-existent, whitespace, and malformed student IDs on deletion.
4. Idempotency of repeated clear_face_cache() calls.
5. Thread-safety and race condition resistance under high-concurrency read/write/delete load.
"""

import concurrent.futures
import random
import threading
import numpy as np
import pytest

from src.utils import face_cache
from src.utils.face_cache import (
    add_student_to_cache,
    remove_student_from_cache,
    clear_face_cache,
    match_faces_batch,
    update_student_metadata_cache,
    update_cached_student_drift,
    get_student_ewma,
)


@pytest.fixture(autouse=True)
def clean_cache():
    """Ensure in-memory cache is pristine before and after each adversarial test."""
    clear_face_cache()
    face_cache._is_initialized = True
    yield
    clear_face_cache()


def _make_unit_vector(dim_idx: int) -> np.ndarray:
    """Generate a standard basis unit vector in 512D."""
    vec = np.zeros(512, dtype=np.float32)
    vec[dim_idx % 512] = 1.0
    return vec


def _make_random_normalized_vector(seed: int) -> np.ndarray:
    """Generate a reproducible random normalized 512D vector."""
    rng = np.random.RandomState(seed)
    vec = rng.randn(512).astype(np.float32)
    norm = np.linalg.norm(vec)
    return vec / norm if norm > 0 else vec


def test_adversarial_sequential_deletions_matrix_alignment():
    """
    Stress-test matrix alignment:
    Insert 60 synthetic students with distinct known unit vectors.
    Delete 25 students across head, middle, and tail in arbitrary order.
    Empirically verify that every remaining student's matrix row matches their vector
    with exact similarity 1.0, and that no index shift occurred.
    """
    num_students = 60
    student_records = {}

    for i in range(num_students):
        sid = f"ADV_STUDENT_{i:03d}"
        emb = _make_unit_vector(i)
        student_records[sid] = {
            "name": f"Student {i}",
            "program": "B.Tech",
            "branch": "CSE" if i % 2 == 0 else "ECE",
            "embedding": emb,
        }
        add_student_to_cache(
            student_id=sid,
            name=student_records[sid]["name"],
            program=student_records[sid]["program"],
            branch=student_records[sid]["branch"],
            embedding=emb,
            enrollment_year=2024,
        )

    assert len(face_cache._student_ids) == num_students
    assert face_cache._embeddings_matrix.shape == (num_students, 512)
    assert len(face_cache._student_metadata) == num_students

    # Select 25 students to delete: head, tail, and random indices
    to_delete = [
        "ADV_STUDENT_000",  # head
        "ADV_STUDENT_001",
        f"ADV_STUDENT_{num_students - 1:03d}",  # tail
        f"ADV_STUDENT_{num_students - 2:03d}",
    ]
    # Add random middle selections
    rng = random.Random(42)
    remaining_pool = [s for s in student_records if s not in to_delete]
    to_delete.extend(rng.sample(remaining_pool, 21))

    for sid in to_delete:
        removed = remove_student_from_cache(sid)
        assert removed is True, f"Failed to remove existing student {sid}"
        # Second removal must return False
        assert remove_student_from_cache(sid) is False

    expected_remaining = num_students - len(to_delete)
    assert len(face_cache._student_ids) == expected_remaining
    assert face_cache._embeddings_matrix.shape == (expected_remaining, 512)
    assert len(face_cache._student_metadata) == expected_remaining

    # Verify every remaining student:
    # 1. Matches their vector with ~1.0 similarity
    # 2. Row index in matrix corresponds to their position in _student_ids
    for sid, rec in student_records.items():
        if sid in to_delete:
            assert sid not in face_cache._student_ids
            assert sid not in face_cache._student_metadata
            # Querying with deleted student's vector must NOT match deleted student ID
            m = match_faces_batch([rec["embedding"]], match_threshold=0.8)
            assert m[0] is None or m[0]["id"] != sid
        else:
            assert sid in face_cache._student_ids
            assert sid in face_cache._student_metadata
            m_idx = face_cache._student_ids.index(sid)
            # Row alignment check: dot product of row with original vector must be 1.0
            row_emb = face_cache._embeddings_matrix[m_idx]
            dot_prod = float(np.dot(row_emb, rec["embedding"]))
            assert pytest.approx(dot_prod, 1e-5) == 1.0, f"Matrix row misalignment for {sid}"

            # Batch match check
            matches = match_faces_batch([rec["embedding"]], match_threshold=0.8)
            assert matches[0] is not None
            assert matches[0]["id"] == sid
            assert pytest.approx(matches[0]["similarity"], 1e-4) == 1.0


def test_adversarial_last_student_deletion_transitions():
    """
    Verify deletion of the last remaining student:
    Matrix must cleanly transition to None (not empty array) and subsequent calls
    must not throw AttributeError, shape mismatches, or indexing errors.
    """
    single_sid = "SOLO_STUDENT"
    emb = _make_unit_vector(5)

    add_student_to_cache(
        student_id=single_sid,
        name="Solo",
        program="MCA",
        branch="CS",
        embedding=emb,
    )

    assert len(face_cache._student_ids) == 1
    assert face_cache._embeddings_matrix.shape == (1, 512)

    # Match works
    m = match_faces_batch([emb], match_threshold=0.5)
    assert m[0] is not None
    assert m[0]["id"] == single_sid

    # Delete the solo student
    removed = remove_student_from_cache(single_sid)
    assert removed is True

    # Invariants after last deletion
    assert face_cache._student_ids == []
    assert face_cache._student_metadata == {}
    assert face_cache._embeddings_matrix is None

    # match_faces_batch on empty cache must return [None] without error
    m_after = match_faces_batch([emb, emb], match_threshold=0.5)
    assert m_after == [None, None]

    # Empty queries
    assert match_faces_batch([], match_threshold=0.5) == []

    # Re-adding a new student after total emptying must re-initialize matrix cleanly
    new_sid = "NEW_STUDENT_AFTER_EMPTY"
    new_emb = _make_unit_vector(12)
    add_student_to_cache(
        student_id=new_sid,
        name="New Student",
        program="B.Sc",
        branch="Math",
        embedding=new_emb,
    )

    assert len(face_cache._student_ids) == 1
    assert face_cache._embeddings_matrix.shape == (1, 512)
    m_readd = match_faces_batch([new_emb], match_threshold=0.5)
    assert m_readd[0] is not None
    assert m_readd[0]["id"] == new_sid


def test_adversarial_non_existent_and_malformed_deletions():
    """
    Verify that deleting non-existent, empty, whitespace, None, or integer IDs
    returns False gracefully without raising exceptions or mutating cache state.
    """
    # Pre-populate with 2 students
    sid1, sid2 = "EXISTING_1", "EXISTING_2"
    emb1, emb2 = _make_unit_vector(1), _make_unit_vector(2)
    add_student_to_cache(sid1, "Student 1", "B.Tech", "CSE", emb1)
    add_student_to_cache(sid2, "Student 2", "B.Tech", "IT", emb2)

    initial_ids = list(face_cache._student_ids)
    initial_matrix_shape = face_cache._embeddings_matrix.shape

    # Adversarial deletion inputs
    invalid_inputs = [
        "DOES_NOT_EXIST",
        "",
        "   ",
        "\t\n",
        None,
        1234567,
        "EXISTING_1_TYPO",
        "existing_1",  # case sensitivity check
    ]

    for inp in invalid_inputs:
        result = remove_student_from_cache(inp)
        assert result is False, f"Expected False for input: {repr(inp)}"

    # Invariants unchanged
    assert face_cache._student_ids == initial_ids
    assert face_cache._embeddings_matrix.shape == initial_matrix_shape
    assert len(face_cache._student_metadata) == 2


def test_adversarial_repeated_clear_face_cache():
    """
    Verify that clear_face_cache() is strictly idempotent and safe to call
    repeatedly on empty, populated, and uninitialized caches.
    """
    # 1. Clear unpopulated cache
    for _ in range(5):
        clear_face_cache()
        assert face_cache._embeddings_matrix is None
        assert face_cache._student_ids == []
        assert face_cache._student_metadata == {}
        assert face_cache._is_initialized is False

    # 2. Populate and clear repeatedly
    for i in range(5):
        face_cache._is_initialized = True
        add_student_to_cache(f"REP_{i}", f"Name {i}", "B.A", "Hist", _make_unit_vector(i))
        assert len(face_cache._student_ids) == 1

        clear_face_cache()
        clear_face_cache()  # Immediate back-to-back call
        assert face_cache._embeddings_matrix is None
        assert face_cache._student_ids == []
        assert face_cache._is_initialized is False


def test_adversarial_high_concurrency_stress():
    """
    Simulated multi-threaded concurrency stress test.
    Spawns 20 worker threads concurrently performing:
    - Thread 1-5: batch matching against known and random faces
    - Thread 6-10: adding dynamic students
    - Thread 11-15: removing random and specific students
    - Thread 16-18: updating student metadata
    - Thread 19-20: updating student EWMA drift
    
    Verifies that:
    1. No thread crashes with unhandled exceptions.
    2. No race condition desynchronizes len(_student_ids), _student_metadata, and _embeddings_matrix.
    3. Final state is completely consistent.
    """
    # Seed with 30 initial students
    initial_count = 30
    for i in range(initial_count):
        sid = f"BASE_CONCUR_{i:03d}"
        add_student_to_cache(
            student_id=sid,
            name=f"Base {i}",
            program="B.Tech",
            branch="CSE",
            embedding=_make_random_normalized_vector(i + 100),
            enrollment_year=2025,
        )

    num_iterations = 80
    barrier = threading.Barrier(20)
    errors = []

    def matcher_worker(thread_id: int):
        try:
            barrier.wait()
            for it in range(num_iterations):
                # Query with random or known vectors
                vec = _make_random_normalized_vector((thread_id * 1000) + it)
                res = match_faces_batch([vec], match_threshold=0.6)
                assert isinstance(res, list)
                assert len(res) == 1
        except Exception as e:
            errors.append(f"matcher_worker-{thread_id}: {e}")

    def adder_worker(thread_id: int):
        try:
            barrier.wait()
            for it in range(num_iterations):
                sid = f"CONCUR_ADD_T{thread_id}_{it}"
                vec = _make_random_normalized_vector((thread_id * 500) + it)
                add_student_to_cache(
                    student_id=sid,
                    name=f"Concur Student {it}",
                    program="M.Tech",
                    branch="AI",
                    embedding=vec,
                    enrollment_year=2026,
                )
        except Exception as e:
            errors.append(f"adder_worker-{thread_id}: {e}")

    def remover_worker(thread_id: int):
        try:
            barrier.wait()
            for it in range(num_iterations):
                # Attempt to delete either base students or newly added students
                target_sid = f"CONCUR_ADD_T{random.randint(6, 10)}_{random.randint(0, num_iterations)}"
                remove_student_from_cache(target_sid)
                if it % 5 == 0:
                    remove_student_from_cache(f"BASE_CONCUR_{random.randint(0, initial_count):03d}")
                # Also delete non-existent ID
                remove_student_from_cache("NON_EXISTENT_RACE_ID")
        except Exception as e:
            errors.append(f"remover_worker-{thread_id}: {e}")

    def metadata_updater_worker(thread_id: int):
        try:
            barrier.wait()
            for it in range(num_iterations):
                sid = f"BASE_CONCUR_{it % initial_count:03d}"
                update_student_metadata_cache(
                    student_id=sid,
                    name=f"Updated Name {it}",
                    program="PhD",
                    branch="Robotics",
                    enrollment_year=2027,
                )
        except Exception as e:
            errors.append(f"metadata_updater-{thread_id}: {e}")

    def drift_updater_worker(thread_id: int):
        try:
            barrier.wait()
            for it in range(num_iterations):
                sid = f"BASE_CONCUR_{it % initial_count:03d}"
                update_cached_student_drift(
                    student_id=sid,
                    new_ewma=round(random.random(), 4),
                    alert_level="WARNING" if it % 2 == 0 else "HEALTHY",
                )
                get_student_ewma(sid)
        except Exception as e:
            errors.append(f"drift_updater-{thread_id}: {e}")

    threads = []
    # 5 matchers
    for t in range(5):
        threads.append(threading.Thread(target=matcher_worker, args=(t,)))
    # 5 adders
    for t in range(5, 10):
        threads.append(threading.Thread(target=adder_worker, args=(t,)))
    # 5 removers
    for t in range(10, 15):
        threads.append(threading.Thread(target=remover_worker, args=(t,)))
    # 3 metadata updaters
    for t in range(15, 18):
        threads.append(threading.Thread(target=metadata_updater_worker, args=(t,)))
    # 2 drift updaters
    for t in range(18, 20):
        threads.append(threading.Thread(target=drift_updater_worker, args=(t,)))

    for th in threads:
        th.start()
    for th in threads:
        th.join()

    assert errors == [], f"Concurrency errors encountered: {errors}"

    # Verify final structural invariants under lock
    with face_cache._cache_lock:
        ids_len = len(face_cache._student_ids)
        meta_len = len(face_cache._student_metadata)
        if face_cache._embeddings_matrix is None:
            matrix_len = 0
        else:
            matrix_len = face_cache._embeddings_matrix.shape[0]

        assert ids_len == meta_len, f"Invariant violated: IDs ({ids_len}) != Metadata ({meta_len})"
        assert ids_len == matrix_len, f"Invariant violated: IDs ({ids_len}) != Matrix rows ({matrix_len})"

        # Verify no duplicate IDs
        assert len(set(face_cache._student_ids)) == ids_len, "Duplicate student IDs detected in cache!"


def test_adversarial_metadata_update_edge_cases():
    """
    Verify update_student_metadata_cache behavior on:
    - Empty student_id or non-existent student_id -> returns False.
    - Partial field updates (enrollment_year=None, academic_year=None).
    """
    sid = "META_TEST_STU"
    emb = _make_unit_vector(20)
    add_student_to_cache(sid, "Original", "B.Tech", "CSE", emb, enrollment_year=2023, academic_year="2023-27")

    # Update non-existent student
    assert update_student_metadata_cache("NON_EXISTENT", "Name", "Prog", "Branch") is False

    # Update with None for optional fields (should preserve previous or not crash)
    success = update_student_metadata_cache(
        student_id=sid,
        name="Updated Name",
        program="M.Tech",
        branch="AI",
        enrollment_year=None,
        academic_year=None,
    )
    assert success is True
    meta = face_cache._student_metadata[sid]
    assert meta["name"] == "Updated Name"
    assert meta["program"] == "M.Tech"
    assert meta["branch"] == "AI"
    # Preserves existing enrollment_year since None was passed
    assert meta["enrollment_year"] == 2023
    assert meta["academic_year"] == "2023-27"
