"""
Script to generate a comprehensive, professional Word (.docx) document
for the Phase 2 Master Implementation Guide.
"""

import os
import sys
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

DOCS_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DOCX = os.path.join(DOCS_DIR, "PHASE_2_MASTER_IMPLEMENTATION_GUIDE.docx")


def set_cell_background(cell, fill_hex):
    tcPr = cell._element.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill_hex}"/>')
    tcPr.append(shd)


def set_cell_margins(cell, top=100, bottom=100, left=150, right=150):
    tcPr = cell._element.get_or_add_tcPr()
    tcMar = parse_xml(
        f'<w:tcMar {nsdecls("w")}>'
        f'<w:top w:w="{top}" w:type="dxa"/>'
        f'<w:bottom w:w="{bottom}" w:type="dxa"/>'
        f'<w:left w:w="{left}" w:type="dxa"/>'
        f'<w:right w:w="{right}" w:type="dxa"/>'
        f'</w:tcMar>'
    )
    tcPr.append(tcMar)


def add_callout(doc, text, alert_type="NOTE"):
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Inches(0.4)
    p.paragraph_format.right_indent = Inches(0.4)
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.space_after = Pt(6)

    run_title = p.add_run(f"[{alert_type}] ")
    run_title.bold = True
    if alert_type in ("IMPORTANT", "CAUTION"):
        run_title.font.color.rgb = RGBColor(185, 28, 28)
    elif alert_type == "TIP":
        run_title.font.color.rgb = RGBColor(16, 149, 193)
    else:
        run_title.font.color.rgb = RGBColor(37, 99, 235)

    run_body = p.add_run(text)
    run_body.font.color.rgb = RGBColor(51, 65, 85)
    run_body.font.size = Pt(10)


def style_table(table, col_widths, headers, data, header_bg="1E3A8A"):
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    # Header Row
    hdr_cells = table.rows[0].cells
    for i, h in enumerate(headers):
        hdr_cells[i].text = h
        set_cell_background(hdr_cells[i], header_bg)
        set_cell_margins(hdr_cells[i], top=120, bottom=120, left=140, right=140)
        p = hdr_cells[i].paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        for r in p.runs:
            r.font.bold = True
            r.font.color.rgb = RGBColor(255, 255, 255)
            r.font.size = Pt(9.5)

    # Data Rows
    for row_idx, row_data in enumerate(data):
        row_cells = table.add_row().cells
        bg_color = "F8FAFC" if row_idx % 2 == 1 else "FFFFFF"
        for col_idx, cell_value in enumerate(row_data):
            row_cells[col_idx].text = str(cell_value)
            set_cell_background(row_cells[col_idx], bg_color)
            set_cell_margins(row_cells[col_idx], top=90, bottom=90, left=140, right=140)
            p = row_cells[col_idx].paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            for r in p.runs:
                r.font.size = Pt(9)
                r.font.color.rgb = RGBColor(51, 65, 85)

    # Widths
    for row in table.rows:
        for i, w in enumerate(col_widths):
            row.cells[i].width = Inches(w)


