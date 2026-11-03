#!/usr/bin/env python3
"""
Independent Empirical Verification & Stress Test Script — Challenger 1.

Targets:
1. In-memory biometric cache matrix alignment under arbitrary insertions & deletions.
2. Boundary handling: last student deletion, empty cache matching, transition to None.
3. Resilience to malformed, empty, whitespace, and non-existent IDs.
4. Idempotency of clear_face_cache().
5. High-concurrency multithreaded stress testing (30 threads, 3000 total operations).
"""

import sys
import os
import random
import threading
import time
import numpy as np

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

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


def make_unit_vector(idx: int) -> np.ndarray:
    vec = np.zeros(512, dtype=np.float32)
    vec[idx % 512] = 1.0
    return vec


def make_random_unit_vector(seed: int) -> np.ndarray:
    rng = np.random.RandomState(seed)
    v = rng.randn(512).astype(np.float32)
    norm = np.linalg.norm(v)
    return v / norm if norm > 0 else v


def test_scenario_1_matrix_alignment():
    print("[1/5] Testing Matrix Alignment under Multi-Row Deletions...")
    clear_face_cache()
    face_cache._is_initialized = True

    N = 100
    records = {}
    for i in range(N):
        sid = f"STU_ALIGN_{i:03d}"
        emb = make_unit_vector(i)
        records[sid] = emb
        add_student_to_cache(sid, f"Student {i}", "BTech", "CSE", emb, 2024)

    assert len(face_cache._student_ids) == N
    assert face_cache._embeddings_matrix.shape == (N, 512)
    assert len(face_cache._student_metadata) == N

    # Delete 40 random students
    rng = random.Random(1337)
    delete_targets = rng.sample(list(records.keys()), 40)
    for sid in delete_targets:
        res = remove_student_from_cache(sid)
        assert res is True, f"Failed deletion for {sid}"
        assert remove_student_from_cache(sid) is False

    remaining_count = N - 40
    assert len(face_cache._student_ids) == remaining_count
    assert face_cache._embeddings_matrix.shape == (remaining_count, 512)
    assert len(face_cache._student_metadata) == remaining_count

    # Check alignment for EVERY single remaining student
    for sid, emb in records.items():
        if sid in delete_targets:
            assert sid not in face_cache._student_ids
            assert sid not in face_cache._student_metadata
        else:
            idx = face_cache._student_ids.index(sid)
            mat_row = face_cache._embeddings_matrix[idx]
            dot = float(np.dot(mat_row, emb))
            assert abs(dot - 1.0) < 1e-4, f"Matrix alignment corrupted for {sid}: dot={dot}"

            # Verify batch matcher returns this exact student
            m = match_faces_batch([emb], match_threshold=0.8)
            assert m[0] is not None
            assert m[0]["id"] == sid
            assert abs(m[0]["similarity"] - 1.0) < 1e-4

    print("  -> PASSED: All 60 remaining rows perfectly aligned (dot=1.0000).")


def test_scenario_2_last_student_deletion():
    print("[2/5] Testing Last Student Deletion & Matrix State Transition...")
    clear_face_cache()
    face_cache._is_initialized = True

    emb = make_unit_vector(42)
    add_student_to_cache("SOLO_1", "Solo", "BTech", "EE", emb)
    assert len(face_cache._student_ids) == 1
    assert face_cache._embeddings_matrix.shape == (1, 512)

    # Delete last student
    assert remove_student_from_cache("SOLO_1") is True
    assert face_cache._embeddings_matrix is None, "Matrix must be None when empty"
    assert face_cache._student_ids == []
    assert face_cache._student_metadata == {}

    # Queries on empty cache
    res = match_faces_batch([emb, emb])
    assert res == [None, None]

    # Re-insert student
    add_student_to_cache("REBORN_1", "Reborn", "BTech", "ME", emb)
    assert len(face_cache._student_ids) == 1
    assert face_cache._embeddings_matrix.shape == (1, 512)
    res2 = match_faces_batch([emb])
    assert res2[0]["id"] == "REBORN_1"

    print("  -> PASSED: Clean transition to None and re-initialization verified.")


def test_scenario_3_non_existent_and_malformed():
    print("[3/5] Testing Non-Existent & Malformed Student Deletions...")
    clear_face_cache()
    face_cache._is_initialized = True

    emb = make_unit_vector(10)
    add_student_to_cache("EXIST_1", "E1", "BSc", "CS", emb)

    bad_ids = [
        "DOES_NOT_EXIST",
        "",
        "   ",
        "\t\r\n",
        None,
        999999,
        "EXIST_1_SUFFIX",
    ]
    for b in bad_ids:
        assert remove_student_from_cache(b) is False, f"Expected False for {repr(b)}"

    assert len(face_cache._student_ids) == 1
    assert face_cache._embeddings_matrix.shape == (1, 512)
    print("  -> PASSED: Malformed/non-existent deletions safely handled.")


