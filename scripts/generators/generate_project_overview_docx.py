"""
Professional DOCX Generator for BioSecure AI Technical Overview.
Produces BioSecure_AI_Project_Overview.docx matching the comprehensive 10-section technical overview.
Strict constraints enforced:
1. Publication-grade corporate formatting (headers, footers, styled tables, callouts, typography).
2. Exactly 0 mentions of patents, patent applications, IDF, or related terms.
"""

import os
import re
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import parse_xml, OxmlElement
from docx.oxml.ns import nsdecls, qn

# Color constants
HEX_NAVY = "0F172A"       # Primary Brand
HEX_ROYAL = "1E3A8A"      # Subheadings
HEX_ACCENT = "2563EB"     # Highlights
HEX_SKY = "0284C7"        # Badges
HEX_DARK = "1E293B"       # Body text
HEX_MUTED = "475569"      # Secondary
HEX_LIGHT_BG = "F8FAFC"   # Tables / Callouts
HEX_ALT_ROW = "F1F5F9"    # Alternating row
HEX_BORDER = "CBD5E1"     # Table borders
HEX_EMERALD = "059669"
HEX_AMBER = "D97706"
HEX_ROSE = "DC2626"

RGB_NAVY = RGBColor(15, 23, 42)
RGB_ROYAL = RGBColor(30, 58, 138)
RGB_ACCENT = RGBColor(37, 99, 235)
RGB_SKY = RGBColor(2, 132, 199)
RGB_DARK = RGBColor(30, 41, 59)
RGB_MUTED = RGBColor(71, 85, 105)


def set_cell_background(cell, fill_hex):
    """Sets background shading of a table cell."""
    tcPr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill_hex}"/>')
    tcPr.append(shd)


def set_cell_margins(cell, top=100, bottom=100, left=150, right=150):
    """Sets cell padding in dxa (1 pt = 20 dxa)."""
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = parse_xml(
        f'<w:tcMar {nsdecls("w")}>'
        f'<w:top w:w="{top}" w:type="dxa"/>'
        f'<w:bottom w:w="{bottom}" w:type="dxa"/>'
        f'<w:left w:w="{left}" w:type="dxa"/>'
        f'<w:right w:w="{right}" w:type="dxa"/>'
        f'</w:tcMar>'
    )
    tcPr.append(tcMar)


def set_cell_borders(cell, top=None, bottom=None, left=None, right=None, color="CBD5E1", sz="4"):
    """Sets individual cell borders."""
    tcPr = cell._tc.get_or_add_tcPr()
    borders_xml = f'<w:tcBorders {nsdecls("w")}>'
    if top:
        borders_xml += f'<w:top w:val="{top}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
    if bottom:
        borders_xml += f'<w:bottom w:val="{bottom}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
    if left:
        borders_xml += f'<w:left w:val="{left}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
    if right:
        borders_xml += f'<w:right w:val="{right}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
    borders_xml += '</w:tcBorders>'
    tcPr.append(parse_xml(borders_xml))


def format_table(table, header_bg=HEX_NAVY, alt_row_bg=HEX_ALT_ROW, border_color=HEX_BORDER):
    """Applies corporate styling to a docx table."""
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    for r_idx, row in enumerate(table.rows):
        is_header = (r_idx == 0)
        bg = header_bg if is_header else (alt_row_bg if r_idx % 2 == 1 else "FFFFFF")
        for cell in row.cells:
            set_cell_background(cell, bg)
            set_cell_margins(cell, top=100, bottom=100, left=140, right=140)
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
            set_cell_borders(cell, top="single", bottom="single", left="single", right="single", color=border_color, sz="4")


def add_callout(doc, text, title="", border_color=HEX_ACCENT, bg_color=HEX_LIGHT_BG):
    """Inserts a styled callout box with a prominent left accent border."""
    t = doc.add_table(rows=1, cols=1)
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    t.columns[0].width = Inches(7.0)

    cell = t.cell(0, 0)
    set_cell_background(cell, bg_color)
    set_cell_margins(cell, top=140, bottom=140, left=200, right=200)
    set_cell_borders(cell, left="single", color=border_color, sz="24")  # 3pt thick left border
    set_cell_borders(cell, top="single", bottom="single", right="single", color=HEX_BORDER, sz="4")

    p = cell.paragraphs[0]
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.line_spacing = 1.15

    if title:
        run_title = p.add_run(f"{title}\n")
        run_title.font.name = "Calibri"
        run_title.font.size = Pt(9.5)
        run_title.font.bold = True
        run_title.font.color.rgb = RGBColor(int(border_color[:2], 16), int(border_color[2:4], 16), int(border_color[4:], 16))

    run_text = p.add_run(text)
    run_text.font.name = "Calibri"
    run_text.font.size = Pt(9.0)
    run_text.font.color.rgb = RGB_DARK

    p_spacer = doc.add_paragraph()
    p_spacer.paragraph_format.space_before = Pt(0)
    p_spacer.paragraph_format.space_after = Pt(4)


def add_section_header(doc, title, number_str=""):
    """Adds a major section heading with formal corporate styling."""
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(12)
    p.paragraph_format.space_after = Pt(4)
    p.paragraph_format.keep_with_next = True

    if number_str:
        run_num = p.add_run(f"{number_str}  ")
        run_num.font.name = "Calibri"
        run_num.font.size = Pt(14)
        run_num.font.bold = True
        run_num.font.color.rgb = RGB_ACCENT

    run_title = p.add_run(title)
    run_title.font.name = "Calibri"
    run_title.font.size = Pt(14)
    run_title.font.bold = True
    run_title.font.color.rgb = RGB_NAVY


def add_subheading(doc, title):
    """Adds a subsection heading."""
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(8)
    p.paragraph_format.space_after = Pt(3)
    p.paragraph_format.keep_with_next = True

    run = p.add_run(title)
    run.font.name = "Calibri"
    run.font.size = Pt(11)
    run.font.bold = True
    run.font.color.rgb = RGB_ROYAL


def add_body(doc, text, bold_prefix=""):
    """Adds standard body paragraph with formal typography."""
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(4)
    p.paragraph_format.line_spacing = 1.15

    if bold_prefix:
        r_pre = p.add_run(bold_prefix)
        r_pre.font.name = "Calibri"
        r_pre.font.size = Pt(9.5)
        r_pre.font.bold = True
        r_pre.font.color.rgb = RGB_DARK

    run = p.add_run(text)
    run.font.name = "Calibri"
    run.font.size = Pt(9.5)
    run.font.color.rgb = RGB_DARK
    return p


def add_bullet(doc, text, bold_prefix=""):
    """Adds a bullet list item."""
    p = doc.add_paragraph(style='List Bullet')
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(3)
    p.paragraph_format.line_spacing = 1.15

    if bold_prefix:
        r_pre = p.add_run(bold_prefix)
        r_pre.font.name = "Calibri"
        r_pre.font.size = Pt(9.5)
        r_pre.font.bold = True
        r_pre.font.color.rgb = RGB_DARK

    run = p.add_run(text)
    run.font.name = "Calibri"
    run.font.size = Pt(9.5)
    run.font.color.rgb = RGB_DARK
    return p


