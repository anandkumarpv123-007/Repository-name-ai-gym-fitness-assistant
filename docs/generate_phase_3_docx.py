import os
import sys
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

OUTPUT_DIR = r"C:\Users\anand\AI-Gym-Fitness-Assistant\docs"
OUTPUT_DOCX = os.path.join(OUTPUT_DIR, "PHASE_3_MASTER_IMPLEMENTATION_GUIDE.docx")


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
    table = doc.add_table(rows=1, cols=1)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    cell = table.cell(0, 0)
    cell.width = Inches(6.5)

    border_color = "2563EB" if alert_type == "NOTE" else ("16A34A" if alert_type == "TIP" else "DC2626")
    bg_color = "EFF6FF" if alert_type == "NOTE" else ("F0FDF4" if alert_type == "TIP" else "FEF2F2")

    set_cell_background(cell, bg_color)
    set_cell_margins(cell, top=120, bottom=120, left=160, right=160)

    tcPr = cell._element.get_or_add_tcPr()
    borders = parse_xml(
        f'<w:tcBorders {nsdecls("w")}>'
        f'<w:top w:val="none"/>'
        f'<w:left w:val="single" w:sz="24" w:space="0" w:color="{border_color}"/>'
        f'<w:bottom w:val="none"/>'
        f'<w:right w:val="none"/>'
        f'</w:tcBorders>'
    )
    tcPr.append(borders)

    p = cell.paragraphs[0]
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(2)
    r_tag = p.add_run(f"[{alert_type}] ")
    r_tag.bold = True
    r_tag.font.size = Pt(10)
    if alert_type == "NOTE":
        r_tag.font.color.rgb = RGBColor(37, 99, 235)
    elif alert_type == "TIP":
        r_tag.font.color.rgb = RGBColor(22, 163, 74)
    else:
        r_tag.font.color.rgb = RGBColor(220, 38, 38)

    r_body = p.add_run(text)
    r_body.font.size = Pt(9.5)
    r_body.font.color.rgb = RGBColor(51, 65, 85)

    doc.add_paragraph().paragraph_format.space_after = Pt(4)


def style_table(table, col_widths, headers, data, header_bg="1E3A8A"):
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
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

    for row in table.rows:
        for i, w in enumerate(col_widths):
            row.cells[i].width = Inches(w)

    doc_p = table._element.getparent()
    # add slight spacing after table


def add_code_block(doc, code_text):
    table = doc.add_table(rows=1, cols=1)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    cell = table.cell(0, 0)
    cell.width = Inches(6.5)
    set_cell_background(cell, "0F172A")
    set_cell_margins(cell, top=100, bottom=100, left=140, right=140)

    p = cell.paragraphs[0]
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(2)
    r = p.add_run(code_text.strip())
    r.font.name = "Consolas"
    r.font.size = Pt(8.5)
    r.font.color.rgb = RGBColor(226, 232, 240)

    doc.add_paragraph().paragraph_format.space_after = Pt(4)


def add_heading_styled(doc, text, level):
    h = doc.add_heading(text, level=level)
    h.paragraph_format.space_before = Pt(14)
    h.paragraph_format.space_after = Pt(4)
    for r in h.runs:
        if level == 1:
            r.font.color.rgb = RGBColor(30, 58, 138)  # Deep Navy
            r.font.size = Pt(18)
            r.bold = True
        elif level == 2:
            r.font.color.rgb = RGBColor(14, 116, 144)  # Cyan/Teal
            r.font.size = Pt(14)
            r.bold = True
        else:
            r.font.color.rgb = RGBColor(51, 65, 85)  # Slate
            r.font.size = Pt(11.5)
            r.bold = True
    return h


