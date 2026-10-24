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
    r'\bB\.?\s*Pharm(?:a)?\b': 'B.Pharma',
    r'\bD\.?\s*Pharm(?:a)?\b': 'D.Pharma',
    r'\bB\.?\s*Com(?:\s*\([^\)]*\))?\b': 'B.Com',
    r'\bBA\s*LLB\b': 'BA LLB',
    r'\bBBA\s*LLB\b': 'BBA LLB',
    r'\bLL\.?B\b': 'LL.B',
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
    r'\b(Biotechnology|BT)\b': 'Biotechnology',
    r'\b(Pharmacy|Pharmaceutics)\b': 'Pharmacy',
    r'\b(Management|Marketing|HR|Finance|Business\s*Analytics)\b': 'Management',
    r'\b(General)\b': 'General'
}

# Common ID card stop-labels to prevent regexes from overflowing into next fields
STOP_LABELS_PATTERN = (
    r'(?:\bBlood(?:\s*Group)?\b|\bBG\b|\bDOB\b|\bDate\s*of\s*Birth\b|'
    r'\bFather(?:\'?s)?(?:\s*Name)?\b|\bMother(?:\'?s)?(?:\s*Name)?\b|'
    r'\bSession\b|\bBatch\b|\bRoll(?:\s*No)?\b|\bCU[\-_]?ID\b|\bCU\b|\bStudent\s*ID\b|\bID\b|'
    r'\bProgram\b|\bCourse\b|\bBranch\b|\bDepartment\b|'
    r'\bValid(?:\s*Upto|\s*Through|\s*Till)?\b|\bRegistrar\b|\bDean\b|\bDirector\b|'
    r'\bSign(?:ature)?\b|\bPhone\b|\bMobile\b|\bContact\b|\bEmergency\b|'
    r'\bAddress\b|\bHostel\b|\bLibrary\b|\bTransport\b|\bDay\s*Scholar\b)'
)

# Reject strings containing non-academic keywords
ACADEMIC_BLACKLIST = {
    'blood', 'group', 'o+ve', 'a+ve', 'b+ve', 'ab+ve', 'o-ve', 'a-ve', 'b-ve', 'ab-ve',
    'registrar', 'director', 'principal', 'dean', 'proctor', 'coordinator', 'authorized',
    'signature', 'sign', 'dob', 'date of birth', 'father', 'mother', 'address', 'phone',
    'mobile', 'contact', 'emergency', 'valid', 'validity', 'session', 'batch', 'roll',
    'identity', 'card', 'student', 'university', 'college', 'campus', 'hostel',
    'vivo', 'zeiss', 'oppo', 'redmi', 'samsung', 'iphone', 'xiaomi', 'realme', 'oneplus',
    'shot on', 'camera', 'dual camera', 'quad camera', 'megapixels'
}


def is_valid_academic_string(text: str) -> bool:
    """Check if candidate text is plausibly a legitimate academic program or branch."""
    if not text or not isinstance(text, str):
        return False
    t_clean = text.strip()
    if len(t_clean) < 2 or len(t_clean) > 35:
        return False
    if '\n' in t_clean or '\r' in t_clean:
        return False
    t_lower = t_clean.lower()
    for bl in ACADEMIC_BLACKLIST:
        if re.search(r'\b' + re.escape(bl) + r'\b', t_lower):
            return False
    return True


def sanitize_ocr_text(text: str) -> str:
    """Clean common phone camera watermarks and scanner artifacts before parsing."""
    cleaned_lines = []
    for line in text.splitlines():
        line_str = line.strip()
        if not line_str:
            continue
        lower_line = line_str.lower()
        if any(brand in lower_line for brand in ['vivo x', 'zeiss', 'shot on', 'ai dual camera', 'redmi note', 'quad camera', 'megapixels']):
            continue
        cleaned_lines.append(line_str)
    return "\n".join(cleaned_lines)


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


