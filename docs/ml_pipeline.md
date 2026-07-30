# 🧠 ML & Inference Pipeline Guide

BioSecure AI implements a state-of-the-art local facial recognition pipeline. This document explains the mathematical foundations, models, and execution flows utilized by the machine learning engine.

---

## 🛠️ Model Details

The system employs **InsightFace** (specifically the `buffalo_l` model pack) running locally inside the Python container. The pipeline comprises three distinct sub-models:

```mermaid
graph LR
    Input[Input Image] --> Retina[1. RetinaFace]
    Retina --> |Aligned crop| Arc[2. ArcFace]
    Arc --> |512-float array| L2[3. L2 Normalisation]
    L2 --> Output[512D Embedding]
```

1. **RetinaFace (Detection)**:
   - Locates faces within the image.
   - Outputs bounding boxes, detection scores, and key facial landmarks (eyes, nose, mouth corners).
2. **ArcFace (Feature Extraction)**:
   - Takes the aligned face crop.
   - Extracts a high-dimensional feature representation (embedding) consisting of a 512-dimensional vector of floating-point numbers.
3. **L2 Normalisation (Post-processing)**:
   - Scales the 512-dimensional vector to have a length (Euclidean/L2 norm) of exactly `1.0`.

---

## 📐 Vector Normalisation & Similarity Mathematics

To perform fast searches, we normalise the face embeddings and compute similarity using the Cosine distance.

### L2 (Euclidean) Normalisation
For a raw embedding vector \(v = [v_1, v_2, \dots, v_n]\), the normalized embedding \(\hat{v}\) is defined as:
\[\hat{v} = \frac{v}{\|v\|_2} = \frac{v}{\sqrt{\sum_{i=1}^n v_i^2}}\]

Normalising ensures that the dot product of two vectors is mathematically identical to their cosine similarity.

### Cosine Similarity
The cosine similarity between two normalised vectors \(\hat{a}\) and \(\hat{b}\) is:
\[\text{Similarity}(\hat{a}, \hat{b}) = \hat{a} \cdot \hat{b} = \sum_{i=1}^{512} \hat{a}_i \hat{b}_i\]

- A score of `1.0` means the faces are identical.
- A score of `0.0` means they are completely orthogonal.
- **Default Match Threshold**: set to `0.3` (configurable via `FACE_MATCH_THRESHOLD` in `.env`).

---

## 📷 Group Photo Processing Pipeline

When a group classroom photo is uploaded:

1. **Preprocessing**: The file bytes are read and decoded using OpenCV:
   ```python
   nparr = np.frombuffer(image_bytes, np.uint8)
   img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
   ```
2. **Face Detection**:
   InsightFace analyzes the image and detects all available faces:
   ```python
   faces = model.get(img)
   ```
3. **Loop & Match**:
   For each detected face:
   - Align the face layout.
   - Generate embedding.
   - Run L2 normalisation.
   - Run `match_face` database RPC search.
4. **Annotation**:
   Draw bounding boxes on the original image:
   - Green bounding box with student's name for identified matches.
   - Red bounding box for "Unknown" faces.
5. **Output**:
   The annotated image is encoded as a Base64 string and sent back to the browser client interface.