def build_docx():
    doc = Document()

    # Configure Margins
    for section in doc.sections:
        section.top_margin = Inches(0.8)
        section.bottom_margin = Inches(0.8)
        section.left_margin = Inches(0.8)
        section.right_margin = Inches(0.8)

    # Document Header / Title
    title_p = doc.add_paragraph()
    title_p.paragraph_format.space_before = Pt(12)
    title_p.paragraph_format.space_after = Pt(2)
    r_badge = title_p.add_run("AI GYM & FITNESS ASSISTANT  |  PHASE 3 MASTER GUIDE\n")
    r_badge.font.size = Pt(11)
    r_badge.font.bold = True
    r_badge.font.color.rgb = RGBColor(14, 116, 144)

    r_title = title_p.add_run("Pose-to-Performance Analyzer &\nWeekly Progress Intelligence")
    r_title.font.size = Pt(24)
    r_title.font.bold = True
    r_title.font.color.rgb = RGBColor(30, 58, 138)

    sub_p = doc.add_paragraph()
    sub_p.paragraph_format.space_after = Pt(16)
    r_sub = sub_p.add_run(
        "Complete Architectural, Algorithmic, Mathematical, API, Frontend, "
        "and Test Documentation for Beginners and Engineering Reviewers"
    )
    r_sub.font.size = Pt(11)
    r_sub.font.color.rgb = RGBColor(100, 116, 139)

    add_callout(
        doc,
        "Phase 3 has been officially reviewed, verified, and APPROVED by Developer 1. "
        "This master document describes the complete implemented system and provides the proposal for Phase 4.",
        "NOTE",
    )

    # 1. WHAT PHASE 3 DOES & WHY WE NEED IT
    add_heading_styled(doc, "1. What Phase 3 Does & Why We Need It", level=1)

    p1 = doc.add_paragraph(
        "In Phase 2, we built a real-time computer vision engine. A user stands in front of a camera, "
        "MediaPipe extracts 33 body landmarks, our finite state machine (FSM) counts repetitions, biomechanical rules "
        "detect posture errors, and our scoring engine calculates a Performance Score (0 to 100) for that single workout session."
    )
    p1.paragraph_format.space_after = Pt(6)

    p2 = doc.add_paragraph(
        "However, an athlete or lifter does not train in a vacuum. A single workout only answers: "
        "'How did I perform right now, in this specific set?' It does NOT answer the most critical questions in fitness:"
    )
    p2.paragraph_format.space_after = Pt(4)

    bullet_pts = [
        ("Am I progressing or regressing?", "Are my technique and stamina improving over time, or is form degrading?"),
        ("What improved the most?", "Which specific component of my movement (Depth, Form, Stability, Tempo) showed the greatest gain?"),
        ("What bad habits keep recurring?", "Do I have a persistent technical flaw (like shallow squats or lumbar lean) across multiple workouts?"),
        ("What should I focus on next week?", "What single, clear, deterministic coaching cue should I take into my next session to eliminate my biggest flaw?"),
    ]
    for b_title, b_desc in bullet_pts:
        bp = doc.add_paragraph(style="List Bullet")
        bp.paragraph_format.space_after = Pt(3)
        r1 = bp.add_run(f"{b_title}: ")
        r1.bold = True
        r1.font.color.rgb = RGBColor(30, 58, 138)
        r2 = bp.add_run(b_desc)
        r2.font.color.rgb = RGBColor(51, 65, 85)

    p3 = doc.add_paragraph(
        "Phase 3 bridges this gap by transforming raw, single-session computer vision logs into actionable "
        "longitudinal fitness intelligence. It aggregates historical workouts over a rolling 7-day, 14-day, or 30-day window, "
        "applies mathematically grounded trend classification, resolves metric ties with strict biomechanical priority hierarchies, "
        "detects recurring errors, and delivers real-time coaching via a dedicated REST API and an interactive Next.js dashboard."
    )
    p3.paragraph_format.space_after = Pt(10)

    # 2. COMPLETE END-TO-END DATA FLOW
    add_heading_styled(doc, "2. Complete End-to-End Data Flow", level=1)

    add_code_block(
        doc,
        """[1. VISION ENGINE (Phase 2.2 - 2.5)]
Webcam -> MediaPipe -> Angles -> FSM -> Violations Logged -> Performance Score
                              |
                              v
[2. RELATIONAL DATABASE (PostgreSQL)]
workout_sessions (started_at, performance_score, user_id)
workout_exercises (exercise_id, sets, reps)
pose_metrics (rep_number, metrics_json, violations, form_status)
                              |
                              v
[3. PERFORMANCE SERVICE LAYER (backend/services/performance_service.py)]
- Time Window Filtering [now - days, now] strictly scoped to current_user.id
- Trend Engine: Chronological split into Prior Half vs Recent Half
- Component Delta: rom_score, form_score, stability_score, tempo_score, etc.
- Violation Aggregator: Frequency & Severity Tie-Breaker
- Next-Week Coaching Rule Engine
                              |
                              v
[4. FASTAPI ROUTER (backend/routers/workouts.py)]
GET /performance/weekly?days=7
Validates JWT Bearer -> Enforces User Isolation -> Serializes Pydantic Schema
                              |
                              v
[5. FRONTEND DASHBOARD (frontend/src/app/reports/page.tsx)]
Next.js 16 + React + Tailwind + SVG Visualization Engine
KPI Cards -> Coaching Banner -> Trajectory Chart -> Form Warning Distribution""",
    )

    # 3. DATABASE SCHEMA & HOW PHASE 2 FEEDS PHASE 3
    add_heading_styled(doc, "3. Database Schema & Relational Modeling", level=1)

    doc.add_paragraph(
        "No new database tables were required for Phase 3. The architecture leverages the clean relational schema "
        "established in Phase 2.1 and Phase 2.5, maintaining zero migration risk:"
    ).paragraph_format.space_after = Pt(6)

    schema_table_headers = ["Table Name", "Key Columns Used in Phase 3", "Biomechanical & Progress Role"]
    schema_table_data = [
        [
            "workout_sessions",
            "id, user_id, started_at, performance_score",
            "Filters workouts in time window [now - days, now], scopes tenant isolation, and provides overall session performance score.",
        ],
        [
            "workout_exercises",
            "workout_session_id, exercise_id, sets, reps",
            "Provides repetition counts and exercise breakdown (Squats vs. Push-ups). Protected by ON DELETE RESTRICT on exercises.",
        ],
        [
            "pose_metrics",
            "rep_number, metrics_json, violations, form_status",
            "Stores per-rep telemetry: subcomponent scores (ROM, posture, stability, tempo) and logged violations for frequency detection.",
        ],
    ]
    tbl_schema = doc.add_table(rows=1, cols=3)
    style_table(tbl_schema, [1.5, 2.0, 3.0], schema_table_headers, schema_table_data, header_bg="1E3A8A")

    # 4. MATHEMATICAL FORMULAS & INTELLIGENCE ENGINES
    add_heading_styled(doc, "4. Mathematical Formulas & Intelligence Engines", level=1)

    add_heading_styled(doc, "A. Deterministic Performance Trend Engine (Subdivision 3.2)", level=2)
    doc.add_paragraph(
        "To avoid volatility from single anomalous sessions (such as an off-day due to lack of sleep), "
        "the engine splits all sessions in the time window chronologically into two equal halves:"
    ).paragraph_format.space_after = Pt(4)

    add_code_block(
        doc,
        """Let N = number of completed sessions in window.
If N < 2:
    Trend = 'insufficient_history', Score_Delta = None

Let M = floor(N / 2)
Prior Half  = Sessions [1 ... M]
Recent Half = Sessions [M+1 ... N]

Prior_Avg  = (1 / M) * sum(Scores[1 ... M])
Recent_Avg = (1 / (N - M)) * sum(Scores[M+1 ... N])
Score_Delta = round(Recent_Avg - Prior_Avg, 1)

Classification Rules:
  If Score_Delta >= +2.5 pts  ==> 'improving'
  If Score_Delta <= -2.5 pts  ==> 'declining'
  If -2.5 < Score_Delta < +2.5 ==> 'stable'""",
    )

    doc.add_paragraph(
        "Numerical Example: Suppose an athlete logs 4 workouts: [70.0, 74.0, 85.0, 87.0]. "
        "N = 4, M = 2. Prior Half average = 72.0. Recent Half average = 86.0. "
        "Score Delta = 86.0 - 72.0 = +14.0 pts. Since +14.0 >= +2.5, the trend is deterministically classified as 'improving'."
    ).paragraph_format.space_after = Pt(8)

    add_heading_styled(doc, "B. Strongest Improvement Area & Priority Tie-Breaking (Subdivision 3.3)", level=2)
    doc.add_paragraph(
        "The engine calculates half-over-half score deltas for all 7 subcomponents stored in pose_metrics.metrics_json: "
        "Range of Motion (ROM), Form Accuracy, Stability, Smoothness, Tempo, Completion Quality, and Bilateral Symmetry."
    ).paragraph_format.space_after = Pt(4)

    add_callout(
        doc,
        "Tie-Breaking Rule: If two or more components share the highest point gain (e.g. both Form and ROM gained +10.0 pts), "
        "the engine resolves the tie deterministically using the Biomechanical Hierarchy: "
        "ROM > Form Accuracy > Stability > Smoothness > Tempo > Completion Quality > Symmetry.",
        "TIP",
    )

    add_heading_styled(doc, "C. Recurring Form Weakness & Severity Hierarchy (Subdivision 3.4)", level=2)
    doc.add_paragraph(
        "The engine aggregates all violation strings across all reps. If multiple errors occur with the same frequency, "
        "the engine breaks ties using a strict Biomechanical Severity Hierarchy:"
    ).paragraph_format.space_after = Pt(4)

    severity_table_headers = ["Priority Rank", "Violation Code", "Severity Level", "Clinical / Biomechanical Rationale"]
    severity_table_data = [
        ["1 (Highest)", "INSUFFICIENT_DEPTH", "High", "Repetition invalidity and quad under-loading; foundational squat failure."],
        ["2", "EXCESSIVE_TORSO_LEAN", "High", "Direct lumbar spine shear stress; excessive forward trunk angle."],
        ["3", "KNEE_ALIGNMENT_ISSUE", "Moderate", "Dynamic knee valgus / cave; stress on medial collateral ligament (MCL)."],
        ["4+", "Alphabetical Fallback", "Low/Info", "Ensures 100% deterministic tie-breaking for novel exercise extensions."],
    ]
    tbl_sev = doc.add_table(rows=1, cols=4)
    style_table(tbl_sev, [1.0, 2.0, 1.2, 2.3], severity_table_headers, severity_table_data, header_bg="0E7490")

    add_heading_styled(doc, "D. Actionable Next-Week Coaching Focus (Subdivision 3.5)", level=2)
    doc.add_paragraph(
        "The engine synthesizes the user's primary weakness and trajectory into clear, action-oriented cues:"
    ).paragraph_format.space_after = Pt(4)

    coaching_headers = ["Condition Detected", "Prescribed Actionable Focus Cue"]
    coaching_data = [
        ["Depth Issue (INSUFFICIENT_DEPTH)", "Prioritize reaching parallel depth (knee angle <= 90 deg) before commencing upward ascent."],
        ["Torso Lean (EXCESSIVE_TORSO_LEAN)", "Maintain an upright chest and brace your core to avoid excessive forward torso lean."],
        ["Knee Cave (KNEE_ALIGNMENT_ISSUE)", "Track knees outward in line with your toes to eliminate medial valgus collapse."],
        ["Declining Trajectory", "Reduce rep speed and focus on controlled eccentric tempo to rebuild movement stability."],
        ["Clean Form / Stable / Improving", "Maintain excellent technique and progressively increase repetition volume."],
    ]
    tbl_coach = doc.add_table(rows=1, cols=2)
    style_table(tbl_coach, [2.3, 4.2], coaching_headers, coaching_data, header_bg="1E3A8A")

    # 5. HOW PHASE 2 HALF-SQUAT PROTECTION FEEDS PHASE 3
    add_heading_styled(doc, "5. How Phase 2 Half-Squat Protection Feeds Phase 3", level=1)
    doc.add_paragraph(
        "In Phase 2.3 and 2.4, a key bug was identified where shallow/half squats could prematurely count as valid reps. "
        "We implemented strict depth gating: a rep must reach <= 100 deg knee flexion before transitioning to ASCENDING, "
        "and any rep turning around between 100 and 115 deg is tagged with INSUFFICIENT_DEPTH."
    ).paragraph_format.space_after = Pt(4)

    doc.add_paragraph(
        "In Phase 3, this protection directly powers the intelligence layer: "
        "If a lifter cheats on depth, those reps are logged in pose_metrics with INSUFFICIENT_DEPTH. "
        "Phase 3 aggregates these violations, elevates INSUFFICIENT_DEPTH to the top of the recurring weakness card "
        "via severity tie-breaking, displays the exact percentage of shallow reps in the frontend, "
        "and prescribes the depth-correction coaching cue. This creates complete technical accountability across the week."
    ).paragraph_format.space_after = Pt(8)

    # 6. BACKEND API & PYDANTIC CONTRACTS
    add_heading_styled(doc, "6. Backend API: GET /performance/weekly", level=1)

    doc.add_paragraph(
        "The endpoint GET /performance/weekly?days=7 is registered in backend/routers/workouts.py. "
        "It enforces JWT Bearer authentication, extracts current_user.id, and validates parameters via Pydantic schemas:"
    ).paragraph_format.space_after = Pt(4)

    add_code_block(
        doc,
        """# Pydantic Schema Contract (backend/schemas/workout.py)
class WeeklyPerformanceResponse(BaseModel):
    reporting_period: ReportingPeriod        # start_date, end_date, days
    total_sessions: int                      # total completed sessions
    total_reps: int                          # total volume across exercises
    average_score: Optional[float]           # mean performance score (0-100)
    trend: str                               # improving | declining | stable | insufficient_history
    score_delta: Optional[float]             # half-over-half score delta
    strongest_improvement: str               # component name with point gain
    recurring_form_issue: str                # highest-severity recurring error
    next_week_focus: str                     # action-oriented coaching advice
    exercise_stats: List[ExerciseStatItem]   # breakdown per exercise
    form_warnings: List[FormWarningItem]     # violation counts and percentages
    session_history: List[SessionTrendPoint] # session_id, date, score, reps""",
    )

    # 7. FRONTEND DASHBOARD & VISUALIZATIONS
    add_heading_styled(doc, "7. Frontend Reports Dashboard (/reports)", level=1)

    doc.add_paragraph(
        "Built in frontend/src/app/reports/page.tsx with Next.js 16 (Turbopack) and Tailwind CSS. Key UI components include:"
    ).paragraph_format.space_after = Pt(4)

    ui_items = [
        ("Time Window Selector", "Instant toggle buttons for 7 Days, 14 Days, and 30 Days that refetch the weekly intelligence API."),
        ("KPI Summary Cards", "Four cards displaying Average Score (/100), Total Workouts, Total Tracked Reps, and Movement Trajectory."),
        ("Actionable Focus Banner", "Gradient banner presenting the next-week coaching focus with a visual target icon."),
        ("2-Column Intelligence Cards", "Side-by-side cards highlighting Strongest Measurable Improvement and Recurring Form Weakness."),
        ("SVG Performance Trajectory", "Responsive SVG polyline chart rendering session-by-session scores with reference gridlines (50, 70, 90) and interactive score nodes."),
        ("Violation Frequency Bars", "Progress bars color-coded by severity (rose for high, amber for moderate, blue for mild) showing error distributions."),
        ("Exercise Breakdown Table", "Tabular view showing sessions, reps, and average scores per exercise pattern."),
    ]
    for ut, ud in ui_items:
        up = doc.add_paragraph(style="List Bullet")
        up.paragraph_format.space_after = Pt(3)
        r1 = up.add_run(f"{ut}: ")
        r1.bold = True
        r1.font.color.rgb = RGBColor(14, 116, 144)
        r2 = up.add_run(ud)
        r2.font.color.rgb = RGBColor(51, 65, 85)

    # 8. AUTHENTICATION & CROSS-USER ISOLATION
    add_heading_styled(doc, "8. Authentication & Cross-User Isolation", level=1)
    doc.add_paragraph(
        "All queries in PerformanceService enforce strict tenant boundaries: "
        "WorkoutSession.user_id == current_user.id. "
        "In test_07 of our test suite, two separate users (User A and User B) are evaluated simultaneously. "
        "When User B calls the weekly intelligence API, the response returns 0 sessions and zero leakage from User A."
    ).paragraph_format.space_after = Pt(8)

    # 9. EXPLANATION OF ALL 10 PHASE 3 TESTS
    add_heading_styled(doc, "9. Deep-Dive: All 10 Phase 3 Automated Tests", level=1)

    test_headers = ["Test Name", "Tested Behavior & Logic", "Result"]
    test_data = [
        ["test_01_empty_history", "Zero workouts -> insufficient_history, None averages, clean empty structures.", "PASS"],
        ["test_02_single_session", "Single workout -> establishes baseline without false trend or false delta.", "PASS"],
        ["test_03_trend_calculations", "Verifies mathematical delta thresholds: improving (>= +2.5), declining (<= -2.5), stable.", "PASS"],
        ["test_04_strongest_improvement", "Tests component delta detection and deterministic tie-breaking (ROM > Form > Stability).", "PASS"],
        ["test_05_recurring_form_issues", "Tests violation counting, percentage computation, and severity tie-breaking (Depth > Torso).", "PASS"],
        ["test_06_unauthenticated_rejected", "GET /performance/weekly without JWT token returns HTTP 401 Unauthorized.", "PASS"],
        ["test_07_weekly_api_lifecycle", "Creates live DB sessions, tests end-to-end API response, and verifies cross-user isolation.", "PASS"],
        ["test_08_empty_history_api", "Authenticated call for user with zero workouts returns HTTP 200 with structured default values.", "PASS"],
        ["test_09_multi_exercise_aggregation", "Verifies multi-exercise aggregation breakdown across Squats and Push-ups.", "PASS"],
        ["test_10_declining_trend_api", "Verifies declining trend detection when recent performance degrades.", "PASS"],
    ]
    tbl_tests = doc.add_table(rows=1, cols=3)
    style_table(tbl_tests, [2.2, 3.8, 0.7], test_headers, test_data, header_bg="1E3A8A")

    # 10. REGRESSION VERIFICATION (75/75)
    add_heading_styled(doc, "10. Full Regression Suite (75/75 Passed)", level=1)

    reg_headers = ["Suite Name", "Script Path", "Scope Under Test", "Checks / Result"]
    reg_data = [
        ["Phase 1 Foundation", "backend/verify_step_2d.py", "Auth, Profiles, JWT, PostgreSQL schema", "12 / 12 PASS"],
        ["Phase 2.1 Database", "backend/verify_phase_2_1.py", "Exercise catalogue, sessions, FK constraints", "9 / 9 PASS"],
        ["Phase 2.2 Pose Detector", "ml/pose/test_pose_detector.py", "OpenCV, MediaPipe, 33 Landmarks, Visualizer", "9 / 9 PASS"],
        ["Phase 2.3 Squat Pipeline", "ml/pose/test_squat_pipeline.py", "2D Angles, SMA-5, FSM, Half-Squat Protection", "22 / 22 PASS"],
        ["Phase 2.4 Form Analyzer", "ml/pose/test_form_analyzer.py", "Rule-based form violations & feedback", "11 / 11 PASS"],
        ["Phase 2.5 Score Engine", "ml/pose/test_performance_analyzer.py", "Performance Score v1.0, penalties, jerk", "8 / 8 PASS"],
        ["Phase 2 Backend API", "backend/test_phase_2_api.py", "Workout lifecycle endpoints & auth", "4 / 4 PASS"],
        ["Phase 2 E2E Smoke", "backend/smoke_test_e2e.py", "Live database end-to-end workout session", "7 / 7 PASS"],
        ["Phase 3 Intelligence", "backend/test_phase_3_performance.py", "Weekly aggregation, trends, warnings, API", "10 / 10 PASS"],
        ["Frontend Production Build", "frontend (npm run build)", "Next.js 16 Turbopack, static prerendering", "0 ERRORS"],
    ]
    tbl_reg = doc.add_table(rows=1, cols=4)
    style_table(tbl_reg, [1.5, 2.0, 2.0, 1.2], reg_headers, reg_data, header_bg="1E3A8A")

    # 11. PHASE 4 PROPOSAL ONLY
    add_heading_styled(doc, "11. Phase 4 Architectural Proposal Only", level=1)

    add_callout(
        doc,
        "PROPOSAL ONLY: Per strict project rules, no Phase 4 code has been created or modified. "
        "The following is an architectural roadmap submitted for Developer 1's review and approval.",
        "IMPORTANT",
    )

    doc.add_paragraph(
        "With Phase 2 and Phase 3 establishing a robust single-exercise (Squat) pipeline, Phase 4 expands "
        "AI Gym into a comprehensive Multi-Exercise Fitness Assistant:"
    ).paragraph_format.space_after = Pt(4)

    p4_subdivisions = [
        ("Subdivision 4.1 — Base Exercise Engine & Factory", "Implement BaseExerciseEngine ABC and ExerciseEngineFactory to enable pluggable exercise pipelines."),
        ("Subdivision 4.2 — Push-up Biomechanical Pipeline", "4-state Push-up FSM, elbow flexion angles, lumbar sag and hip pike detection."),
        ("Subdivision 4.3 — Bicep Curl Biomechanical Pipeline", "Elbow flexion state machine, shoulder swing detection, and range of motion verification."),
        ("Subdivision 4.4 — Multi-Exercise Visualizer Integration", "Dynamic skeleton overlays adapting to upper-body and lower-body movement patterns."),
        ("Subdivision 4.5 — Multi-Exercise Workout Session Integration", "Support workouts with multiple exercise sets in a single session."),
        ("Subdivision 4.6 — Frontend Exercise Switcher & HUD", "Interactive exercise picker on /workout with exercise-specific feedback gauges."),
        ("Subdivision 4.7 — Automated Multi-Exercise Test Suite", "Full test coverage and regression for Push-up and Bicep Curl engines."),
    ]
    for s_title, s_desc in p4_subdivisions:
        sp = doc.add_paragraph(style="List Bullet")
        sp.paragraph_format.space_after = Pt(3)
        r1 = sp.add_run(f"{s_title}: ")
        r1.bold = True
        r1.font.color.rgb = RGBColor(30, 58, 138)
        r2 = sp.add_run(s_desc)
        r2.font.color.rgb = RGBColor(51, 65, 85)

    doc.save(OUTPUT_DOCX)
    print(f"[SUCCESS] Document generated at: {OUTPUT_DOCX}")


if __name__ == "__main__":
    build_docx()