def test_scenario_4_clear_face_cache_idempotency():
    print("[4/5] Testing clear_face_cache() Idempotency...")
    for _ in range(10):
        clear_face_cache()
        assert face_cache._embeddings_matrix is None
        assert face_cache._student_ids == []
        assert face_cache._student_metadata == {}
        assert face_cache._is_initialized is False

    print("  -> PASSED: Repeated clear_face_cache() calls are 100% idempotent.")


def test_scenario_5_high_concurrency():
    print("[5/5] Stress-Testing High Concurrency (30 threads, 3000 operations)...")
    clear_face_cache()
    face_cache._is_initialized = True

    # Pre-seed 40 students
    initial_count = 40
    for i in range(initial_count):
        add_student_to_cache(
            student_id=f"CONCUR_BASE_{i:03d}",
            name=f"Base {i}",
            program="BTech",
            branch="CSE",
            embedding=make_random_unit_vector(i + 10),
            enrollment_year=2024,
        )

    barrier = threading.Barrier(30)
    iterations = 100
    errors = []

    def matcher_task(tid: int):
        try:
            barrier.wait()
            for it in range(iterations):
                q = make_random_unit_vector(tid * 1000 + it)
                matches = match_faces_batch([q], match_threshold=0.6)
                assert isinstance(matches, list)
        except Exception as e:
            errors.append(f"Matcher-{tid}: {e}")

    def adder_task(tid: int):
        try:
            barrier.wait()
            for it in range(iterations):
                sid = f"DYN_{tid}_{it}"
                v = make_random_unit_vector(tid * 500 + it)
                add_student_to_cache(sid, f"Dyn {it}", "MTech", "AI", v)
        except Exception as e:
            errors.append(f"Adder-{tid}: {e}")

    def remover_task(tid: int):
        try:
            barrier.wait()
            for it in range(iterations):
                # Target existing base students or dynamic ones
                target = f"DYN_{random.randint(10, 19)}_{random.randint(0, iterations)}"
                remove_student_from_cache(target)
                if it % 5 == 0:
                    remove_student_from_cache(f"CONCUR_BASE_{random.randint(0, initial_count):03d}")
                remove_student_from_cache("DOES_NOT_EXIST")
        except Exception as e:
            errors.append(f"Remover-{tid}: {e}")

    def updater_task(tid: int):
        try:
            barrier.wait()
            for it in range(iterations):
                sid = f"CONCUR_BASE_{it % initial_count:03d}"
                update_student_metadata_cache(sid, f"Name {it}", "PhD", "Robotics", 2027)
                update_cached_student_drift(sid, 0.05, "HEALTHY")
                get_student_ewma(sid)
        except Exception as e:
            errors.append(f"Updater-{tid}: {e}")

    threads = []
    # 10 matchers
    for t in range(10):
        threads.append(threading.Thread(target=matcher_task, args=(t,)))
    # 10 adders
    for t in range(10, 20):
        threads.append(threading.Thread(target=adder_task, args=(t,)))
    # 6 removers
    for t in range(20, 26):
        threads.append(threading.Thread(target=remover_task, args=(t,)))
    # 4 updaters
    for t in range(26, 30):
        threads.append(threading.Thread(target=updater_task, args=(t,)))

    t0 = time.time()
    for th in threads:
        th.start()
    for th in threads:
        th.join()
    duration = time.time() - t0

    assert errors == [], f"Concurrency errors occurred: {errors}"

    # Check invariants
    with face_cache._cache_lock:
        ids_cnt = len(face_cache._student_ids)
        meta_cnt = len(face_cache._student_metadata)
        mat_cnt = 0 if face_cache._embeddings_matrix is None else face_cache._embeddings_matrix.shape[0]

        assert ids_cnt == meta_cnt, f"ID count ({ids_cnt}) != Metadata count ({meta_cnt})"
        assert ids_cnt == mat_cnt, f"ID count ({ids_cnt}) != Matrix rows ({mat_cnt})"
        assert len(set(face_cache._student_ids)) == ids_cnt, "Duplicate IDs present"

    print(f"  -> PASSED: 3000 operations across 30 threads in {duration:.2f}s with 0 errors.")
    print("  -> Invariants strictly preserved: len(_student_ids) == len(_student_metadata) == _embeddings_matrix.shape[0].")


if __name__ == "__main__":
    test_scenario_1_matrix_alignment()
    test_scenario_2_last_student_deletion()
    test_scenario_3_non_existent_and_malformed()
    test_scenario_4_clear_face_cache_idempotency()
    test_scenario_5_high_concurrency()
    print("\n=======================================================")
    print("ALL EMPIRICAL ADVERSARIAL STRESS TESTS COMPLETED SUCCESSFULLY!")
    print("=======================================================")