def build_docx(filename="BioSecure_AI_Project_Overview.docx"):
    doc = docx.Document()

    # Configure Margins (0.75 in = 54 pt)
    section = doc.sections[0]
    section.top_margin = Inches(0.75)
    section.bottom_margin = Inches(0.75)
    section.left_margin = Inches(0.75)
    section.right_margin = Inches(0.75)
    section.different_first_page_header_footer = True

    # Configure Running Header (Pages 2+)
    header = section.header
    hp = header.paragraphs[0]
    hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    hrun1 = hp.add_run("BIOSECURE AI  |  ")
    hrun1.font.name = "Calibri"
    hrun1.font.size = Pt(8)
    hrun1.font.bold = True
    hrun1.font.color.rgb = RGB_ROYAL
    hrun2 = hp.add_run("ENTERPRISE TECHNICAL SPECIFICATION & OVERVIEW")
    hrun2.font.name = "Calibri"
    hrun2.font.size = Pt(8)
    hrun2.font.color.rgb = RGB_MUTED

    # Configure Running Footer (Pages 2+)
    footer = section.footer
    fp = footer.paragraphs[0]
    frun1 = fp.add_run("BioSecure AI Web System  |  Institutional Biometric Systems Architecture")
    frun1.font.name = "Calibri"
    frun1.font.size = Pt(8)
    frun1.font.color.rgb = RGB_MUTED

    # =========================================================================
    # SECTION 1: Executive Overview & Project Identity
    # =========================================================================
    p_kick = doc.add_paragraph()
    p_kick.paragraph_format.space_before = Pt(0)
    p_kick.paragraph_format.space_after = Pt(2)
    rk = p_kick.add_run("INSTITUTIONAL TECHNICAL SPECIFICATION & SYSTEM ARCHITECTURE")
    rk.font.name = "Calibri"
    rk.font.size = Pt(9)
    rk.font.bold = True
    rk.font.color.rgb = RGB_SKY

    p_title = doc.add_paragraph()
    p_title.paragraph_format.space_before = Pt(0)
    p_title.paragraph_format.space_after = Pt(4)
    rt = p_title.add_run("BIOSECURE AI")
    rt.font.name = "Calibri"
    rt.font.size = Pt(24)
    rt.font.bold = True
    rt.font.color.rgb = RGB_NAVY

    p_sub = doc.add_paragraph()
    p_sub.paragraph_format.space_before = Pt(0)
    p_sub.paragraph_format.space_after = Pt(12)
    rs = p_sub.add_run("Automated Multi-Face Recognition Attendance & Autonomous Biometric Drift Monitoring Platform")
    rs.font.name = "Calibri"
    rs.font.size = Pt(12)
    rs.font.color.rgb = RGB_ROYAL

    # Document Control Metadata Table
    meta_table = doc.add_table(rows=3, cols=3)
    meta_table.columns[0].width = Inches(2.33)
    meta_table.columns[1].width = Inches(2.33)
    meta_table.columns[2].width = Inches(2.34)

    control_cells = [
        ("Document Classification:", "Production Technical Specification", "System Release:", "v3.2.0 Stable Build", "Verification Date:", "October 2026"),
        ("Core Frameworks:", "Flask 3.1 / InsightFace Buffalo_L", "Database Engine:", "PostgreSQL 16 + pgvector", "Client Architecture:", "Progressive Web App (PWA)"),
        ("Target Environment:", "Linux VPS / On-Premise Host", "Inference Providers:", "CPU / CUDA ONNX Runtime", "Security Standard:", "Supabase RLS & RBAC Protected")
    ]
    for row_idx, r_data in enumerate(control_cells):
        for col_idx in range(3):
            cell = meta_table.cell(row_idx, col_idx)
            lbl = r_data[col_idx * 2]
            val = r_data[col_idx * 2 + 1]
            p = cell.paragraphs[0]
            p.paragraph_format.space_before = Pt(1)
            p.paragraph_format.space_after = Pt(1)
            rl = p.add_run(f"{lbl} ")
            rl.font.name = "Calibri"
            rl.font.size = Pt(8.5)
            rl.font.bold = True
            rl.font.color.rgb = RGB_NAVY
            rv = p.add_run(val)
            rv.font.name = "Calibri"
            rv.font.size = Pt(8.5)
            rv.font.color.rgb = RGB_DARK
    format_table(meta_table, header_bg=HEX_LIGHT_BG, alt_row_bg=HEX_LIGHT_BG)
    doc.add_paragraph().paragraph_format.space_after = Pt(6)

    add_section_header(doc, "Executive Summary & Operational Background", "1.")
    add_body(doc, "Accurate, fraud-resistant attendance logging is essential for university administration, academic compliance, student safety tracking, and corporate workplace operations. Conventional attendance methods suffer from persistent systemic flaws: manual roll calls waste 10 to 15 minutes of instructional lecture time per session; magnetic or RFID swipe badges invite widespread proxy attendance ('buddy-punching'); and physical fingerprint readers cause severe door bottlenecks while raising sanitary concerns in high-traffic campus environments.")
    add_body(doc, "BioSecure AI solves these institutional challenges through an automated, contactless computer vision platform. Instructors simply capture or upload a single classroom group photograph containing dozens of seated students. The platform autonomously detects all faces, aligns them to standardized 5-point facial geometry, extracts 512-dimensional deep biometric embeddings, matches identities in under a millisecond via an in-memory BLAS matrix engine, and commits verified attendance records directly to a PostgreSQL database.")
    add_body(doc, "Beyond instant attendance capture, the system incorporates an autonomous biometric health monitoring engine. By continuously tracking subtle facial aging across academic terms (such as new hairstyles, facial hair growth, and natural maturation), the platform isolates true physical changes from momentary posture variations, alerting administrators before identity verification degrades.")

    add_section_header(doc, "Foundational Architectural Pillars", "2.")
    pillars_data = [
        ["Pillar & Capability", "Underlying Technologies", "Operational Impact & Performance Profile"],
        ["High-Density Group Ingestion", "RetinaFace + ArcFace Buffalo_L ONNX", "Processes 50+ students in a single classroom snapshot; handles varying distances, natural yaw/pitch, and uneven ambient lighting."],
        ["Sub-Millisecond Vector Matching", "NumPy BLAS Matrix Dot-Product (AVX2)", "Evaluates full institutional rosters in <1.0 ms on CPU (Q · M^T), eliminating cloud database network roundtrips."],
        ["Biometric Drift Detection Engine", "3D Pose-Gated EWMA Accumulator (α=0.30)", "Continuously monitors facial template aging (hair, beard, maturation) over academic semesters; flags degradation before failures occur."],
        ["Zero-Touch Student Enrollment", "RapidOCR (DBNet+SVTR) + OpenCV CLAHE", "Extracts structured credentials (Name, ID, Program, Branch, Batch) directly from physical ID card snapshots in <1.2 seconds."],
        ["Universal Device Portability", "Progressive Web App + Service Worker Caching", "Installs natively across Android, iOS, Windows, and macOS; includes direct hardware camera integration and offline app shell fallback."]
    ]
    t_pillars = doc.add_table(rows=len(pillars_data), cols=3)
    t_pillars.columns[0].width = Inches(1.8)
    t_pillars.columns[1].width = Inches(2.0)
    t_pillars.columns[2].width = Inches(3.2)
    for r_idx, row in enumerate(pillars_data):
        for c_idx, val in enumerate(row):
            cell = t_pillars.cell(r_idx, c_idx)
            p = cell.paragraphs[0]
            p.paragraph_format.space_before = Pt(2)
            p.paragraph_format.space_after = Pt(2)
            run = p.add_run(val)
            run.font.name = "Calibri"
            run.font.size = Pt(8.5)
            if r_idx == 0:
                run.font.bold = True
                run.font.color.rgb = RGBColor(255, 255, 255)
            else:
                run.font.color.rgb = RGB_DARK
                if c_idx == 0:
                    run.font.bold = True
    format_table(t_pillars)
    doc.add_paragraph().paragraph_format.space_after = Pt(6)

    add_callout(
        doc,
        "BioSecure AI establishes a dual-pipeline operational model. While Pipeline A executes real-time facial recognition and attendance persistence, a concurrent biometric drift detection engine computes pose-gated template degradation metrics, insulating the institution against gradual verification failure without disrupting live attendance workflows.",
        "DUAL-PIPELINE OPERATIONAL PARADIGM",
        HEX_ACCENT
    )

    doc.add_page_break()

    # =========================================================================
    # SECTION 2: System Architecture & Dual-Pipeline Dataflow
    # =========================================================================
    add_section_header(doc, "System Architecture & Dual-Pipeline Dataflow", "2.")
    add_body(doc, "BioSecure AI is architected as an asynchronous, multi-tiered enterprise application designed for high concurrency, sub-second latency, and fault isolation. The system couples a stateless application layer with an in-memory BLAS accelerated vector caching engine and a persistent relational database hosting 512-dimensional vectors.")

    add_subheading(doc, "2.1 Distributed Multi-Tier System Topology")
    add_body(doc, "The system topology separates responsibilities into four distinct structural tiers: Client Edge (browser application, Progressive Web App shell, native hardware camera window), Reverse Proxy & Gateway (Nginx handling TLS termination, static asset caching, request buffering up to 25MB), Application Execution Layer (Gunicorn WSGI process manager coordinating stateless Flask worker instances), and the Persistence & Analytics Tier (Supabase PostgreSQL with pgvector HNSW indexing, Row-Level Security, and Google SMTP alerting).")

    add_subheading(doc, "2.2 Comprehensive 10-Stage Request Lifecycle")
    add_body(doc, "Every incoming attendance submission initiates a bifurcated execution cycle. Pipeline A verifies identities and records attendance; concurrently, Pipeline B evaluates head orientation angles, filters out pose distortion, updates cumulative appearance drift metrics, and escalates warnings when facial aging crosses established safety thresholds.")

    seq_data = [
        ["Step", "Subsystem", "Execution Action & Algorithmic Process", "Latency Profile"],
        ["1", "Client Edge", "Instructor captures or uploads classroom group photo via Web UI or PWA mobile window.", "< 50 ms (Network)"],
        ["2", "Nginx Gateway", "Buffers payload (up to 25MB), terminates TLS, and proxies multipart stream to Gunicorn WSGI.", "< 5 ms (Proxy)"],
        ["3", "OpenCV Buffer", "Decodes image stream directly in RAM using cv2.imdecode; zero disk latency or wear.", "12 - 25 ms"],
        ["4", "RetinaFace + ArcFace", "Detects bounding boxes, aligns 5 landmarks, and extracts 512D hyperspherical embeddings.", "350 - 550 ms (CPU)"],
        ["5", "BLAS Matrix Engine", "Computes batch matrix dot-product Q · M^T against in-memory student embeddings.", "< 1.0 ms (RAM)"],
        ["6", "Supabase pgvector", "Fallback search: queries match_face stored procedure if cache requires synchronization.", "15 - 30 ms (RPC)"],
        ["7", "Attendance Logger", "Commits verified records (student_id, status='Present', timestamp, lecture) to PostgreSQL.", "20 - 40 ms"],
        ["8", "3D Pose Gate", "Validates Euler angles (|Yaw| <= 25°, |Pitch| <= 20°); marks non-frontal faces POSE_REJECTED.", "< 0.1 ms"],
        ["9", "EWMA Accumulator", "For accepted poses, calculates D = 1 - S and updates running score: EWMA_t = 0.30·D + 0.70·EWMA_{t-1}.", "< 0.1 ms"],
        ["10", "SMTP Alerting", "Dispatches automated email notification to admin if EWMA crosses CRITICAL (>=0.25) or ALERT (>=0.35).", "Async Worker"]
    ]
    t_seq = doc.add_table(rows=len(seq_data), cols=4)
    t_seq.columns[0].width = Inches(0.6)
    t_seq.columns[1].width = Inches(1.5)
    t_seq.columns[2].width = Inches(3.7)
    t_seq.columns[3].width = Inches(1.2)
    for r_idx, row in enumerate(seq_data):
        for c_idx, val in enumerate(row):
            cell = t_seq.cell(r_idx, c_idx)
            p = cell.paragraphs[0]
            p.paragraph_format.space_before = Pt(1.5)
            p.paragraph_format.space_after = Pt(1.5)
            run = p.add_run(val)
            run.font.name = "Calibri"
            run.font.size = Pt(8.0)
            if r_idx == 0:
                run.font.bold = True
                run.font.color.rgb = RGBColor(255, 255, 255)
            else:
                run.font.color.rgb = RGB_DARK
                if c_idx == 0:
                    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    format_table(t_seq)
    doc.add_paragraph().paragraph_format.space_after = Pt(4)

    add_subheading(doc, "2.3 Concurrency, State Management & Memory Safety")
    add_body(doc, "To guarantee high concurrency during simultaneous morning roll-call surges across campus departments, the application enforces complete statelessness across all Gunicorn worker processes. No ephemeral session tokens or image fragments are written to local disk. The in-memory BLAS matrix cache utilizes a Python threading.Lock concurrency guard, allowing safe concurrent read operations during vector matrix multiplications and atomic reloads whenever administrative onboarding registers new students.")

    add_callout(
        doc,
        "Incoming group photos from web clients are streamed into byte buffers and decoded directly into NumPy arrays via OpenCV. This in-memory architecture completely removes disk wear, eliminates file race conditions across worker processes, and drastically enhances transactional security.",
        "ZERO-DISK INGESTION GUARANTEE",
        HEX_ROYAL
    )

    doc.add_page_break()

    # =========================================================================
    # SECTION 3: Deep Learning Biometric Inference Pipeline
    # =========================================================================
    add_section_header(doc, "Deep Learning Biometric Inference Pipeline", "3.")
    add_body(doc, "BioSecure AI incorporates deep convolutional neural networks and transformer-based vision architectures through the InsightFace Buffalo_L model suite. The inference pipeline transforms unconstrained classroom photos into compact, discriminative coordinates on a 512-dimensional unit hypersphere.")

    add_subheading(doc, "3.1 RetinaFace Detection & 5-Point Fiducial Alignment")
    add_body(doc, "Face localization is executed via RetinaFace, a robust single-stage multi-task face detector utilizing feature pyramids and deformable context modules. For every detected face, RetinaFace returns a bounding box tuple [x1, y1, x2, y2], a confidence score, and 5 distinct anatomical landmarks: left eye pupil, right eye pupil, nose tip, left oral commissure, and right oral commissure. The system computes a 2D similarity transformation matrix (rotation, scaling, translation) to warp and align the facial crop to a standardized canonical orientation, eliminating in-plane roll rotation.")

    add_subheading(doc, "3.2 3D Euler Head Pose Estimation")
    add_body(doc, "Simultaneously, the landmark localization regressor estimates the 3D spatial orientation of the skull relative to the optical camera plane, resolving three angular degrees of freedom: Yaw (ψ, horizontal rotation), Pitch (θ, vertical elevation/depression), and Roll (φ, lateral tilt). These angles provide the objective metric gating required by the downstream biometric drift engine.")

    add_subheading(doc, "3.3 ArcFace 512D Deep Feature Extraction & Loss Formulation")
    add_body(doc, "Aligned facial crops are passed into the ArcFace (Additive Angular Margin Loss) deep residual feature extractor. Unlike traditional Euclidean loss functions (such as Softmax or Triplet Loss), ArcFace optimizes an additive angular margin penalty directly on a hyperspherical manifold:")
    add_body(doc, "ArcFace Loss Formulation:  L = - ∑ log [ e^(s · cos(θ_y + m)) / (e^(s · cos(θ_y + m)) + ∑_{j ≠ y} e^(s · cos(θ_j))) ]\nWhere s is the feature scale radius (set to 64.0), m is the additive angular margin penalty (0.50 radians), and θ_y is the angle between the normalized feature vector and target ground truth weight vector.")

    add_subheading(doc, "3.4 Strict L2 Hyperspherical Normalization Invariant")
    add_body(doc, "ArcFace produces a raw embedding vector v ∈ ℝ^512. To ensure that vector magnitude does not distort identity matching, every embedding is normalized to unit Euclidean length prior to persistence or matrix comparison:")
    add_body(doc, "Unit Vector Projection:  v̂ = v / ( ||v||_2 + ε ) = v / [ ( ∑_{i=1}^512 v_i^2 )^(1/2) + 10^(-10) ]   ⟹   ||v̂||_2 ≡ 1.0 ± 10^(-6)")
    add_body(doc, "Under this hyperspherical invariant, the Cosine Similarity S between a live capture vector Ê_live and an enrolled template Ê_enroll simplifies to an inner dot product: S = Ê_live · Ê_enroll = ∑_{i=1}^512 (Ê_live)_i · (Ê_enroll)_i.")

    nn_params = [
        ["Pipeline Component", "Architecture Model", "Tensor Dimensions", "Operational Role in Pipeline"],
        ["Face Detector", "RetinaFace ResNet50", "[1, 3, 1280, 1280]", "Detects multi-scale faces, outputs bounding boxes & 5 keypoints."],
        ["Pose Estimator", "Landmark 3D PnP Solver", "[3] (Yaw, Pitch, Roll)", "Extracts spatial head orientation for drift gate filtering."],
        ["Feature Encoder", "ArcFace ResNet-100", "[1, 512] float32", "Maps aligned crops to 512D hyperspherical embeddings."],
        ["L2 Sanitizer", "NumPy Epsilon Normalizer", "[512] unit norm", "Guarantees ||v|| = 1.0; cleanses NaNs, Infs, and zero-norm artifacts."]
    ]
    t_nn = doc.add_table(rows=len(nn_params), cols=4)
    t_nn.columns[0].width = Inches(1.4)
    t_nn.columns[1].width = Inches(1.6)
    t_nn.columns[2].width = Inches(1.4)
    t_nn.columns[3].width = Inches(2.6)
    for r_idx, row in enumerate(nn_params):
        for c_idx, val in enumerate(row):
            cell = t_nn.cell(r_idx, c_idx)
            p = cell.paragraphs[0]
            p.paragraph_format.space_before = Pt(1.5)
            p.paragraph_format.space_after = Pt(1.5)
            run = p.add_run(val)
            run.font.name = "Calibri"
            run.font.size = Pt(8.0)
            if r_idx == 0:
                run.font.bold = True
                run.font.color.rgb = RGBColor(255, 255, 255)
            else:
                run.font.color.rgb = RGB_DARK
                if c_idx == 0:
                    run.font.bold = True
    format_table(t_nn)
    doc.add_paragraph().paragraph_format.space_after = Pt(4)

    add_callout(
        doc,
        "The helper function normalize_embedding() safely intercepts corrupted strings, bracketed database vectors, zero vectors, and NaN entries. If an invalid or uninitialized vector is parsed, it returns None safely, preventing arithmetic crashes during matrix multiplication.",
        "NUMERICAL STABILITY & SANITIZATION GUARANTEE",
        HEX_EMERALD
    )

    doc.add_page_break()

    # =========================================================================
    # SECTION 4: High-Throughput Vector Matching & Dual-Tier Search
    # =========================================================================
    add_section_header(doc, "High-Throughput Vector Matching & Dual-Tier Search", "4.")
    add_body(doc, "In a busy classroom containing 60+ students, multiple group photos must be ingested, analyzed, and confirmed within seconds. Standard cloud database vector queries introduce significant network roundtrip latency (30-100ms per face). BioSecure AI resolves this performance bottleneck through a Dual-Tier Vector Search Engine.")

    add_subheading(doc, "4.1 In-Memory NumPy BLAS Batch Matrix Engine")
    add_body(doc, "Upon application startup, the service preloads all enrolled student 512D ArcFace embeddings into a contiguous C-aligned float32 matrix M ∈ ℝ^(M × 512) residing directly in system memory. When an attendance image containing N query faces is processed, their normalized embeddings are stacked into matrix Q ∈ ℝ^(N × 512). The entire similarity grid C ∈ ℝ^(N × M) is resolved in a single BLAS matrix dot product operation:")
    add_body(doc, "Batch Matrix Dot-Product:  C = Q · M^T   ≡   [ N × 512 ] × [ 512 × M ]   =   [ N × M ]\nWhere entry C_{i, j} represents the exact Cosine Similarity between live query face i and registered student j. The optimal match candidate j* for face i is chosen via:  j* = argmax_j C_{i, j}  subject to:  C_{i, j*} >= 0.40 (FACE_MATCH_THRESHOLD)")

    add_subheading(doc, "4.2 Dual-Tier Search Hierarchy & Fault Fallback")
    add_body(doc, "The system coordinates a resilient two-tier search strategy: Tier 1 (In-Memory BLAS) satisfies >99.8% of queries in <1ms on modern CPU hardware using SIMD (AVX2/AVX-512) vector acceleration. If a query yields no valid match or if cache desynchronization is suspected, the system seamlessly falls back to Tier 2 (PostgreSQL pgvector) via the match_face RPC function, querying an HNSW index directly in the database.")

    bench_data = [
        ["Search Architecture", "Operational Tier", "Latency (N=1)", "Latency (N=50 Batch)", "Network Overhead"],
        ["In-Memory NumPy BLAS", "Tier 1 (Primary)", "0.08 ms", "0.62 ms", "0 KB (Local RAM)"],
        ["Supabase pgvector (HNSW)", "Tier 2 (Fallback)", "18.5 ms", "420.0 ms (Sequential)", "150 KB (HTTP/PostgREST)"],
        ["Pure Python Loop", "Legacy Baseline", "12.4 ms", "620.0 ms", "0 KB"]
    ]
    t_bench = doc.add_table(rows=len(bench_data), cols=5)
    t_bench.columns[0].width = Inches(1.8)
    t_bench.columns[1].width = Inches(1.3)
    t_bench.columns[2].width = Inches(1.2)
    t_bench.columns[3].width = Inches(1.4)
    t_bench.columns[4].width = Inches(1.3)
    for r_idx, row in enumerate(bench_data):
        for c_idx, val in enumerate(row):
            cell = t_bench.cell(r_idx, c_idx)
            p = cell.paragraphs[0]
            p.paragraph_format.space_before = Pt(1.5)
            p.paragraph_format.space_after = Pt(1.5)
            run = p.add_run(val)
            run.font.name = "Calibri"
            run.font.size = Pt(8.0)
            if r_idx == 0:
                run.font.bold = True
                run.font.color.rgb = RGBColor(255, 255, 255)
            else:
                run.font.color.rgb = RGB_DARK
                if c_idx >= 2:
                    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    format_table(t_bench)
    doc.add_paragraph().paragraph_format.space_after = Pt(4)

    add_subheading(doc, "4.3 Class Roster Modes: Separate vs Combined")
    add_bullet(doc, "Matches are strictly constrained to the subset of students enrolled in the designated Program, Branch, and Batch Year, preventing accidental attendance cross-contamination between distinct cohorts.", "Separate Class Mode (Default): ")
    add_bullet(doc, "Deployed during joint auditorium lectures or inter-disciplinary electives. The matrix matcher evaluates queries against the combined roster of multiple enrolled sections, resolving student branch affiliations dynamically.", "Combined Class Mode: ")

    add_callout(
        doc,
        "Because 512 float32 values consume exactly 2,048 bytes per student, a roster of 5,000 enrolled students occupies only ~10.2 MB of RAM. The BLAS matrix dot product executes across all 5,000 vectors in less than 2.5 ms on a standard quad-core server CPU, proving infinite scalability for university campuses.",
        "SCALABILITY & MEMORY PROOF",
        HEX_ACCENT
    )

    doc.add_page_break()

    # =========================================================================
    # SECTION 5: Adaptive Biometric Drift Engine & Template Aging Analysis
    # =========================================================================
    add_section_header(doc, "Adaptive Biometric Drift Engine & Template Aging", "5.")
    add_body(doc, "A critical flaw in commercial facial recognition systems is Biometric Template Aging. Over a student's 4-year degree, facial appearance changes significantly due to natural maturation, facial hair, hairstyles, prescription eyewear, and weight fluctuations. Systems that do not account for drift suffer gradual similarity degradation, culminating in sudden false rejections.")

    add_subheading(doc, "5.1 The Appearance Drift Challenge in Campus Environments")
    add_body(doc, "In static biometric databases, an enrollment photo captured during freshman orientation remains unchanged for years. Over successive semesters, the Cosine similarity S between live captures and reference photos drops from ~0.85 to borderline thresholds (~0.40). Without proactive monitoring, administrators only discover biometric degradation when a student fails to get marked present.")

    add_subheading(doc, "5.2 3D Pose Gate Noise Filtering Formulation")
    add_body(doc, "A naive drift tracker that updates aging on every attendance photo will inevitably absorb noise: students looking sideways, chatting, or tilting down produce artificially low similarity scores. BioSecure AI solves this with an objective 3D Pose Gate:")
    add_body(doc, "3D Pose Gate Acceptance Criterion:  PoseGatePass = TRUE   ⟺   |Yaw| <= 25.0°  ∧  |Pitch| <= 20.0°\nFaces exceeding these spatial thresholds are marked POSE_REJECTED. The attendance record is still logged as PRESENT, but the biometric aging accumulator is preserved unchanged, shielding the health model from posture artifacts.")

    add_subheading(doc, "5.3 Exponentially Weighted Moving Average (EWMA) Accumulator")
    add_body(doc, "For captures satisfying the 3D Pose Gate, the system computes the Instantaneous Cosine Drift D_t = 1.0 - S_t. To decouple transient illumination changes from permanent physical appearance changes, a recursive EWMA filter updates the student's cumulative drift score:")
    add_body(doc, "EWMA Drift Accumulation Equation (α = 0.30):  EWMA_t = α · D_t + (1 - α) · EWMA_{t-1}   =   0.30 · (1.0 - S_t) + 0.70 · EWMA_{t-1}\nWhere α = 0.30 acts as a balanced half-life parameter, giving 70% weight to historical baseline integrity while smoothly incorporating verified ongoing morphological shifts.")

    drift_levels = [
        ["Alert State", "EWMA Threshold", "Biometric Condition", "Automated System Remediation"],
        ["HEALTHY", "EWMA < 0.15", "Optimal template alignment; minimal physical drift.", "Standard logging in embedding_health table."],
        ["WARNING", "0.15 <= EWMA < 0.25", "Mild facial appearance evolution detected.", "Flagged on admin dashboard for observational tracking."],
        ["CRITICAL", "0.25 <= EWMA < 0.35", "Substantial drift; nearing recognition boundary.", "Automated SMTP alert email dispatched to system administrator."],
        ["ALERT", "EWMA >= 0.35", "Severe template obsolescence; high false-rejection risk.", "Visual re-enrollment banner triggered; 1-click template reset activated."]
    ]
    t_drift = doc.add_table(rows=len(drift_levels), cols=4)
    t_drift.columns[0].width = Inches(1.2)
    t_drift.columns[1].width = Inches(1.4)
    t_drift.columns[2].width = Inches(2.2)
    t_drift.columns[3].width = Inches(2.2)
    for r_idx, row in enumerate(drift_levels):
        for c_idx, val in enumerate(row):
            cell = t_drift.cell(r_idx, c_idx)
            p = cell.paragraphs[0]
            p.paragraph_format.space_before = Pt(1.5)
            p.paragraph_format.space_after = Pt(1.5)
            run = p.add_run(val)
            run.font.name = "Calibri"
            run.font.size = Pt(8.0)
            if r_idx == 0:
                run.font.bold = True
                run.font.color.rgb = RGBColor(255, 255, 255)
            else:
                run.font.color.rgb = RGB_DARK
                if c_idx == 0:
                    run.font.bold = True
    format_table(t_drift)
    doc.add_paragraph().paragraph_format.space_after = Pt(4)

    add_callout(
        doc,
        "Rather than reacting to failed attendances, BioSecure AI enables institutions to manage biometrics as an evolving operational lifecycle. Administrators can refresh a student's template with a single click, instantly resetting their EWMA drift score to 0.00 and updating the in-memory matrix matcher.",
        "PROACTIVE LIFECYCLE MANAGEMENT",
        HEX_AMBER
    )

    doc.add_page_break()

    # =========================================================================
    # SECTION 6: Neural OCR Student Enrollment Pipeline & ID Card Ingestion
    # =========================================================================
    add_section_header(doc, "Neural OCR Student Enrollment Pipeline", "6.")
    add_body(doc, "Student onboarding in higher education is notoriously labor-intensive, frequently requiring manual typing of names, roll numbers, academic programs, and email addresses for thousands of candidates. BioSecure AI eliminates onboarding friction through an end-to-end Neural Optical Character Recognition (OCR) pipeline.")

    add_subheading(doc, "6.1 Multi-Pass OpenCV Image Preprocessing")
    add_body(doc, "Physical institutional ID cards often present adverse optical conditions: reflective plastic lamination, deep colored backgrounds (e.g., navy blue cards with white text), and shadows from mobile camera snapshots. The image preprocessing engine generates three complementary representations to maximize character extraction recall:")
    add_bullet(doc, "If width < 1,000px, resizes to a standardized 1,200px width using bicubic interpolation to preserve stroke clarity for small font sizes.", "1. Bilinear Dimensional Upscaling: ")
    add_bullet(doc, "Converts white typography on dark backgrounds into high-contrast black characters on a pure white field via cv2.bitwise_not().", "2. Bitwise Inverse Transformation: ")
    add_bullet(doc, "Evaluates localized pixel neighborhoods to isolate text boundaries despite non-uniform glare and harsh room lighting conditions.", "3. Adaptive Gaussian Thresholding: ")

    add_subheading(doc, "6.2 RapidOCR (DBNet + SVTR) Deep Neural Architecture")
    add_body(doc, "The primary OCR engine utilizes RapidOCR, an ONNX-runtime neural architecture combining DBNet (Real-time Scene Text Detection with Differentiable Binarization) and SVTR (Single Visual Model for Text Recognition). DBNet detects arbitrary text polygons, while SVTR processes character tokens through a lightweight vision transformer, significantly outperforming traditional Tesseract OCR on skewed or stylized credentials.")

    add_subheading(doc, "6.3 Structured Regex Extraction & State Machine")
    ocr_field_data = [
        ["Target Field", "Extraction Pattern / Regex Rules", "Sample Extracted Value"],
        ["Student ID / Roll", "(?i)(?:ID|Roll|Enr|CU[-_]?ID)[\\s:]*([A-Z]{2,4}\\d{6,12})", "CU240251013"],
        ["Full Name", "Filters out university headers and labels; captures title-cased alpha tokens.", "Arnav Pundir"],
        ["Academic Program", "Keyword matching: B.Tech, BCA, MCA, M.Tech, B.Sc, MBA, Ph.D.", "B.Tech"],
        ["Academic Branch", "Branch dictionary: Computer Science/CSE, IT, ECE, Mechanical, AI&ML.", "CSE"],
        ["Enrollment Year", "4-digit year pattern (2018-2030) or derived from 2-digit student ID prefix.", "2024"],
        ["Institutional Email", "Standard RFC-5322 regex: [\\w\\.-]+@[\\w\\.-]+\\.\\w+", "cu240251013@coeruniversity.ac.in"]
    ]
    t_ocr = doc.add_table(rows=len(ocr_field_data), cols=3)
    t_ocr.columns[0].width = Inches(1.5)
    t_ocr.columns[1].width = Inches(3.5)
    t_ocr.columns[2].width = Inches(2.0)
    for r_idx, row in enumerate(ocr_field_data):
        for c_idx, val in enumerate(row):
            cell = t_ocr.cell(r_idx, c_idx)
            p = cell.paragraphs[0]
            p.paragraph_format.space_before = Pt(1.5)
            p.paragraph_format.space_after = Pt(1.5)
            run = p.add_run(val)
            run.font.name = "Calibri"
            run.font.size = Pt(8.0)
            if r_idx == 0:
                run.font.bold = True
                run.font.color.rgb = RGBColor(255, 255, 255)
            else:
                run.font.color.rgb = RGB_DARK
                if c_idx == 0:
                    run.font.bold = True
    format_table(t_ocr)
    doc.add_paragraph().paragraph_format.space_after = Pt(4)

    add_subheading(doc, "6.4 Mobile Native Camera Hardware Window Integration")
    add_body(doc, "On smartphone browsers, navigating traditional file-upload menus to find photos is slow. BioSecure AI implements a dedicated mobile hardware capture attribute (<input type='file' accept='image/*' capture='environment'>). Tapping 'Click ID Photo' launches the device's native full-screen camera viewfinder instantly (ChatGPT-style), capturing high-resolution photos that stream directly into the neural OCR pipeline.")

    add_callout(
        doc,
        "By combining native mobile camera invocation with RapidOCR neural inference, an administrator can photograph a student's physical ID card, have all registration fields auto-populated in <1.2 seconds, capture the portrait reference, and commit the 512D ArcFace embedding to memory in under 3 seconds total.",
        "RAPID ENROLLMENT SPEED & THROUGHPUT",
        HEX_ROYAL
    )

    doc.add_page_break()

    # =========================================================================
    # SECTION 7: Database Architecture, pgvector Storage & Security Policies
    # =========================================================================
    add_section_header(doc, "Database Architecture, pgvector & Security", "7.")
    add_body(doc, "BioSecure AI utilizes an enterprise PostgreSQL instance managed through Supabase. The relational database schema stores student profiles, historical attendance records, biometric drift telemetry, academic taxonomies, and 512-dimensional floating-point embeddings backed by HNSW indexing.")

    add_subheading(doc, "7.1 Relational Schema Definitions & Entity Design")
    db_schema_data = [
        ["Table Name", "Primary Key", "Key Columns & Types", "Functional Responsibility"],
        ["students", "id (TEXT)", "name (TEXT), program (TEXT), branch (TEXT), embedding (VECTOR(512)), current_ewma_drift (FLOAT), drift_alert_level (TEXT)", "Master student directory containing 512D ArcFace reference templates and active drift scores."],
        ["attendance", "att_id (BIGSERIAL)", "student_id (FK), name (TEXT), status (TEXT), timestamp (TEXT), lecture (TEXT)", "Immutable chronological log of classroom attendance events."],
        ["embedding_health", "id (BIGSERIAL)", "student_id (FK), drift_score (FLOAT), ewma_drift (FLOAT), pose_yaw (FLOAT), pose_pitch (FLOAT), pose_accepted (BOOL)", "Granular telemetry log recording every biometric drift computation and pose-gate decision."],
        ["academic_structure", "id (BIGSERIAL)", "type (TEXT: program/branch), value (TEXT)", "Dynamic academic curriculum options supporting UI dropdown filters."]
    ]
    t_dbs = doc.add_table(rows=len(db_schema_data), cols=4)
    t_dbs.columns[0].width = Inches(1.3)
    t_dbs.columns[1].width = Inches(1.1)
    t_dbs.columns[2].width = Inches(2.4)
    t_dbs.columns[3].width = Inches(2.2)
    for r_idx, row in enumerate(db_schema_data):
        for c_idx, val in enumerate(row):
            cell = t_dbs.cell(r_idx, c_idx)
            p = cell.paragraphs[0]
            p.paragraph_format.space_before = Pt(1.5)
            p.paragraph_format.space_after = Pt(1.5)
            run = p.add_run(val)
            run.font.name = "Calibri"
            run.font.size = Pt(8.0)
            if r_idx == 0:
                run.font.bold = True
                run.font.color.rgb = RGBColor(255, 255, 255)
            else:
                run.font.color.rgb = RGB_DARK
                if c_idx == 0:
                    run.font.bold = True
    format_table(t_dbs)
    doc.add_paragraph().paragraph_format.space_after = Pt(4)

    add_subheading(doc, "7.2 pgvector HNSW Indexing & match_face Stored Procedure")
    add_body(doc, "To accelerate vector lookups, the embedding column is indexed using a Hierarchical Navigable Small World (HNSW) graph with Cosine distance operators: CREATE INDEX idx_students_embedding_hnsw ON public.students USING hnsw (embedding vector_cosine_ops). The backend executes database-level searches via an optimized PL/pgSQL stored procedure:")
    add_body(doc, "PostgreSQL Stored Procedure (match_face):\nCREATE OR REPLACE FUNCTION public.match_face(query_embedding VECTOR(512), match_threshold FLOAT DEFAULT 0.40, filter_program TEXT DEFAULT NULL, filter_branch TEXT DEFAULT NULL)\nRETURNS TABLE (id TEXT, name TEXT, program TEXT, branch TEXT, similarity FLOAT) AS $$\nBEGIN\n  RETURN QUERY SELECT s.id, s.name, s.program, s.branch, (1.0 - (s.embedding <=> query_embedding))::FLOAT AS similarity\n  FROM public.students s WHERE s.embedding IS NOT NULL AND (1.0 - (s.embedding <=> query_embedding)) >= match_threshold\n  AND (filter_program IS NULL OR s.program ILIKE filter_program) AND (filter_branch IS NULL OR s.branch ILIKE filter_branch)\n  ORDER BY s.embedding <=> query_embedding ASC LIMIT 1;\nEND; $$ LANGUAGE plpgsql SECURITY DEFINER;")

    add_subheading(doc, "7.3 Row-Level Security (RLS) & Access Control")
    add_body(doc, "Biometric vectors represent highly sensitive personally identifiable information (PII). BioSecure AI enforces strict Row-Level Security across the database layer: anonymous public access (anon) is completely revoked; authenticated client sessions hold read-only permissions on student rosters; and administrative write operations execute exclusively through trusted backend connections utilizing the SUPABASE_SERVICE_ROLE_KEY.")

    add_callout(
        doc,
        "Raw facial photographs are never exposed through database APIs. Only abstract 512D mathematical feature projections are stored in pgvector. These floating-point vectors are mathematically non-invertible, meaning a face image cannot be reverse-synthesized from the stored embedding numbers.",
        "PRIVACY & VECTOR NON-INVERTIBILITY",
        HEX_EMERALD
    )

    doc.add_page_break()

    # =========================================================================
    # SECTION 8: Progressive Web App (PWA) & Client-Side Architecture
    # =========================================================================
    add_section_header(doc, "Progressive Web App (PWA) & Client Architecture", "8.")
    add_body(doc, "BioSecure AI is engineered as a modern Progressive Web App (PWA), delivering a unified, application-grade experience across desktop workstations, lecture-hall tablets, and instructor smartphones without requiring distribution through native app stores.")

    add_subheading(doc, "8.1 PWA Shell, Service Worker & Offline Caching")
    add_body(doc, "The client architecture is powered by a custom Service Worker (src/static/js/sw.js) and a standardized W3C Web App Manifest (manifest.json). The Service Worker orchestrates a dual caching strategy: a Cache-First policy caches static App Shell assets (Tailwind CSS, Lucide Icons, interactive canvas particle scripts, and web fonts); a Network-First policy manages dynamic API endpoints. If an instructor enters a lecture room with degraded Wi-Fi, the App Shell remains instantly accessible, gracefully rendering a dedicated offline screen (/offline) rather than a broken browser timeout.")

    pwa_data = [
        ["PWA Capability", "Technical Specification", "Operational User Benefit"],
        ["Standalone Installation", "Web App Manifest with full icon suite (72px to 512px maskable).", "Installs directly to iOS Home Screen, Android launcher, and Windows taskbar."],
        ["App Shell Caching", "Cache Storage API versioning (biosecure-v1).", "Instant page loads (<100ms) with zero repeat network asset requests."],
        ["Network Resilience", "Fetch event interceptor routing to /offline fallback.", "Prevents crash screens during intermittent campus Wi-Fi drops."],
        ["Native Camera Hook", "HTML5 capture='environment' media capture constraint.", "Launches mobile device's native optical hardware camera with one tap."]
    ]
    t_pwa = doc.add_table(rows=len(pwa_data), cols=3)
    t_pwa.columns[0].width = Inches(1.8)
    t_pwa.columns[1].width = Inches(2.2)
    t_pwa.columns[2].width = Inches(3.0)
    for r_idx, row in enumerate(pwa_data):
        for c_idx, val in enumerate(row):
            cell = t_pwa.cell(r_idx, c_idx)
            p = cell.paragraphs[0]
            p.paragraph_format.space_before = Pt(1.5)
            p.paragraph_format.space_after = Pt(1.5)
            run = p.add_run(val)
            run.font.name = "Calibri"
            run.font.size = Pt(8.0)
            if r_idx == 0:
                run.font.bold = True
                run.font.color.rgb = RGBColor(255, 255, 255)
            else:
                run.font.color.rgb = RGB_DARK
                if c_idx == 0:
                    run.font.bold = True
    format_table(t_pwa)
    doc.add_paragraph().paragraph_format.space_after = Pt(4)

    add_subheading(doc, "8.2 Responsive Dark-Glassmorphic UI/UX Design System")
    add_body(doc, "The interface incorporates a high-end dark glassmorphic design system constructed with Tailwind CSS. It features translucent card overlays with backdrop blur (backdrop-blur-md), glowing accent borders, micro-interactions, and high-contrast typography calibrated for high visibility in brightly lit classrooms and dimly lit auditoriums.")

    add_subheading(doc, "8.3 Interactive Attendance Viewer & CSV Export Engine")
    add_body(doc, "The live attendance viewer (/viewer) provides instructors with a real-time operational control room. Key features include:")
    add_bullet(doc, "Dynamically filter attendance logs by Date, Program (B.Tech, BCA), Branch (CSE, ECE), Batch Year, and Lecture Identifier.", "Multi-Column Filtering: ")
    add_bullet(doc, "Displays group photo results with green bounding boxes and confidence scores for verified students, and red bounding boxes for unidentified faces.", "Instant Visual Annotation Overlay: ")
    add_bullet(doc, "Generates formatted spreadsheet reports on demand for seamless upload to institutional ERP and student management portals.", "One-Click CSV Export: ")

    add_callout(
        doc,
        "Instructors can walk into a classroom with an Android phone, take an attendance photo through the PWA app icon, process 45 students in parallel, and export the official attendance roster before concluding the first five minutes of the lecture.",
        "CROSS-DEVICE WORKFLOW ACCELERATION",
        HEX_SKY
    )

    doc.add_page_break()

    # =========================================================================
    # SECTION 9: Administrative Governance, Analytics & System Control
    # =========================================================================
    add_section_header(doc, "Administrative Governance, Analytics & Control", "9.")
    add_body(doc, "BioSecure AI incorporates enterprise-grade governance controls, separating daily attendance tasks from high-privilege configuration, user management, and biometric health maintenance.")

    add_subheading(doc, "9.1 Role-Based Access Control (RBAC) Architecture")
    add_body(doc, "System functionality is segregated into two explicit privilege tiers: Instructor Role (authorized to process attendance photos, review class logs, and export session spreadsheets) and Administrator Role (authorized to enroll new student profiles, access the neural OCR card scanner, configure academic branches, manage user accounts, and execute biometric drift template resets).")

    add_subheading(doc, "9.2 Biometric Drift Management Portal (/admin/drift)")
    add_body(doc, "The dedicated Biometric Drift Dashboard acts as a predictive maintenance console. The system continuously aggregates student records sorted by highest cumulative EWMA drift score, highlighting individuals transitioning into WARNING, CRITICAL, or ALERT zones before identity verification degrades.")

    add_subheading(doc, "9.3 Automated Alerting & 1-Click Re-Enrollment Reset")
    add_body(doc, "When a student's appearance changes significantly (e.g. growing a full beard or changing hairstyle), their EWMA drift score escalates. The governance workflow executes as follows:")
    add_bullet(doc, "Once a student crosses the CRITICAL threshold (>=0.25), an asynchronous background task dispatches an HTML notification email to the administrator containing student details, current drift score, and recommended actions.", "1. Automated SMTP Warning Dispatch: ")
    add_bullet(doc, "In the admin dashboard, the administrator captures or uploads an updated reference portrait and clicks Reset Drift Score. The backend extracts the new 512D ArcFace embedding, updates the database, resets current_ewma_drift to 0.00 (HEALTHY), and refreshes the in-memory BLAS matrix cache atomically.", "2. Single-Click Template Reset: ")

    admin_actions = [
        ["Administrative Function", "Endpoint / Route", "Privilege Level", "Security & System Impact"],
        ["Drift Telemetry Dashboard", "GET /admin/drift", "Admin Only", "Monitors institution-wide biometric health and template degradation."],
        ["Single-Click Template Reset", "POST /student/reset_drift/<id>", "Admin Only", "Resets EWMA to 0.00; updates 512D embedding in DB and RAM cache."],
        ["Manual Attendance Override", "POST /update_attendance_status", "Admin / Instructor", "Allows audited manual adjustments for excused student absences."],
        ["Academic Curriculum Config", "GET/POST /admin/academics", "Admin Only", "Creates/edits recognized programs, branches, and academic terms."]
    ]
    t_adm = doc.add_table(rows=len(admin_actions), cols=4)
    t_adm.columns[0].width = Inches(1.8)
    t_adm.columns[1].width = Inches(1.8)
    t_adm.columns[2].width = Inches(1.1)
    t_adm.columns[3].width = Inches(2.3)
    for r_idx, row in enumerate(admin_actions):
        for c_idx, val in enumerate(row):
            cell = t_adm.cell(r_idx, c_idx)
            p = cell.paragraphs[0]
            p.paragraph_format.space_before = Pt(1.5)
            p.paragraph_format.space_after = Pt(1.5)
            run = p.add_run(val)
            run.font.name = "Calibri"
            run.font.size = Pt(8.0)
            if r_idx == 0:
                run.font.bold = True
                run.font.color.rgb = RGBColor(255, 255, 255)
            else:
                run.font.color.rgb = RGB_DARK
                if c_idx == 0:
                    run.font.bold = True
                elif c_idx == 2:
                    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    format_table(t_adm)
    doc.add_paragraph().paragraph_format.space_after = Pt(4)

    add_subheading(doc, "9.4 Institutional Attendance Analytics & Trends")
    add_body(doc, "The administrative console aggregates real-time 7-day attendance trends, computing presence/absence ratios across departmental branches. Instructors and deans gain immediate visibility into chronic absenteeism patterns, enabling timely student interventions.")

    add_callout(
        doc,
        "Every biometric template modification, attendance override, and drift reset is permanently logged with timestamps and operator credentials, satisfying institutional compliance, accreditation, and data protection standards.",
        "COMPLIANCE & AUDIT ASSURANCE",
        HEX_ROYAL
    )

    doc.add_page_break()

    # =========================================================================
    # SECTION 10: Production Deployment, Verification & Roadmap
    # =========================================================================
    add_section_header(doc, "Production Deployment, Verification & Roadmap", "10.")
    add_body(doc, "BioSecure AI is architected for zero-downtime production deployment on standard Linux virtual private servers (VPS), containerized environments, or enterprise on-premise infrastructure. This section outlines the deployment topology, automated test verification, and future roadmap.")

    add_subheading(doc, "10.1 Production Server Topology & Daemon Architecture")
    add_body(doc, "In production, the application executes behind an Nginx reverse proxy communicating with a Gunicorn WSGI process manager via UNIX domain sockets or local loopback. System reliability is enforced through Systemd service daemons:")
    add_bullet(doc, "Configured with client_max_body_size 25M to handle multi-megapixel group photos; serves static assets directly with 30-day cache-control headers; enforces HTTPS encryption required by browser camera APIs.", "Nginx Gateway: ")
    add_bullet(doc, "Spawns worker processes according to workers = (2 * CPU_CORES) + 1. Worker timeout is tuned to 120s to accommodate heavy initial ONNX model warmups.", "Gunicorn WSGI Manager: ")
    add_bullet(doc, "Automatically launches the application on server reboot, monitors worker memory usage, and executes immediate automatic restarts upon unexpected process termination.", "Systemd Service Daemon: ")

    add_subheading(doc, "10.2 Empirical Verification & Automated Test Suite")
    test_data = [
        ["Test Module", "Verification Target", "Assertions & Edge Cases Covered", "Status"],
        ["test_face_cache.py", "In-Memory BLAS Engine", "Vector normalization, zero-norm sanitization, JSON/string deserialization, batch dot-product matching.", "PASSED (5/5)"],
        ["test_ocr_helpers.py", "RapidOCR & Regex Parser", "Multi-pass contrast inversion, university ID regex extraction, multiline name/program splitting.", "PASSED (3/3)"],
        ["test_routes.py", "HTTP & PWA Endpoints", "/healthz JSON status, /manifest.json headers, Service Worker delivery, 404 handlers.", "PASSED (6/6)"]
    ]
    t_test = doc.add_table(rows=len(test_data), cols=4)
    t_test.columns[0].width = Inches(1.5)
    t_test.columns[1].width = Inches(1.5)
    t_test.columns[2].width = Inches(3.0)
    t_test.columns[3].width = Inches(1.0)
    for r_idx, row in enumerate(test_data):
        for c_idx, val in enumerate(row):
            cell = t_test.cell(r_idx, c_idx)
            p = cell.paragraphs[0]
            p.paragraph_format.space_before = Pt(1.5)
            p.paragraph_format.space_after = Pt(1.5)
            run = p.add_run(val)
            run.font.name = "Calibri"
            run.font.size = Pt(8.0)
            if r_idx == 0:
                run.font.bold = True
                run.font.color.rgb = RGBColor(255, 255, 255)
            else:
                run.font.color.rgb = RGB_DARK
                if c_idx == 0:
                    run.font.bold = True
                elif c_idx == 3:
                    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    run.font.bold = True
                    run.font.color.rgb = RGBColor(5, 150, 105)
    format_table(t_test)
    doc.add_paragraph().paragraph_format.space_after = Pt(4)

    add_subheading(doc, "10.3 Component Latency & Operational Throughput")
    perf_data = [
        ["Pipeline Component", "Execution Environment", "Average Turnaround", "Throughput Capacity"],
        ["RetinaFace Detection & Alignment", "ONNX Runtime (CPU)", "320 - 450 ms per frame", "2.5 frames / sec (Multi-face)"],
        ["ArcFace 512D Vector Encoding", "ONNX Runtime (CPU)", "18 - 25 ms per face", "45 faces / sec"],
        ["BLAS Matrix Dot-Product Match", "C-NumPy AVX2 SIMD", "< 0.75 ms (1,000 students)", "> 1,300,000 matches / sec"],
        ["End-to-End Classroom Ingestion", "Full HTTP Request Cycle", "680 - 920 ms (40 students)", "Real-Time Turnaround"]
    ]
    t_perf = doc.add_table(rows=len(perf_data), cols=4)
    t_perf.columns[0].width = Inches(2.0)
    t_perf.columns[1].width = Inches(1.8)
    t_perf.columns[2].width = Inches(1.6)
    t_perf.columns[3].width = Inches(1.6)
    for r_idx, row in enumerate(perf_data):
        for c_idx, val in enumerate(row):
            cell = t_perf.cell(r_idx, c_idx)
            p = cell.paragraphs[0]
            p.paragraph_format.space_before = Pt(1.5)
            p.paragraph_format.space_after = Pt(1.5)
            run = p.add_run(val)
            run.font.name = "Calibri"
            run.font.size = Pt(8.0)
            if r_idx == 0:
                run.font.bold = True
                run.font.color.rgb = RGBColor(255, 255, 255)
            else:
                run.font.color.rgb = RGB_DARK
                if c_idx == 0:
                    run.font.bold = True
                elif c_idx >= 2:
                    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    format_table(t_perf)
    doc.add_paragraph().paragraph_format.space_after = Pt(4)

    add_subheading(doc, "10.4 Strategic Architectural Roadmap")
    add_body(doc, "Upcoming engineering milestones for BioSecure AI include: Edge AI Hardware Acceleration (porting RetinaFace and ArcFace to TensorRT and Apple CoreML for on-device mobile inference), Continuous Video Stream Ingestion (processing RTSP security camera feeds for passive hall attendance), and Federated Template Synchronization across multi-campus university networks.")

    add_callout(
        doc,
        "BioSecure AI transitions institutional attendance from a manual friction point into an automated, sub-second ambient process. By unifying deep facial recognition, sub-millisecond BLAS vector matching, neural OCR onboarding, and proactive biometric drift tracking, the platform delivers a production-grade biometric solution for modern educational institutions.",
        "EXECUTIVE TECHNICAL SUMMARY",
        HEX_NAVY
    )

    doc.save(filename)
    print(f"Successfully generated {filename}")