def build_word_guide():
    doc = Document()

    # Configure Margins
    for section in doc.sections:
        section.top_margin = Inches(0.8)
        section.bottom_margin = Inches(0.8)
        section.left_margin = Inches(0.8)
        section.right_margin = Inches(0.8)

    # Set Base Styles
    style_normal = doc.styles["Normal"]
    style_normal.font.name = "Calibri"
    style_normal.font.size = Pt(11)
    style_normal.font.color.rgb = RGBColor(30, 41, 59)

    # =========================================================================
    # DOCUMENT COVER / TITLE BLOCK
    # =========================================================================
    p_pre = doc.add_paragraph()
    p_pre.paragraph_format.space_before = Pt(12)
    p_pre.paragraph_format.space_after = Pt(2)
    r_sub = p_pre.add_run("AI GYM & FITNESS ASSISTANT — MASTER SPECIFICATION")
    r_sub.font.size = Pt(10.5)
    r_sub.font.bold = True
    r_sub.font.color.rgb = RGBColor(37, 99, 235)

    p_title = doc.add_paragraph()
    p_title.paragraph_format.space_after = Pt(6)
    r_title = p_title.add_run("Phase 2 Master Implementation Guide")
    r_title.font.size = Pt(24)
    r_title.font.bold = True
    r_title.font.color.rgb = RGBColor(15, 23, 42)

    p_tagline = doc.add_paragraph()
    p_tagline.paragraph_format.space_after = Pt(16)
    r_tag = p_tagline.add_run("The Complete Pose-to-Performance System\nComputer Vision • Biomechanical State Machine • Form Analysis • Scoring Engine • APIs • Database • Next.js Frontend")
    r_tag.font.size = Pt(12)
    r_tag.font.color.rgb = RGBColor(100, 116, 139)

    # Metadata Table
    meta_table = doc.add_table(rows=1, cols=4)
    meta_widths = [1.6, 1.8, 1.6, 1.8]
    meta_headers = ["Attribute", "Specification", "Attribute", "Specification"]
    meta_data = [
        ["Project", "AI Gym & Fitness Assistant", "Phase", "Phase 2 (Accepted)"],
        ["Implementation", "Developer 2 (Antigravity)", "Review & Approval", "Developer 1 (ChatGPT)"],
        ["Project Owner", "Anand (Developer 3)", "Status", "100% Verified (82/82 Checks)"],
        ["Backend Stack", "FastAPI + SQLAlchemy + PostgreSQL", "Vision Stack", "OpenCV + MediaPipe Tasks Vision"],
        ["Frontend Stack", "Next.js 16 + React 19 + Tailwind", "Python Runtime", "Python 3.14.2 (64-bit)"],
    ]
    style_table(meta_table, meta_widths, meta_headers, meta_data, header_bg="0F172A")

    doc.add_paragraph().paragraph_format.space_after = Pt(12)

    # =========================================================================
    # CHAPTER 1: EXECUTIVE ARCHITECTURE & PIPELINE
    # =========================================================================
    h1 = doc.add_heading("Chapter 1: Executive Overview & Pipeline Architecture", level=1)
    h1.runs[0].font.color.rgb = RGBColor(30, 58, 138)

    doc.add_paragraph(
        "Phase 2 builds the core intelligence of the AI Gym application. It connects raw optical inputs "
        "(webcam or recorded workout video) through landmark extraction, 2D planar vector kinematics, "
        "anti-cheat finite state machines, real-time coaching heuristics, and 7-factor biomechanical "
        "performance scoring into PostgreSQL database persistence and a modern Next.js 16 frontend."
    )

    doc.add_paragraph("The system functions as a strictly unidirectional, deterministic pipeline:")

    pipe_table = doc.add_table(rows=1, cols=3)
    pipe_widths = [1.8, 2.2, 2.8]
    pipe_headers = ["Pipeline Stage", "Primary Component", "Key Functional Responsibilities"]
    pipe_data = [
        ["1. Optical Capture", "OpenCV VideoCapture / WebRTC", "Acquires 30 FPS RGB video frames from user camera."],
        ["2. Pose Landmark Tasks", "ml/pose/pose_detector.py", "Extracts 33 3D normalized body landmarks with visibility scores."],
        ["3. Visibility Gate", "Landmark Reliability Gate", "Rejects occluded joints (min confidence >= 0.5); blocks hallucinated reps."],
        ["4. Joint Geometry", "ml/pose/angle_calculator.py", "Calculates 2D planar knee angle via vector cosine dot product."],
        ["5. Signal Smoothing", "ml/pose/smoothing.py", "5-frame Simple Moving Average (SMA) removes camera micro-jitter."],
        ["6. State Machine FSM", "ml/pose/squat_state_machine.py", "Enforces UP -> DESCENDING -> BOTTOM -> ASCENDING cycle."],
        ["7. Form Analysis", "ml/pose/form_analyzer.py", "Evaluates depth, torso lean (<45°), knee valgus; emits coaching cues."],
        ["8. Performance Scoring", "ml/pose/performance_analyzer.py", "Computes 7-factor normalized score [0-100] & jerk smoothness."],
        ["9. Backend API & DB", "backend/routers/workouts.py", "Saves workout session and per-rep pose metrics into PostgreSQL."],
        ["10. Web Interface", "frontend/src/app/workout", "Live HUD with reps, joint angle, coaching cues, and post-session modal."],
    ]
    style_table(pipe_table, pipe_widths, pipe_headers, pipe_data)

    doc.add_paragraph().paragraph_format.space_after = Pt(12)

    # =========================================================================
    # CHAPTER 2: DATABASE ARCHITECTURE & LIVE MIGRATION
    # =========================================================================
    h2 = doc.add_heading("Chapter 2: Database Schema & Relational Models", level=1)
    h2.runs[0].font.color.rgb = RGBColor(30, 58, 138)

    doc.add_paragraph(
        "All data models were implemented in SQLAlchemy 2.0 with strict foreign key integrity, "
        "cascading policies, non-negative constraints, and zero large video/binary storage in relational tables."
    )

    models_table = doc.add_table(rows=1, cols=4)
    models_widths = [1.6, 1.8, 1.6, 1.8]
    models_headers = ["Table Name", "Model Class", "Key Foreign Keys", "Integrity & Constraint Rules"]
    models_data = [
        ["exercises", "Exercise", "None (Primary Catalogue)", "Unique name constraint. Seeded with Squat, Push-up, Bicep Curl."],
        ["workout_sessions", "WorkoutSession", "user_id -> users.id", "ON DELETE CASCADE from User. Stores performance_score and calories."],
        ["workout_exercises", "WorkoutExercise", "workout_session_id -> sessions\nexercise_id -> exercises", "ON DELETE RESTRICT on exercises (prevents catalogue deletion history loss). Check constraints: sets >= 0, reps >= 0."],
        ["pose_metrics", "PoseMetric", "workout_session_id -> sessions", "ON DELETE CASCADE. Stores per-rep angles, violations, duration, and metrics_json."],
    ]
    style_table(models_table, models_widths, models_headers, models_data)

    add_callout(
        doc,
        "Zero Video in Relational Tables: AI Gym stores purely scalar metrics (angles, durations, scores) and compact JSON telemetry. No raw video files or base64 frame dumps are stored in PostgreSQL.",
        "IMPORTANT"
    )

    doc.add_paragraph().paragraph_format.space_after = Pt(12)

    # =========================================================================
    # CHAPTER 3: VISION PIPELINE & MEDIAPIPE TASKS
    # =========================================================================
    h3 = doc.add_heading("Chapter 3: OpenCV + MediaPipe Tasks Vision Pipeline", level=1)
    h3.runs[0].font.color.rgb = RGBColor(30, 58, 138)

    doc.add_paragraph(
        "Modern Python 3.14+ distributions do not support legacy `mp.solutions.pose`. "
        "AI Gym uses the Google MediaPipe Tasks Vision API with `pose_landmarker_heavy.task`:"
    )

    p_list = doc.add_paragraph()
    p_list.paragraph_format.left_indent = Inches(0.25)
    p_list.add_run("• Landmark Resolution: 33 anatomical landmarks extracted per frame in 3D normalized space.\n"
                   "• Confidence Tracking: Each landmark provides both visibility and presence confidence scores [0.0, 1.0].\n"
                   "• Processing Efficiency: Measured CPU inference latency is ~26.3 ms, comfortably exceeding 30 FPS real-time requirements.\n"
                   "• Graceful Fallback: The pipeline automatically detects camera availability; if access is restricted or headless, it falls back to deterministic testing fixtures without crashing.")

    doc.add_paragraph().paragraph_format.space_after = Pt(12)

    # =========================================================================
    # CHAPTER 4: 2D ANGLE GEOMETRY & SQUAT FSM
    # =========================================================================
    h4 = doc.add_heading("Chapter 4: 2D Joint Angles & Squat State Machine", level=1)
    h4.runs[0].font.color.rgb = RGBColor(30, 58, 138)

    doc.add_paragraph(
        "Knee flexion is computed at vertex B (Knee) between vector BA (Hip) and vector BC (Ankle):"
    )

    add_callout(
        doc,
        "Mathematical Formulation:\n"
        "1. v1 = (x_hip - x_knee, y_hip - y_knee),  v2 = (x_ankle - x_knee, y_ankle - y_knee)\n"
        "2. cos(θ) = (v1 · v2) / (||v1|| * ||v2||)\n"
        "3. θ = arccos(clip(cos(θ), -1.0, 1.0)) * (180 / π)\n"
        "Calculated using 2D pixel coordinates to preserve true optical aspect ratio without monocular z-jitter.",
        "TIP"
    )

    doc.add_paragraph("The Squat Finite State Machine (FSM) operates across 4 deterministic phases:")

    fsm_table = doc.add_table(rows=1, cols=3)
    fsm_widths = [1.5, 2.0, 3.3]
    fsm_headers = ["FSM State", "Transition Condition", "Biomechanical Meaning & Anti-Cheat Behavior"]
    fsm_data = [
        ["UP", "Initial or θ >= 160.0°", "Athlete standing tall with locked hips/knees."],
        ["DESCENDING", "θ < 155.0° (160° - 5° hysteresis)", "Athlete actively flexing knees downward."],
        ["BOTTOM", "θ <= 100.0° (depth_threshold)", "Valid squat inflection zone reached. Sets _hit_bottom = True."],
        ["ASCENDING", "θ > 105.0° (100° + 5° hysteresis)", "Athlete driving upward out of the squat hole."],
        ["UP (Lockout)", "θ >= 160.0°", "Repetition completed! If _hit_bottom was True, Reps += 1."],
    ]
    style_table(fsm_table, fsm_widths, fsm_headers, fsm_data)

    add_callout(
        doc,
        "Shallow/Half Squat Safeguard: If an athlete descends only to 105° (failing to hit <= 100°) and returns to standing, the FSM transitions directly from DESCENDING back to UP with _hit_bottom = False. ZERO reps are counted, and the system alerts: 'Squat not deep enough. Rep uncounted.'",
        "IMPORTANT"
    )

    doc.add_paragraph().paragraph_format.space_after = Pt(12)

    # =========================================================================
    # CHAPTER 5: SQUAT FORM ANALYSIS & COACHING RULES
    # =========================================================================
    h5 = doc.add_heading("Chapter 5: Squat Form Analysis & Real-Time Feedback", level=1)
    h5.runs[0].font.color.rgb = RGBColor(30, 58, 138)

    doc.add_paragraph(
        "Implemented in `ml/pose/form_analyzer.py`. Rule-based biomechanical analysis evaluates posture "
        "continuously and generates actionable, non-diagnostic coaching cues:"
    )

    form_table = doc.add_table(rows=1, cols=4)
    form_widths = [1.6, 1.8, 1.6, 1.8]
    form_headers = ["Evaluation Metric", "Threshold Rule", "Violation Code", "Actionable User Feedback"]
    form_data = [
        ["Squat Depth", "θ_knee <= 100.0° at bottom", "INSUFFICIENT_DEPTH", "Go slightly deeper."],
        ["Torso Forward Lean", "θ_torso <= 45.0° from vertical", "EXCESSIVE_TORSO_LEAN", "Keep your chest more upright."],
        ["Knee Alignment", "Lateral deviation <= 0.35", "KNEE_ALIGNMENT_ISSUE", "Keep your knees aligned with your feet."],
        ["Landmark Gate", "min(visibility, presence) >= 0.5", "None (Gated)", "Landmarks occluded or out of frame."],
    ]
    style_table(form_table, form_widths, form_headers, form_data)

    doc.add_paragraph().paragraph_format.space_after = Pt(12)

    # =========================================================================
    # CHAPTER 6: 7-FACTOR PERFORMANCE SCORING ENGINE
    # =========================================================================
    h6 = doc.add_heading("Chapter 6: Deterministic 7-Factor Performance Scoring", level=1)
    h6.runs[0].font.color.rgb = RGBColor(30, 58, 138)

    doc.add_paragraph(
        "Phase 2.5 implements a transparent, deterministic scoring engine (Version 1.0) "
        "normalized to [0.0, 100.0] without black-box ML or LLM hallucinations:"
    )

    add_callout(
        doc,
        "Master Performance Score Equation:\n"
        "Score = 0.25*S_form + 0.20*S_comp + 0.15*S_stability + 0.15*S_ROM + 0.10*S_tempo + 0.10*S_smooth + 0.05*S_sym\n"
        "Weights sum exactly to 1.0. All component scores are bounded within [0.0, 100.0].",
        "TIP"
    )

    score_table = doc.add_table(rows=1, cols=4)
    score_widths = [1.6, 1.5, 1.2, 2.5]
    score_headers = ["Factor Name", "Weight", "Range", "Mathematical Formulation / Logic"]
    score_data = [
        ["Form Accuracy (S_form)", "0.25 (25%)", "[0, 100]", "max(0, 100 - (sum_violations / reps) * 25)"],
        ["Completion Quality (S_comp)", "0.20 (20%)", "[0, 100]", "(full_reps / total_reps) * 100  (Penalizes shallow reps)"],
        ["Joint Stability (S_stability)", "0.15 (15%)", "[0, 100]", "max(0, 100 - std_dev_knee_deviation * 200)"],
        ["ROM Consistency (S_ROM)", "0.15 (15%)", "[0, 100]", "max(0, 100 - |mean_depth - 90| * 2 - std_dev_depth * 3)"],
        ["Tempo & Pacing (S_tempo)", "0.10 (10%)", "[0, 100]", "max(0, 100 - |mean_duration - 3.0| * 20 - std_dev_dur * 20)"],
        ["Smoothness (S_smooth)", "0.10 (10%)", "[0, 100]", "max(0, 100 - (mean_jerk / 1500) * 100)"],
        ["Symmetry (S_sym)", "0.05 (5%)", "[0, 100]", "max(0, 100 - mean_bilateral_delta * 4.0) (Default 90 if single-side)"],
    ]
    style_table(score_table, score_widths, score_headers, score_data)

    doc.add_paragraph().paragraph_format.space_after = Pt(12)

    # =========================================================================
    # CHAPTER 7: BACKEND APIS & SECURITY ARCHITECTURE
    # =========================================================================
    h7 = doc.add_heading("Chapter 7: Backend API Endpoints & Security", level=1)
    h7.runs[0].font.color.rgb = RGBColor(30, 58, 138)

    doc.add_paragraph("Implemented in `backend/routers/workouts.py` with strict JWT Bearer authentication:")

    api_table = doc.add_table(rows=1, cols=4)
    api_widths = [1.2, 2.2, 1.4, 2.0]
    api_headers = ["Method", "Endpoint Route", "Auth Required", "Description & Response"]
    api_data = [
        ["GET", "/exercises", "No (Public)", "Returns available catalogue (Squat, Push-up, Curl)."],
        ["POST", "/workouts/start", "Yes (JWT)", "Creates active session record with session_id."],
        ["POST", "/workouts/{id}/complete", "Yes (JWT)", "Finalizes session with score, duration, reps, and pose_metrics."],
        ["GET", "/workouts/history", "Yes (JWT)", "Returns chronological list of user's past workouts."],
        ["GET", "/workouts/{id}", "Yes (JWT)", "Detailed breakdown of session and per-rep pose metrics."],
        ["GET", "/performance/summary", "Yes (JWT)", "Longitudinal average score, trend (IMPROVING/STABLE), and cues."],
    ]
    style_table(api_table, api_widths, api_headers, api_data)

    add_callout(
        doc,
        "Cross-User Authorization Isolation: All workout queries filter by WorkoutSession.user_id == current_user.id. If User A attempts to view or complete User B's workout session, the server strictly returns 403 Forbidden. User B's workout data never leaks into User A's history or performance summary.",
        "IMPORTANT"
    )

    doc.add_paragraph().paragraph_format.space_after = Pt(12)

    # =========================================================================
    # CHAPTER 8: FRONTEND INTEGRATION
    # =========================================================================
    h8 = doc.add_heading("Chapter 8: Next.js 16 Web Dashboard", level=1)
    h8.runs[0].font.color.rgb = RGBColor(30, 58, 138)

    doc.add_paragraph(
        "The frontend is built with Next.js 16 (App Router), React 19, and Tailwind CSS v4:"
    )

    p_fe = doc.add_paragraph()
    p_fe.paragraph_format.left_indent = Inches(0.25)
    p_fe.add_run("1. Live Workout Studio (/workout):\n"
                 "   - Real-time webcam integration via navigator.mediaDevices.getUserMedia.\n"
                 "   - In-frame Heads-Up Display (HUD) showing Rep Counter, Movement State badge, Knee Flexion Angle, and AI Coaching Banner.\n"
                 "   - Interactive fallback simulation mode allowing full workout cycle testing without requiring physical camera hardware.\n"
                 "   - Post-workout performance modal displaying overall score rating, 5-factor progress breakdown, and coaching guidance.\n\n"
                 "2. Workout Analytics & History (/history):\n"
                 "   - Longitudinal summary cards: Average Performance Score, Total Sessions Logged, Total Reps Counted, and Form Trend (Improving/Stable/Declining).\n"
                 "   - Detailed session table displaying date, exercise category, sets x reps, color-coded score badge, and calories burned.\n\n"
                 "3. Enhanced Dashboard (/dashboard):\n"
                 "   - Direct quick-launch banner for Phase 2 AI Trainer and seamless navigation between Workout, History, Profile, and Logout.")

    doc.add_paragraph().paragraph_format.space_after = Pt(12)

    # =========================================================================
    # CHAPTER 9: VERIFICATION & TEST RESULTS
    # =========================================================================
    h9 = doc.add_heading("Chapter 9: Verification & Automated Test Results", level=1)
    h9.runs[0].font.color.rgb = RGBColor(30, 58, 138)

    doc.add_paragraph(
        "A total of 82 automated verification checks were executed across all tiers of the application, "
        "achieving a 100% pass rate with zero regressions:"
    )

    test_table = doc.add_table(rows=1, cols=4)
    test_widths = [1.6, 2.2, 1.4, 1.6]
    test_headers = ["Test Suite", "File Path", "Checks Run", "Verified Result"]
    test_data = [
        ["Phase 1 Auth & Profile", "backend/verify_step_2d.py", "12 checks", "PASS (100%)"],
        ["Phase 2.1 Database & FKs", "backend/verify_phase_2_1.py", "9 checks", "PASS (100%)"],
        ["Phase 2.2 MediaPipe Vision", "ml/pose/test_pose_detector.py", "9 tests", "PASS (100%)"],
        ["Phase 2.3 FSM & Angles", "ml/pose/test_squat_pipeline.py", "22 tests", "PASS (100%)"],
        ["Phase 2.4 Form Analysis", "ml/pose/test_form_analyzer.py", "11 tests", "PASS (100%)"],
        ["Phase 2.5 Performance", "ml/pose/test_performance_analyzer.py", "8 tests", "PASS (100%)"],
        ["Backend API & Security", "backend/test_phase_2_api.py", "4 tests", "PASS (100%)"],
        ["End-to-End Smoke Test", "backend/smoke_test_e2e.py", "7 steps", "PASS (100%)"],
        ["Next.js Production Build", "frontend/ (npm.cmd run build)", "9 routes", "PASS (0 Errors)"],
    ]
    style_table(test_table, test_widths, test_headers, test_data, header_bg="059669")

    doc.add_paragraph().paragraph_format.space_after = Pt(12)

    # =========================================================================
    # CHAPTER 10: RUN COMMANDS & ENVIRONMENT SETUP
    # =========================================================================
    h10 = doc.add_heading("Chapter 10: Run Commands & Developer Guide", level=1)
    h10.runs[0].font.color.rgb = RGBColor(30, 58, 138)

    doc.add_paragraph("Commands to operate the AI Gym & Fitness Assistant locally:")

    p_cmds = doc.add_paragraph()
    p_cmds.paragraph_format.left_indent = Inches(0.25)
    p_cmds.add_run(
        "A. Start Backend FastAPI Server:\n"
        "   cd C:\\Users\\anand\\AI-Gym-Fitness-Assistant\\backend\n"
        "   .\\.venv\\Scripts\\Activate.ps1\n"
        "   uvicorn main:app --reload --port 8000\n\n"
        "B. Start Frontend Development Server:\n"
        "   cd C:\\Users\\anand\\AI-Gym-Fitness-Assistant\\frontend\n"
        "   npm.cmd run dev\n\n"
        "C. Run Computer Vision Standalone Demo:\n"
        "   cd C:\\Users\\anand\\AI-Gym-Fitness-Assistant\\ml\\pose\n"
        "   ..\\..\\backend\\.venv\\Scripts\\python.exe demo.py --source webcam\n\n"
        "D. Run Complete Test Suite:\n"
        "   cd C:\\Users\\anand\\AI-Gym-Fitness-Assistant\\ml\n"
        "   ..\\backend\\.venv\\Scripts\\python.exe -m unittest discover -s pose -p \"test_*.py\"\n"
        "   cd ..\\backend\n"
        "   .\\.venv\\Scripts\\python.exe test_phase_2_api.py\n"
        "   .\\.venv\\Scripts\\python.exe smoke_test_e2e.py"
    )

    # Save Document
    doc.save(OUTPUT_DOCX)
    print(f"[SUCCESS] Word document generated successfully at:\n{OUTPUT_DOCX}")


if __name__ == "__main__":
    build_word_guide()
