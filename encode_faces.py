"""
Batch face encoder.

Reads all images from the ``known_faces/`` directory, computes per-person
average face embeddings using InsightFace, and saves the result in the safe
numpy format used by the application:

  EncodeFile_Insight.npy          — float32 matrix, shape (N, D)
  EncodeFile_Insight_names.json   — ordered list of N student names

Run this script whenever you add new photos to ``known_faces/`` and want to
rebuild all embeddings from scratch.  For incremental encoding of a single
new student, use the "Add Student" form in the web UI instead.
"""

import json
import os
from collections import defaultdict

import cv2
import insightface
import numpy as np

# ---------------------------------------------------------------------------
# Configuration (mirrors config.py to avoid a circular import)
# ---------------------------------------------------------------------------
KNOWN_FACES_DIR  = os.environ.get('KNOWN_FACES_DIR', 'known_faces')
ENCODE_FILE_BASE = os.environ.get('ENCODE_FILE_BASE', 'EncodeFile_Insight')
MATRIX_FILE      = ENCODE_FILE_BASE + '.npy'
NAMES_FILE       = ENCODE_FILE_BASE + '_names.json'

# ctx_id: 0 = GPU, -1 = CPU
CTX_ID = int(os.environ.get('INSIGHTFACE_CTX_ID', '-1'))

# ---------------------------------------------------------------------------
# Model initialisation
# ---------------------------------------------------------------------------
print("[INFO] Loading InsightFace model …")
face_model = insightface.app.FaceAnalysis(name='buffalo_l')
face_model.prepare(ctx_id=CTX_ID)

# ---------------------------------------------------------------------------
# Encode every image in known_faces/
# ---------------------------------------------------------------------------
print("[INFO] Encoding faces …")

raw_embeddings: defaultdict[str, list] = defaultdict(list)

for filename in os.listdir(KNOWN_FACES_DIR):
    if not filename.lower().endswith(('.jpg', '.jpeg', '.png')):
        continue

    name = os.path.splitext(filename)[0].replace("_", " ").split("-")[0].strip()
    image_path = os.path.join(KNOWN_FACES_DIR, filename)
    image = cv2.imread(image_path)

    if image is None:
        print(f"[ERROR] Could not read {filename}")
        continue

    faces = face_model.get(image)
    if not faces:
        print(f"[WARNING] No face found in {filename}")
        continue

    # Use the largest detected face to handle group photos gracefully.
    face = max(faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))
    raw_embeddings[name].append(face.embedding)
    print(f"[INFO] Added encoding for: {name}")

# ---------------------------------------------------------------------------
# Average + normalise embeddings per person
# ---------------------------------------------------------------------------
names  = sorted(raw_embeddings.keys())
matrix_rows = []

for name in names:
    mean_emb = np.mean(raw_embeddings[name], axis=0).astype(np.float32)
    norm = np.linalg.norm(mean_emb)
    if norm > 0:
        mean_emb = mean_emb / norm
    matrix_rows.append(mean_emb)

# ---------------------------------------------------------------------------
# Save in numpy format (no pickle)
# ---------------------------------------------------------------------------
if matrix_rows:
    matrix = np.array(matrix_rows, dtype=np.float32)  # shape (N, D)
    np.save(MATRIX_FILE, matrix)
    with open(NAMES_FILE, 'w', encoding='utf-8') as fh:
        json.dump(names, fh, ensure_ascii=False, indent=2)
    print(f"[SUCCESS] Saved {len(names)} person(s) to {MATRIX_FILE} and {NAMES_FILE}")
else:
    print("[WARNING] No embeddings generated — output files not written.")

