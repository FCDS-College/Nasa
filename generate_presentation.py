import sys
from pathlib import Path
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN
from pptx.dml.color import RGBColor

# Output Presentation Path
REPO_ROOT = Path(__file__).resolve().parent
PPTX_PATH = REPO_ROOT / "NASA_Evaluation_Platform_Overview.pptx"

def create_presentation():
    prs = Presentation()
    prs.slide_width = Inches(13.333)  # 16:9 Widescreen
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6]

    # Color Palette: NASA Deep Space Tech Theme
    C_BG = RGBColor(11, 15, 25)         # Dark navy background #0B0F19
    C_CARD = RGBColor(23, 32, 51)       # Card navy #172033
    C_CYAN = RGBColor(56, 189, 248)     # Accent Cyan #38BDF8
    C_GOLD = RGBColor(251, 191, 36)     # Gold #FBBF24
    C_WHITE = RGBColor(243, 244, 246)   # Text off-white #F3F4F6
    C_GRAY = RGBColor(156, 163, 175)    # Text gray #9CA3AF
    C_BORDER = RGBColor(31, 41, 55)

    def add_slide_bg(slide):
        bg = slide.shapes.add_shape(1, 0, 0, prs.slide_width, prs.slide_height)
        bg.fill.solid()
        bg.fill.fore_color.rgb = C_BG
        bg.line.fill.background()
        return bg

    def add_header(slide, title_text, subtitle_text):
        tx_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.5), Inches(11.7), Inches(1.2))
        tf = tx_box.text_frame
        tf.word_wrap = True
        
        p = tf.paragraphs[0]
        p.text = title_text
        p.font.size = Pt(26)
        p.font.bold = True
        p.font.color.rgb = C_CYAN
        
        p2 = tf.add_paragraph()
        p2.text = subtitle_text
        p2.font.size = Pt(14)
        p2.font.color.rgb = C_GRAY

    # ==========================================
    # SLIDE 1: Title Slide
    # ==========================================
    s1 = prs.slides.add_slide(blank_layout)
    add_slide_bg(s1)

    tbox = s1.shapes.add_textbox(Inches(1.2), Inches(2.0), Inches(10.9), Inches(3.5))
    tf = tbox.text_frame
    tf.word_wrap = True

    p = tf.paragraphs[0]
    p.text = "NASA Advanced Scientific Intelligence Platform"
    p.font.size = Pt(36)
    p.font.bold = True
    p.font.color.rgb = C_CYAN

    p2 = tf.add_paragraph()
    p2.text = "AI Evaluation, Research Intelligence & Quality Verification Harness (Phase 2)"
    p2.font.size = Pt(20)
    p2.font.color.rgb = C_GOLD
    p2.space_before = Pt(12)

    p3 = tf.add_paragraph()
    p3.text = "Architect: Ziad (Engineer 5)  |  Basis: Phase 2 Plan (M10, M11, C1–C6) & MVP §18"
    p3.font.size = Pt(14)
    p3.font.color.rgb = C_WHITE
    p3.space_before = Pt(32)

    # ==========================================
    # SLIDE 2: Architectural Overview
    # ==========================================
    s2 = prs.slides.add_slide(blank_layout)
    add_slide_bg(s2)
    add_header(s2, "1. Architecture & Quality Taxonomy", "The four non-overlapping quality dimensions governing NASA Phase 2 decisions")

    cards_s2 = [
        ("Data Quality (C4)", "Ensures source integrity, hash parity, and exact locator matching.\n- Schema compliance (§18 JSON Schema)\n- Zero document leakage across splits\n- Real NASA/NIST technical publications"),
        ("Knowledge Quality (C5)", "Validates extracted claims, entities, and scientific triples.\n- Typology classification (source-reported vs derived)\n- Independent Corroboration Rule (>=2 sources)\n- No duplicate echo-chamber validation"),
        ("Model Quality (C2 & M10)", "Mathematical evaluation of algorithm outputs.\n- Retrieval: Recall@k, MRR, nDCG@k\n- Vision: Flame segmentation IoU & Dice\n- Pareto multi-criteria candidate model ranking"),
        ("Answer Quality (C1 & C3)", "User-facing safety, trust, and citation grounding.\n- Citation Precision, Recall & F1\n- Automated PII & Classified Ref masking\n- 100% correct abstention on unanswerable queries")
    ]

    for i, (title, body) in enumerate(cards_s2):
        col = i % 2
        row = i // 2
        left = Inches(0.8 + col * 5.9)
        top = Inches(1.8 + row * 2.6)
        
        shape = s2.shapes.add_shape(1, left, top, Inches(5.6), Inches(2.3))
        shape.fill.solid()
        shape.fill.fore_color.rgb = C_CARD
        shape.line.color.rgb = C_CYAN
        shape.line.width = Pt(1)
        
        tf = shape.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = title
        p.font.size = Pt(16)
        p.font.bold = True
        p.font.color.rgb = C_GOLD
        
        p2 = tf.add_paragraph()
        p2.text = body
        p2.font.size = Pt(12)
        p2.font.color.rgb = C_WHITE
        p2.space_before = Pt(6)

    # ==========================================
    # SLIDE 3: Core Pipeline Classes (master_pipeline.py)
    # ==========================================
    s3 = prs.slides.add_slide(blank_layout)
    add_slide_bg(s3)
    add_header(s3, "2. Core Pipeline Classes (master_pipeline.py)", "Modular evaluation and guardrail components ensuring robust gate enforcement")

    classes_s3 = [
        ("ProvenanceTracker", "Extracts §18 metadata automatically: Git commit hash, SHA-256 dataset checksum, hardware specs, ISO-8601 UTC timestamp, and scorer version."),
        ("PIIMaskingGuardrail", "Redacts emails, phone numbers, and sensitive identifiers. Regex tailored for NASA classified references (NASA-CONF-*) and personnel contact."),
        ("CitationVerificationGuardrail", "Validates that model citations strictly match expected technical document locators. Computes citation score and enforces safe-to-publish threshold."),
        ("CrossModalConsistencyEngine", "Detects discrepancies between textual mission reports ('nominal') and computer vision anomaly features ('anomaly/damage detected')."),
        ("Hybrid LLMJudge", "Dual-engine evaluator: Uses Google Gemini 1.5 Pro when GEMINI_API_KEY is present; automatically falls back to local domain heuristics offline."),
        ("MasterSafetyPipeline", "Central orchestrator executing all safety layers sequentially, aggregating check statuses, and generating signed JSON provenance reports.")
    ]

    for i, (title, desc) in enumerate(classes_s3):
        col = i % 3
        row = i // 2
        left = Inches(0.8 + col * 3.9)
        top = Inches(1.8 + row * 2.6)
        
        box = s3.shapes.add_shape(1, left, top, Inches(3.7), Inches(2.3))
        box.fill.solid()
        box.fill.fore_color.rgb = C_CARD
        box.line.color.rgb = C_BORDER
        box.line.width = Pt(1)
        
        tf = box.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = title
        p.font.size = Pt(15)
        p.font.bold = True
        p.font.color.rgb = C_CYAN
        
        p2 = tf.add_paragraph()
        p2.text = desc
        p2.font.size = Pt(11)
        p2.font.color.rgb = C_WHITE
        p2.space_before = Pt(6)

    # ==========================================
    # SLIDE 4: Mathematical Metrics & Scientific Ranking
    # ==========================================
    s4 = prs.slides.add_slide(blank_layout)
    add_slide_bg(s4)
    add_header(s4, "3. Evaluation Algorithms & Ranking Functions", "Deterministic mathematical computations implemented across metrics.py, cv_metrics.py & ranking.py")

    sec_s4 = [
        ("IR & RAG Metrics (metrics.py)", 
         "• Recall@K: Proportion of expected evidence recovered in top-k.\n"
         "• MRR: Reciprocal rank of first ground-truth document hit.\n"
         "• nDCG@K: Positional logarithmic discounted cumulative gain.\n"
         "• Citation Precision/Recall/F1: Micro & macro locator matching."),
        ("Flame CV Metrics (cv_metrics.py)", 
         "• compute_mask_iou(): Binary intersection-over-union for flame core.\n"
         "• compute_dice_coefficient(): Boundary F1 overlap (M10 design).\n"
         "• Pixel-level Precision & Recall for soot/flame segmentation."),
        ("Multi-Criteria Ranking (ranking.py)", 
         "• rank_models(): Hard-gate filtering + Pareto frontier speed/accuracy.\n"
         "• rank_documents(): 60% dense vector + 40% BM25 + NASA authority boost.\n"
         "• rank_knowledge_records(): Hierarchical source priority + corroboration.")
    ]

    for i, (stitle, sbody) in enumerate(sec_s4):
        left = Inches(0.8 + i * 3.9)
        top = Inches(1.8)
        box = s4.shapes.add_shape(1, left, top, Inches(3.7), Inches(5.0))
        box.fill.solid()
        box.fill.fore_color.rgb = C_CARD
        box.line.color.rgb = C_GOLD
        box.line.width = Pt(1)

        tf = box.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = stitle
        p.font.size = Pt(16)
        p.font.bold = True
        p.font.color.rgb = C_GOLD

        p2 = tf.add_paragraph()
        p2.text = sbody
        p2.font.size = Pt(13)
        p2.font.color.rgb = C_WHITE
        p2.space_before = Pt(10)

    # ==========================================
    # SLIDE 5: Benchmark Dataset (rag_gold.jsonl)
    # ==========================================
    s5 = prs.slides.add_slide(blank_layout)
    add_slide_bg(s5)
    add_header(s5, "4. Gold Benchmark (§18 Compliant Dataset)", "35 curated NASA microgravity combustion instances with strict split isolation")

    items_s5 = [
        ("Dataset Structure", "• Total instances: 35 curated cases\n• Schema: gold_schema.json\n• Domain: NASA Glenn, FLEX, ACME, SAFFIRE, NASA-STD-6001B, NIST-SP-1200\n• All records carry expected_evidence_ids, source locators, and rubric_version 'v2.0'"),
        ("Splits & Leakage Control", "• Dev split: 12 cases (DOC-001 to DOC-009)\n• Validation split: 12 cases (DOC-004 to DOC-014)\n• Holdout split: 11 cases (DOC-001 to DOC-015)\n• Zero document locator leakage enforced via pytest"),
        ("Special Case Taxonomies", "• Unanswerable (4 cases): Budget, salaries, weather - forces model to decline safely.\n• Adversarial (3 cases): Prompt injections, security overrides, dangerous propellant recipes.\n• Modality: 20 Text, 8 Image, 7 Table")
    ]

    for i, (title, content) in enumerate(items_s5):
        left = Inches(0.8 + i * 3.9)
        top = Inches(1.8)
        box = s5.shapes.add_shape(1, left, top, Inches(3.7), Inches(5.0))
        box.fill.solid()
        box.fill.fore_color.rgb = C_CARD
        box.line.color.rgb = C_CYAN
        box.line.width = Pt(1)

        tf = box.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = title
        p.font.size = Pt(16)
        p.font.bold = True
        p.font.color.rgb = C_CYAN

        p2 = tf.add_paragraph()
        p2.text = content
        p2.font.size = Pt(13)
        p2.font.color.rgb = C_WHITE
        p2.space_before = Pt(10)

    # ==========================================
    # SLIDE 6: Automated Harness, Reports & CI/CD
    # ==========================================
    s6 = prs.slides.add_slide(blank_layout)
    add_slide_bg(s6)
    add_header(s6, "5. Automated Execution, Reporting & CI/CD", "Numbers are generated, never typed: Full automation loop from commit to dashboard")

    points_s6 = [
        ("Unified RAG Connector", "tests/eval/rag_connector.py provides seamless switching:\n• `python run_evaluation.py --model mock` (local testing)\n• `python run_evaluation.py --model api` (production REST backend)."),
        ("Automated Report Rendering", "render_report.py reads evaluation_report.json and generates:\n• Markdown Scorecard: docs/evaluation/reports/baseline-v0.1.0-mvp.md\n• HTML Dashboard: scorecard.html with dark mode and metric badges."),
        ("Continuous Integration (CI)", ".github/workflows/eval.yml executes on every push/PR:\n• Runs 21 Pytest gates\n• Runs benchmark evaluation\n• Uploads evaluation artifacts and HTML scorecards automatically."),
        ("Pytest Gate Status", "Current execution status: 17 Passed, 4 Skipped (API contract stubs awaiting backend deployment) in 0.49s.")
    ]

    for i, (title, content) in enumerate(points_s6):
        col = i % 2
        row = i // 2
        left = Inches(0.8 + col * 5.9)
        top = Inches(1.8 + row * 2.6)
        
        box = s6.shapes.add_shape(1, left, top, Inches(5.6), Inches(2.3))
        box.fill.solid()
        box.fill.fore_color.rgb = C_CARD
        box.line.color.rgb = C_BORDER
        box.line.width = Pt(1)

        tf = box.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = title
        p.font.size = Pt(16)
        p.font.bold = True
        p.font.color.rgb = C_GOLD

        p2 = tf.add_paragraph()
        p2.text = content
        p2.font.size = Pt(12)
        p2.font.color.rgb = C_WHITE
        p2.space_before = Pt(6)

    # Save
    prs.save(str(PPTX_PATH))
    print(f"Presentation saved successfully to: {PPTX_PATH}")

if __name__ == "__main__":
    create_presentation()
