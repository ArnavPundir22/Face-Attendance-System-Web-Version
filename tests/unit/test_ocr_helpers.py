import pytest
import numpy as np
import cv2

from src.utils.ocr_helpers import (
    parse_student_id_text,
    preprocess_id_card_image
)

def test_parse_student_id_text_standard_university():
    sample_text = """
    COER UNIVERSITY
    Name : Arnav Pundir
    CU-ID : CU240251013
    Program : B.Tech (CSE)
    Session : 2024-2028
    Email : arnav@example.com
    """
    parsed = parse_student_id_text(sample_text)
    assert parsed["name"] == "Arnav Pundir"
    assert parsed["id"] == "CU240251013"
    assert parsed["program"] == "B.Tech"
    assert parsed["branch"] == "CSE"
    assert parsed["enrollment_year"] == "2024"
    assert parsed["email"] == "arnav@example.com"

def test_parse_student_id_text_multiline_split():
    # Test OCR where colon was placed on next line
    sample_text = """
    Name
    : Jane Doe
    Roll No: 2021BCA042
    BCA (Information Technology)
    Batch 2021-2024
    """
    parsed = parse_student_id_text(sample_text)
    assert parsed["name"] == "Jane Doe"
    assert "2021BCA042" in parsed["id"]
    assert parsed["program"] == "BCA"
    assert parsed["branch"] == "IT"
    assert parsed["enrollment_year"] == "2021"

def test_preprocess_id_card_image():
    # Create synthetic test image bytes (100x100 white square with blue text)
    img = np.ones((100, 100, 3), dtype=np.uint8) * 255
    cv2.putText(img, "TEST", (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
    _, buffer = cv2.imencode('.jpg', img)
    image_bytes = buffer.tobytes()

    processed = preprocess_id_card_image(image_bytes)
    assert len(processed) >= 2  # At least gray and inverted
    for p in processed:
        assert isinstance(p, np.ndarray)
        assert len(p.shape) == 2  # Grayscale / 2D
