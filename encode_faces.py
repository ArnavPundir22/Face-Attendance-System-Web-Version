import insightface
import cv2
import os
import numpy as np
import pickle
from collections import defaultdict

# Path where face images are stored
path = 'known_faces'
encodings_dict = defaultdict(list)

# Initialize InsightFace model
print("[INFO] Loading InsightFace model...")
model = insightface.app.FaceAnalysis(name='buffalo_l')
model.prepare(ctx_id=0)  # 0 = GPU, -1 = CPU

print("[INFO] Encoding faces...")

for filename in os.listdir(path):
    if filename.lower().endswith(('.jpg', '.jpeg', '.png')):
        name = os.path.splitext(filename)[0].replace("_", " ").split("-")[0].strip()
        image_path = os.path.join(path, filename)
        image = cv2.imread(image_path)

        if image is None:
            print(f"[ERROR] Could not read {filename}")
            continue

        faces = model.get(image)
        if not faces:
            print(f"[WARNING] No face found in {filename}")
            continue

        # Take the largest face (useful if image has more than one)
        face = max(faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))
        encodings_dict[name].append(face.embedding)
        print(f"[INFO] Added encoding for: {name}")

# Average encodings per person
known_embeddings = []
for name, enc_list in encodings_dict.items():
    mean_encoding = np.mean(enc_list, axis=0)
    known_embeddings.append((mean_encoding, name))

# Save to file
with open('EncodeFile_Insight.pkl', 'wb') as f:
    pickle.dump(known_embeddings, f)

print(f"[SUCCESS] Saved {len(known_embeddings)} person(s) to EncodeFile_Insight.pkl")