def parse_student_id_text(text: str, known_programs: list = None, known_branches: list = None) -> dict:
    """
    Parses OCR text output to extract structured student attributes based on university ID format:
    1. enrollment_year: 1st 4 digits of Session (e.g., '2024-2028' -> '2024')
    2. program: validated academic program (e.g., 'B.Tech', 'B.Pharma', 'BCA')
    3. branch: validated branch/specialization (e.g., 'CSE', 'AI-ML', 'ME')
    4. id: student roll number or institutional ID
    5. name: student name
    6. email: institutional or personal email
    """
    # 0. Sanitize text by stripping camera watermarks and EXIF timestamps
    text = sanitize_ocr_text(text)

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
            # Stop candidate before stop-labels if joined
            candidate_clean = re.split(STOP_LABELS_PATTERN, candidate, flags=re.IGNORECASE)[0].strip()
            if candidate_clean and not (len(candidate_clean) == 4 and candidate_clean.isdigit()):
                parsed["id"] = candidate_clean.upper()
                break

    # 3. Extract Name (Line-first, then full text fallback)
    name_line_match = re.search(r'(?:Student\s*Name|Name\s*of\s*Student|Name|Candidate)\s*[:;\-\.\s|!]+\s*([^\n\r]+)', text, re.IGNORECASE)
    if name_line_match:
        candidate_name = name_line_match.group(1).strip()
        clean_name = re.split(STOP_LABELS_PATTERN, candidate_name, flags=re.IGNORECASE)[0].strip()
        clean_name = re.sub(r'[^A-Za-z\s\.]', '', clean_name).strip()
        if len(clean_name) > 2 and clean_name.upper() not in ["STUDENT", "CARD", "IDENTITY", "COLLEGE", "UNIVERSITY", "DAY", "SCHOLAR", "BLOOD", "GROUP"]:
            parsed["name"] = clean_name.title()

    if not parsed["name"]:
        name_match = re.search(r'(?:Student\s*Name|Name\s*of\s*Student|Name|Candidate)\s*[:;\-\.\s|!]+\s*([A-Za-z\s\.]{2,40})', raw_full, re.IGNORECASE)
        if name_match:
            candidate_name = name_match.group(1).strip()
            clean_name = re.split(STOP_LABELS_PATTERN, candidate_name, flags=re.IGNORECASE)[0].strip()
            clean_name = re.sub(r'[^A-Za-z\s\.]', '', clean_name).strip()
            if len(clean_name) > 2 and clean_name.upper() not in ["STUDENT", "CARD", "IDENTITY", "COLLEGE", "UNIVERSITY", "DAY", "SCHOLAR", "BLOOD", "GROUP"]:
                parsed["name"] = clean_name.title()

    # Fallback Name heuristics if label not found
    if not parsed["name"]:
        for line in lines:
            words = line.split()
            if 2 <= len(words) <= 4 and all(w.isalpha() for w in words):
                upper_words = [w.upper() for w in words]
                ignored = {"STUDENT", "IDENTITY", "CARD", "COLLEGE", "UNIVERSITY", "CAMPUS", "DEPARTMENT", "FACULTY", "ACADEMIC", "YEAR", "ROLL", "BRANCH", "DAY", "SCHOLAR", "BLOOD", "GROUP", "FORMERLY", "KNOWN", "SIGNATURE", "REGISTRAR", "DIRECTOR"}
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

    # -------------------------------------------------------------------------
    # 5. Extract Program and Branch with Boundary Protection & Validation
    # -------------------------------------------------------------------------
    raw_prog_candidate = ""
    raw_branch_candidate = ""

    # Strategy A: Find line with Program/Course label
    prog_line_match = re.search(r'(?:Program|Course|Degree|Prog)\s*[:;\-\.\s|!]+\s*([^\n\r]+)', text, re.IGNORECASE)
    if prog_line_match:
        full_line = prog_line_match.group(1).strip()
        # Truncate at any subsequent field label (e.g. Blood Group, DOB, etc.)
        prog_line = re.split(STOP_LABELS_PATTERN, full_line, flags=re.IGNORECASE)[0].strip()

        # Check for bracket pattern: e.g. "B.Tech (CSE)" or "BCA [IT]"
        bracket_match = re.search(r'([^\(\)\[\]]+?)\s*[\(\[]\s*([^\(\)\[\]]+)\s*[\)\]]', prog_line)
        if bracket_match:
            raw_prog_candidate = bracket_match.group(1).strip()
            raw_branch_candidate = bracket_match.group(2).strip()
        else:
            raw_prog_candidate = prog_line

    # Strategy B: Find line with explicit Branch / Department / Specialization label
    branch_line_match = re.search(r'(?:Branch|Department|Dept|Specialization|Stream)\s*[:;\-\.\s|!]+\s*([^\n\r]+)', text, re.IGNORECASE)
    if branch_line_match:
        full_b_line = branch_line_match.group(1).strip()
        b_line = re.split(STOP_LABELS_PATTERN, full_b_line, flags=re.IGNORECASE)[0].strip()
        if not raw_branch_candidate or len(b_line) > len(raw_branch_candidate):
            raw_branch_candidate = b_line

    # Dynamic catalog matching helper
    def match_against_catalog(candidate: str, catalog: list) -> str:
        if not candidate or not catalog:
            return ""
        c_norm = re.sub(r'[^a-zA-Z0-9]', '', candidate).lower()
        for item in catalog:
            if not item:
                continue
            i_norm = re.sub(r'[^a-zA-Z0-9]', '', str(item)).lower()
            if c_norm == i_norm or (len(c_norm) >= 3 and c_norm in i_norm):
                return str(item)
        return ""

    # Resolve Program
    # 1. Match against known_programs from DB if provided
    if known_programs and raw_prog_candidate:
        matched = match_against_catalog(raw_prog_candidate, known_programs)
        if matched:
            parsed["program"] = matched

    # 2. Match against PROGRAM_KEYWORDS
    if not parsed["program"] and raw_prog_candidate:
        for pattern, p_val in PROGRAM_KEYWORDS.items():
            if re.search(pattern, raw_prog_candidate, re.IGNORECASE):
                parsed["program"] = p_val
                break

    # 3. Fallback: Search PROGRAM_KEYWORDS across full text if line wasn't found
    if not parsed["program"]:
        for pattern, program_val in PROGRAM_KEYWORDS.items():
            if re.search(pattern, raw_full, re.IGNORECASE):
                parsed["program"] = program_val
                break

    # 4. If raw_prog_candidate is structurally a valid academic string and has no blacklist words
    if not parsed["program"] and is_valid_academic_string(raw_prog_candidate):
        parsed["program"] = raw_prog_candidate.title()

    # Resolve Branch
    # 1. Match against known_branches from DB if provided
    if known_branches and raw_branch_candidate:
        matched = match_against_catalog(raw_branch_candidate, known_branches)
        if matched:
            parsed["branch"] = matched

    # 2. Match against BRANCH_KEYWORDS
    if not parsed["branch"] and raw_branch_candidate:
        for pattern, b_val in BRANCH_KEYWORDS.items():
            if re.search(pattern, raw_branch_candidate, re.IGNORECASE):
                parsed["branch"] = b_val
                break

    # 3. Fallback: Search BRANCH_KEYWORDS across full text
    if not parsed["branch"]:
        for pattern, branch_val in BRANCH_KEYWORDS.items():
            if re.search(pattern, raw_full, re.IGNORECASE):
                parsed["branch"] = branch_val
                break

    # 4. If raw_branch_candidate is structurally a valid academic string and has no blacklist words
    if not parsed["branch"] and is_valid_academic_string(raw_branch_candidate):
        parsed["branch"] = raw_branch_candidate.upper()

    # Final sanity check: NEVER allow blacklisted strings in program or branch
    if not is_valid_academic_string(parsed["program"]):
        parsed["program"] = ""
    if not is_valid_academic_string(parsed["branch"]):
        parsed["branch"] = ""

    # Construct institutional email using CU-ID / Student ID if email not explicitly found
    if not parsed["email"] and parsed["id"]:
        clean_id_str = parsed["id"].lower()
        parsed["email"] = f"{clean_id_str}@coeruniversity.ac.in"

    return parsed

    # Construct institutional email using CU-ID / Student ID if email not explicitly found
    if not parsed["email"] and parsed["id"]:
        clean_id_str = parsed["id"].lower()
        parsed["email"] = f"{clean_id_str}@coeruniversity.ac.in"

    return parsed
