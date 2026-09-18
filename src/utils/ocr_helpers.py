"""
OCR & Text Parsing Utilities for Student ID Cards.

Provides robust parsing logic using Pretrained RapidOCR (ONNX Deep Learning)
and OpenCV to extract Student Name, ID/Roll Number, Program, Branch, Enrollment Year, and Email.
"""

import re
import cv2
import numpy as np

try:
    import pytesseract
    PYTESSERACT_AVAILABLE = True
except ImportError:
    PYTESSERACT_AVAILABLE = False

try:
    from rapidocr_onnxruntime import RapidOCR
    rapid_engine = RapidOCR()
    RAPIDOCR_AVAILABLE = True
except Exception as e:
    print(f"RapidOCR initialization notice: {e}")
    rapid_engine = None
    RAPIDOCR_AVAILABLE = False


# Known Program keywords and map
PROGRAM_KEYWORDS = {
    r'\bB\.?\s*Tech\b': 'B.Tech',
    r'\bB\.?\s*E\b': 'B.Tech',
    r'\bBCA\b': 'BCA',
    r'\bM\.?\s*Tech\b': 'M.Tech',
    r'\bMCA\b': 'MCA',
    r'\bB\.?\s*Sc\b': 'B.Sc',
    r'\bM\.?\s*Sc\b': 'M.Sc',
    r'\bBBA\b': 'BBA',
    r'\bMBA\b': 'MBA',
    r'\bPh\.?D\b': 'Ph.D',
    r'\bDiploma\b': 'Diploma'
}

# Known Branch keywords and map
BRANCH_KEYWORDS = {
    r'\b(Computer\s*Science|CSE|Comp\s*Sci)\b': 'CSE',
    r'\b(Information\s*Tech(nology)?|IT)\b': 'IT',
    r'\b(Electronics\s*(&|\+)?\s*Comm(unication)?|ECE|Electronics)\b': 'ECE',
    r'\b(Electrical\s*(&|\+)?\s*Electronics|EEE|Electrical)\b': 'EEE',
    r'\b(Mechanical|ME)\b': 'ME',
    r'\b(Civil|CE)\b': 'CE',
    r'\b(Artificial\s*Intelligence|AI\s*(&|\+)?\s*ML|AIML|AI)\b': 'AI & ML',
    r'\b(Data\s*Science|DS)\b': 'Data Science',
    r'\b(Cyber\s*Security)\b': 'Cyber Security',
    r'\b(Biotechnology|BT)\b': 'Biotechnology'
}


def preprocess_id_card_image(image_bytes: bytes) -> list:
    """
    Returns multiple preprocessed OpenCV image variants (original, inverted, adaptive thresholded)
    to handle dark background text (like COER ID cards) as well as light background text.
    """
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        return []

    # Grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Resize for high resolution OCR reading
    height, width = gray.shape[:2]
    if width < 1000:
        scale = 1200.0 / width
        gray = cv2.resize(gray, (int(width * scale), int(height * scale)), interpolation=cv2.INTER_CUBIC)

    processed_list = [gray]

    # Inverted Grayscale (turns white text on dark blue background into black text on white background)
    inverted = cv2.bitwise_not(gray)
    processed_list.append(inverted)

    # Adaptive Thresholding
    try:
        thresh_adaptive = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
        )
        processed_list.append(thresh_adaptive)

        thresh_adaptive_inv = cv2.adaptiveThreshold(
            inverted, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
        )
        processed_list.append(thresh_adaptive_inv)
    except Exception:
        pass

    return processed_list


def perform_python_ocr(image_bytes: bytes) -> str:
    """Run pretrained Neural OCR (RapidOCR) or PyTesseract multi-pass on image bytes."""
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        return ""

    combined_texts = []

    # 1. Pretrained Deep Learning Neural OCR (RapidOCR - DBNet + SVTR ONNX)
    if RAPIDOCR_AVAILABLE and rapid_engine is not None:
        try:
            result, _ = rapid_engine(img)
            if result:
                lines = [item[1].strip() for item in result if item and len(item) > 1 and item[1].strip()]
                if lines:
                    combined_texts.append("\n".join(lines))
        except Exception as e:
            print(f"RapidOCR engine execution error: {e}")

    # 2. PyTesseract multi-pass fallback
    if PYTESSERACT_AVAILABLE:
        try:
            images = preprocess_id_card_image(image_bytes)
            for m_img in images:
                try:
                    txt = pytesseract.image_to_string(m_img, config='--oem 3 --psm 6') or pytesseract.image_to_string(m_img)
                    if txt and txt.strip():
                        combined_texts.append(txt.strip())
                except Exception:
                    continue
        except Exception as e:
            print(f"pytesseract OCR error: {e}")

    return "\n".join(combined_texts)


