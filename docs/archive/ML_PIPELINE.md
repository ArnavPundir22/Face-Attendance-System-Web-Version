# 🧠 Machine Learning & Inference Pipeline

BioSecure AI leverages a robust local computer vision pipeline. The system performs face detection, alignment, and high-dimensional feature extraction directly on the host machine using ONNX Runtime.

---

## 1. Pipeline Overview

The pipeline transforms raw input frames into mathematical coordinates (vector embeddings) through four distinct phases:

```
[ Raw Image Bytes ] ──► (1. Decoding) ──► [ CV2 BGR Matrix ]
                                                 │
                                                 ▼
[ Bounding Boxes ] ◄── (2. RetinaFace) ◄─────── [ Face Detection ]
       │
       ▼
(3. Landmark Alignment) ──► [ Aligned Face Chip ]
                                   │
                                   ▼
[ 512D Vector ] ◄── (4. ArcFace) ◄─┴── [ Embedding Generation ]
       │
       ▼
(5. L2 Normalisation) ──► [ Normalized Vector ] ──► (Database RPC Match)
```

---

## 2. Core Components

### 2.1. Image Decoding (`cv2.imdecode`)
Incoming photo requests contain multipart form bytes. The backend decodes this memory buffer directly into an OpenCV BGR matrix:
```python
npimg = np.frombuffer(file.read(), np.uint8)
frame = cv2.imdecode(npimg, cv2.IMREAD_COLOR)
```

### 2.2. Face Detection & Landmarking (RetinaFace)
We utilize the `buffalo_l` configuration from **InsightFace**. The detector identifies bounding boxes (`bbox`) and 5-point facial key landmarks (eyes, nose, and mouth corners) even under complex angles or low lighting conditions.

### 2.3. Facial Alignment (Affine Transform)
Before generating vector representations, the system rotates and scales the face based on the landmark coordinates. This alignment ensures the face is centered, front-facing, and scaled uniformly, significantly increasing match rates.

### 2.4. Embedding Extraction (ArcFace)
The aligned face chip is passed to the ArcFace deep neural network model. It processes the pixels and outputs a **512-dimensional vector embedding** (`float32`), capturing unique high-level semantic facial identifiers.

---

## 3. Mathematical Alignment & Normalisation

### 3.1. Vector Normalisation
To perform accurate similarity searches using cosine distance metrics, the raw embeddings must be **L2 normalised** (scaled to unit length of 1.0).

The L2 norm of a vector \( \mathbf{v} \) is defined as:
\[ \|\mathbf{v}\|_2 = \sqrt{\sum_{i=1}^{n} v_i^2} \]

The normalised vector \( \mathbf{\hat{v}} \) is calculated as:
\[ \mathbf{\hat{v}} = \frac{\mathbf{v}}{\|\mathbf{v}\|_2} \]

This ensures that the Euclidean distance between any two vectors directly represents their cosine similarity, making calculations invariant to image lighting changes.

### 3.2. Normalisation implementation (`utils/face.py`)
```python
def normalize_embedding(emb: np.ndarray) -> np.ndarray | None:
    """Perform L2 normalization on a face embedding array."""
    norm = np.linalg.norm(emb)
    if norm == 0:
        return None
    return emb / norm
```
By feeding only normalised vectors to Supabase, we ensure the index metrics (`cosine` operators) function accurately.
