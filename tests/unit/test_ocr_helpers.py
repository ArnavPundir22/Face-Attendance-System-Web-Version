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


def test_parse_student_id_text_blood_group_and_watermark_isolation():
    """Ensure blood group, registrar signature, and camera watermarks are never captured as program."""
    sample_text = """
    COER UNIVERSITY
    STUDENT IDENTITY CARD
    Name : Rohit Sharma
    CU-ID : CU240251099
    Program : B.Pharma
    Blood Group : O+ve
    DOB : 12/05/2003
    Registrar
    Vivo X60 Pro ZEISS Oct 14, 2026, 13:30
    """
    parsed = parse_student_id_text(sample_text)
    assert parsed["name"] == "Rohit Sharma"
    assert parsed["id"] == "CU240251099"
    assert parsed["program"] == "B.Pharma"
    assert "blood" not in parsed["program"].lower()
    assert "registrar" not in parsed["program"].lower()
    assert "vivo" not in parsed["program"].lower()
    assert parsed["branch"] == ""


def test_parse_student_id_text_inline_blood_group_stop_token():
    """Ensure inline blood group on the same line as program is stopped by the boundary delimiter."""
    sample_text = """
    Name : Ananya Singh
    Roll No : 22010455
    Course : B.Tech (AI-ML) Blood Group : B+ve Registrar
    Session : 2022-2026
    """
    parsed = parse_student_id_text(sample_text)
    assert parsed["name"] == "Ananya Singh"
    assert parsed["id"] == "22010455"
    assert parsed["program"] == "B.Tech"
    assert parsed["branch"] in ("AI & ML", "AI-ML", "AIML")
    assert "blood" not in parsed["program"].lower()
    assert "registrar" not in parsed["program"].lower()


def test_parse_student_id_text_separate_branch_line():
    """Ensure dedicated Branch / Department line is accurately parsed."""
    sample_text = """
    Name : Vikram Patel
    Roll No : CU23010988
    Program : B.Tech
    Branch : Mechanical Engineering
    Session : 2023-2027
    """
    parsed = parse_student_id_text(sample_text)
    assert parsed["name"] == "Vikram Patel"
    assert parsed["id"] == "CU23010988"
    assert parsed["program"] == "B.Tech"
    assert parsed["branch"] == "ME"


def test_parse_student_id_text_dynamic_catalog_and_blacklist_rejection():
    """Ensure passing DB catalog matches custom programs, and garbage is rejected."""
    # Custom catalog match
    custom_text = """
    Name : Neha Gupta
    CU-ID : CU25010022
    Course : B.Com (Hons)
    """
    parsed = parse_student_id_text(
        custom_text,
        known_programs=["B.Com (Hons)", "BCA", "B.Tech"],
        known_branches=["Finance", "CSE"]
    )
    assert parsed["program"] == "B.Com (Hons)"

    # Garbage candidate containing blacklisted terms must be rejected
    garbage_text = """
    Name : Test Student
    ID : STU12345
    Program : Blood Group: Onish Registrar
    """
    parsed_garbage = parse_student_id_text(garbage_text)
    assert parsed_garbage["program"] == ""
    assert "blood" not in parsed_garbage["program"].lower()