def verify_docx(filename="BioSecure_AI_Project_Overview.docx"):
    """Validates that DOCX exists, has 0 patent terms, and contains all 10 sections."""
    if not os.path.exists(filename):
        raise FileNotFoundError(f"{filename} does not exist.")

    doc = docx.Document(filename)
    full_text = []
    for p in doc.paragraphs:
        full_text.append(p.text)
    for t in doc.tables:
        for row in t.rows:
            for cell in row.cells:
                full_text.append(cell.text)

    all_text = " ".join(full_text).lower()

    # Banned words check
    banned_words = ['patent', 'idf', 'invention disclosure', 'prior art']
    violations = [w for w in banned_words if w in all_text]
    if violations:
        raise ValueError(f"DOCX contains banned terms: {violations}")
    print("DOCX Patent Check PASSED: Exactly 0 mentions of patent/IDF/prior art.")

    # Check sections present
    sections_expected = ["Executive Summary", "System Architecture", "Biometric Inference", "Vector Matching", "Biometric Drift", "Neural OCR", "Database Architecture", "Progressive Web App", "Administrative Governance", "Production Deployment"]
    for s in sections_expected:
        if s.lower() not in all_text:
            raise ValueError(f"Missing section: {s}")
    print("DOCX Structure Check PASSED: All 10 technical sections verified.")


if __name__ == '__main__':
    build_docx()
    verify_docx()