def parse_student_id_text(text: str) -> dict:
    """
    Parses OCR text output to extract structured student attributes based on university ID format:
    1. enrollment_year: 1st 4 digits of Session (e.g., '2024-2028' -> '2024')
    2. program: text before brackets in Program line (e.g., 'B.Tech (CSE)' -> 'B.Tech')
    3. branch: text inside brackets after program (e.g., 'B.Tech (CSE)' -> 'CSE')
    4. id: value after CU-ID / Roll No / ID
    5. name: value after Name :
    6. email: standard email if present
    """
    # 1. Normalize full-width unicode punctuation & brackets
    text = re.sub(r'[\uFF1A\uFF1B\u2010\u2013\u2014]', ':', text)
    text = re.sub(r'[\uFF08\u3010]', '(', text)
    text = re.sub(r'[\uFF09\u3011]', ')', text)

    # 2. Join lines where label and value got split onto 2 lines e.g. "Name \n :Arnav Pundir"
    text = re.sub(r'(\b[A-Za-z\-]{2,15}\b)\s*\n\s*[:=]', r'\1:', text)

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    parsed = {
        "name": "",
        "id": "",
        "program": "",
        "branch": "",
        "enrollment_year": "",
        "email": ""
    }

    raw_full = " ".join(lines)

    # 1. Extract Email if present
    email_match = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', raw_full)
    if email_match:
        parsed["email"] = email_match.group(0).lower()

    # 2. Extract Student ID / CU-ID / Roll Number
    id_patterns = [
        r'(?:CU[\-_]?ID|CU\s*ID|Roll\s*(?:No|Num|Number)?|Student\s*ID|ID\s*No|Enrollment\s*(?:No|Num)?|Reg\s*(?:No|Num)?|URN)\s*[:;\-\.\s|!]+\s*([A-Z0-9/\-]+)',
        r'\b(CU\d{6,12}|STU\d{4,10}|\d{2}[A-Z]{2,4}\d{3,6}|[A-Z]{2,4}/\d{4,8}/\d{2,4})\b',
        r'\b([0-9]{7,12})\b'
    ]
    for pattern in id_patterns:
        match = re.search(pattern, raw_full, re.IGNORECASE)
        if match:
            candidate = match.group(1).strip()
            if not (len(candidate) == 4 and candidate.isdigit()):
                parsed["id"] = candidate.upper()
                break

    # 3. Extract Name
    name_match = re.search(r'(?:Student\s*Name|Name\s*of\s*Student|Name|Candidate)\s*[:;\-\.\s|!]+\s*([A-Za-z\s\.]{2,30})', raw_full, re.IGNORECASE)
    if name_match:
        candidate_name = name_match.group(1).strip()
        clean_name = re.split(r'\b(CU|ID|Session|Program|Roll|DOB|Blood)\b', candidate_name, flags=re.IGNORECASE)[0].strip()
        clean_name = re.sub(r'[^A-Za-z\s\.]', '', clean_name).strip()
        if len(clean_name) > 2 and clean_name.upper() not in ["STUDENT", "CARD", "IDENTITY", "COLLEGE", "UNIVERSITY", "DAY", "SCHOLAR", "BLOOD", "GROUP"]:
            parsed["name"] = clean_name.title()

    # Fallback Name heuristics if label not found
    if not parsed["name"]:
        for line in lines:
            words = line.split()
            if 2 <= len(words) <= 4 and all(w.isalpha() for w in words):
                upper_words = [w.upper() for w in words]
                ignored = {"STUDENT", "IDENTITY", "CARD", "COLLEGE", "UNIVERSITY", "CAMPUS", "DEPARTMENT", "FACULTY", "ACADEMIC", "YEAR", "ROLL", "BRANCH", "DAY", "SCHOLAR", "BLOOD", "GROUP", "FORMERLY", "KNOWN"}
                if not any(w in ignored for w in upper_words):
                    parsed["name"] = " ".join(words).title()
                    break

    # 4. Extract Session & Take 1st 4 digits for Enrollment Year
    session_match = re.search(r'(?:Session|Batch|Sessin|Year)\s*[:;\-\.\s|!]*\s*(20[1-3][0-9])', raw_full, re.IGNORECASE)
    if session_match:
        parsed["enrollment_year"] = session_match.group(1)
    else:
        year_match = re.search(r'\b(20[1-3][0-9])\b', raw_full)
        if year_match:
            parsed["enrollment_year"] = year_match.group(1)

    # 5. Extract Program and Branch from "Program : B.Tech (CSE)" line
    prog_line_match = re.search(r'(?:Program|Course|Degree|Prog)\s*[:;\-\.\s|!]+\s*([^\n\r]+)', raw_full, re.IGNORECASE)
    if prog_line_match:
        prog_line = prog_line_match.group(1).strip()
        bracket_match = re.search(r'([^\(\)\[\]]+?)\s*[\(\[]\s*([^\(\)\[\]]+)\s*[\)\]]', prog_line)
        if bracket_match:
            raw_prog = bracket_match.group(1).strip()
            raw_branch = bracket_match.group(2).strip()

            # Program mapping
            for pattern, p_val in PROGRAM_KEYWORDS.items():
                if re.search(pattern, raw_prog, re.IGNORECASE):
                    parsed["program"] = p_val
                    break
            if not parsed["program"]:
                parsed["program"] = raw_prog

            # Branch mapping from inside brackets
            for pattern, b_val in BRANCH_KEYWORDS.items():
                if re.search(pattern, raw_branch, re.IGNORECASE):
                    parsed["branch"] = b_val
                    break
            if not parsed["branch"]:
                parsed["branch"] = raw_branch.upper()
        else:
            # No brackets in program line
            for pattern, p_val in PROGRAM_KEYWORDS.items():
                if re.search(pattern, prog_line, re.IGNORECASE):
                    parsed["program"] = p_val
                    break
            if not parsed["program"]:
                parsed["program"] = prog_line

    # Fallback Program / Branch search across full text if not found above
    if not parsed["program"]:
        for pattern, program_val in PROGRAM_KEYWORDS.items():
            if re.search(pattern, raw_full, re.IGNORECASE):
                parsed["program"] = program_val
                break

    if not parsed["branch"]:
        for pattern, branch_val in BRANCH_KEYWORDS.items():
            if re.search(pattern, raw_full, re.IGNORECASE):
                parsed["branch"] = branch_val
                break

    # Construct institutional email using CU-ID / Student ID if email not explicitly found
    if not parsed["email"] and parsed["id"]:
        clean_id_str = parsed["id"].lower()
        parsed["email"] = f"{clean_id_str}@coeruniversity.ac.in"

    return parsed
