"""Build the 3-minute Flame in Freefall pitch deck (python-pptx, 16:9).

    python docs/presentations/build_pitch_deck.py

Writes docs/presentations/flame-in-freefall-3min-pitch.pptx. Style follows generate_presentation.py (dark navy,
cards); images are the dashboard screenshots taken by apps/web/scripts/demo-smoke.mjs (docs/presentations/screenshots/
pitch-*.png). Speaker notes are read from PITCH_SCRIPT_3MIN.md so the deck and the script never drift apart. Every
number on a slide is in .internal/research/2026-11-13-apollo1-facts.md.
"""
from __future__ import annotations

import re
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Emu, Inches, Pt

HERE = Path(__file__).resolve().parent
OUT = HERE / "flame-in-freefall-3min-pitch.pptx"
SHOTS = HERE / "screenshots"
SCRIPT = HERE / "PITCH_SCRIPT_3MIN.md"
FONT = "Arial"

BG = RGBColor(11, 15, 25)
CARD = RGBColor(23, 32, 51)
BORDER = RGBColor(45, 55, 72)
WHITE = RGBColor(243, 244, 246)
GRAY = RGBColor(156, 163, 175)
DIM = RGBColor(107, 114, 128)
EMBER = RGBColor(249, 115, 22)
RED = RGBColor(239, 68, 68)
GREEN = RGBColor(34, 197, 94)
BLUE = RGBColor(96, 165, 250)
BLACK = RGBColor(0, 0, 0)


def speaker_notes() -> list[str]:
    """One note per '### Slide N' section of the script: its quoted lines, without markdown emphasis."""
    notes = []
    for section in re.split(r"^### ", SCRIPT.read_text(encoding="utf-8"), flags=re.M)[1:]:
        if not section.startswith("Slide"):
            continue
        heading, _, body = section.partition("\n")
        spoken = [re.sub(r"\*\*|\*", "", line[1:].strip()) for line in body.splitlines() if line.startswith(">")]
        notes.append(f"{heading.strip()}\n\n" + "\n".join(s for s in spoken if s))
    return notes


class Deck:
    def __init__(self) -> None:
        self.prs = Presentation()
        self.prs.slide_width, self.prs.slide_height = Inches(13.333), Inches(7.5)
        self.W, self.H = self.prs.slide_width, self.prs.slide_height

    def slide(self, background: RGBColor = BG):
        s = self.prs.slides.add_slide(self.prs.slide_layouts[6])
        bg = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, self.W, self.H)
        bg.fill.solid()
        bg.fill.fore_color.rgb = background
        bg.line.fill.background()
        return s

    @staticmethod
    def text(slide, x, y, w, h, runs, size=18, color=WHITE, bold=False, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP,
             spacing=1.1):
        """runs: a string, or a list of paragraphs; a paragraph is a string or a list of (text, overrides) pieces."""
        box = slide.shapes.add_textbox(x, y, w, h)
        tf = box.text_frame
        tf.word_wrap = True
        tf.vertical_anchor = anchor
        tf.margin_left = tf.margin_right = Inches(0.05)
        paragraphs = [runs] if isinstance(runs, str) else runs
        for i, para in enumerate(paragraphs):
            p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            p.alignment = align
            p.line_spacing = spacing
            pieces = [(para, {})] if isinstance(para, str) else para
            for piece, opts in pieces:
                r = p.add_run()
                r.text = piece
                f = r.font
                f.name = FONT
                f.size = Pt(opts.get("size", size))
                f.bold = opts.get("bold", bold)
                f.italic = opts.get("italic", False)
                f.color.rgb = opts.get("color", color)
            if isinstance(para, list) and para and para[0][1].get("space_before"):
                p.space_before = Pt(para[0][1]["space_before"])
        return box

    @staticmethod
    def card(slide, x, y, w, h, fill=CARD, line=BORDER, line_width=1.0):
        shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, y, w, h)
        shape.adjustments[0] = 0.06
        shape.fill.solid()
        shape.fill.fore_color.rgb = fill
        shape.line.color.rgb = line
        shape.line.width = Pt(line_width)
        shape.shadow.inherit = False
        return shape

    def header(self, slide, kicker, title, kicker_color=EMBER):
        self.text(slide, Inches(0.7), Inches(0.45), Inches(12), Inches(0.4), kicker.upper(), size=13, color=kicker_color, bold=True)
        self.text(slide, Inches(0.7), Inches(0.8), Inches(12), Inches(0.9), title, size=32, bold=True)

    def image(self, slide, path: Path, x, y, max_w, max_h, border=BORDER):
        from PIL import Image

        with Image.open(path) as im:
            ratio = im.width / im.height
        w, h = max_w, int(max_w / ratio)
        if h > max_h:
            h, w = max_h, int(max_h * ratio)
        x = x + (max_w - w) // 2
        frame = self.card(slide, Emu(x - Inches(0.04)), Emu(y - Inches(0.04)), Emu(w + Inches(0.08)), Emu(h + Inches(0.08)),
                          fill=BORDER, line=border, line_width=1.5)
        frame.adjustments[0] = 0.02
        slide.shapes.add_picture(str(path), x, y, w, h)
        return w, h

    def footer(self, slide, text):
        self.text(slide, Inches(0.7), Inches(7.0), Inches(12), Inches(0.35), text, size=10, color=DIM)


def build() -> Path:
    d = Deck()
    notes = speaker_notes()
    assert len(notes) == 7, f"expected 7 slide sections in {SCRIPT.name}, found {len(notes)}"

    # 1 · Hook ---------------------------------------------------------------------------------------------------
    s = d.slide(BLACK)
    d.text(s, Inches(0.9), Inches(0.9), Inches(11.5), Inches(0.6), "27 JANUARY 1967 · LAUNCH COMPLEX 34", size=16, color=GRAY, bold=True)
    d.text(s, Inches(0.9), Inches(1.6), Inches(11.5), Inches(2.4), [
        [("100% oxygen.", {"color": RED, "bold": True, "size": 60})],
        [("16.7 psi.  One spark.", {"bold": True, "size": 60})],
    ], spacing=1.0)
    d.text(s, Inches(0.9), Inches(4.05), Inches(11.5), Inches(0.6), "Virgil I. Grissom  ·  Edward H. White II  ·  Roger B. Chaffee",
           size=22, color=WHITE)
    d.text(s, Inches(0.9), Inches(5.0), Inches(11.5), Inches(1.4), [
        [("“…materials were exposed to 16.2 psia 100% oxygen environment in which they had ", {"italic": True}),
         ("never been tested", {"italic": True, "bold": True, "color": EMBER}), (".”", {"italic": True})],
        [("NASA, Crew Exploration Vehicle ECLSS Fire Protection Approach (NTRS 20070021223), p. 2. "
          "The Apollo 204 Review Board gives 16.7 psia (NTRS 19930078717, p. 189).", {"size": 11, "color": DIM, "space_before": 8})],
    ], size=20, color=GRAY)

    # 2 · Problem ------------------------------------------------------------------------------------------------
    s = d.slide()
    d.header(s, "Sixty years later", "We are choosing new cabin atmospheres again")
    stats = [
        ("30–34%", "O₂ planned for Orion and lunar-lander cabins, against 21% on the ISS", "NASA/TM-2008-215260, p. 5", EMBER),
        ("1950", "microgravity combustion tests in 19 NASA flight investigations: droplets, gas flames, burning solids, smoke", "NASA Physical Sciences Informatics", BLUE),
        ("27", "NASA technical reports, licence-checked, every page citable", "NASA Technical Reports Server", BLUE),
    ]
    for i, (big, label, src, color) in enumerate(stats):
        x = Inches(0.7 + i * 4.1)
        d.card(s, x, Inches(2.0), Inches(3.8), Inches(3.2))
        d.text(s, x + Inches(0.3), Inches(2.25), Inches(3.3), Inches(1.1), big, size=46, color=color, bold=True)
        d.text(s, x + Inches(0.3), Inches(3.35), Inches(3.3), Inches(1.3), label, size=16)
        d.text(s, x + Inches(0.3), Inches(4.75), Inches(3.3), Inches(0.4), src, size=11, color=DIM)
    d.text(s, Inches(0.7), Inches(5.7), Inches(12), Inches(1.0), [
        [("The evidence exists. It is scattered, slow to search, and ", {}), ("silent about where it ends.", {"bold": True, "color": EMBER})],
    ], size=24)

    # 3 · It solves (ISS) ----------------------------------------------------------------------------------------
    s = d.slide()
    d.header(s, "Flame in Freefall · it solves", "Pick an atmosphere: ISS air", kicker_color=GREEN)
    d.image(s, SHOTS / "pitch-1-iss-covered.png", Inches(0.7), Inches(1.85), Inches(7.6), Inches(4.9))
    bullets = [("310", "flight tests lie near it, with the closest one cited"),
               ("Ranked", "investigations by how directly their data applies"),
               ("Cited", "every number links to its NASA table cell"),
               ("Estimated", "droplet-flame outcomes from a validated model")]
    for i, (k, v) in enumerate(bullets):
        y = Inches(1.95 + i * 1.2)
        d.card(s, Inches(8.65), y, Inches(4.0), Inches(1.0))
        d.text(s, Inches(8.85), y + Inches(0.08), Inches(3.7), Inches(0.9),
               [[(k + "  ", {"bold": True, "color": GREEN, "size": 20}), (v, {"size": 15})]], anchor=MSO_ANCHOR.MIDDLE)

    # 4 · The refusal (Apollo 1) ---------------------------------------------------------------------------------
    s = d.slide()
    d.header(s, "It knows when not to answer", "Apollo 1's atmosphere: the system refuses", kicker_color=RED)
    d.image(s, SHOTS / "pitch-2-apollo1-refusal.png", Inches(0.7), Inches(1.85), Inches(7.6), Inches(4.9))
    d.card(s, Inches(8.65), Inches(1.95), Inches(4.0), Inches(2.0), fill=RGBColor(40, 16, 20), line=RED, line_width=1.5)
    d.text(s, Inches(8.85), Inches(2.05), Inches(3.7), Inches(1.8),
           "“None of the 1950 flight tests cover this atmosphere.”", size=22, bold=True, anchor=MSO_ANCHOR.MIDDLE)
    facts = [("2.5×", "the highest O₂ ever flown (40%)"), ("1 g", "while every test was in microgravity"),
             ("0", "estimates: the nearest real test is shown instead")]
    for i, (k, v) in enumerate(facts):
        d.text(s, Inches(8.75), Inches(4.2 + i * 0.75), Inches(3.9), Inches(0.7),
               [[(k + "  ", {"bold": True, "color": RED, "size": 24}), (v, {"size": 15})]], anchor=MSO_ANCHOR.MIDDLE)
    d.footer(s, "The decision Apollo 1 needed and never had: an atmosphere nobody had tested. Sources: NTRS 19930078717 p. 189, 20070021223 p. 2.")

    # 5 · What changed, and where the data is --------------------------------------------------------------------
    s = d.slide()
    d.header(s, "What changed after, and where data does exist", "From a lesson to an atmosphere the data covers", kicker_color=GREEN)
    d.image(s, SHOTS / "pitch-3-apollo1-lesson-timeline.png", Inches(0.7), Inches(1.85), Inches(5.9), Inches(4.95))
    d.image(s, SHOTS / "pitch-4-orion-covered.png", Inches(6.85), Inches(1.85), Inches(5.8), Inches(3.5))
    d.text(s, Inches(6.85), Inches(5.55), Inches(5.8), Inches(1.3), [
        [("Orion, 30% O₂ at 71 kPa: ", {"bold": True, "color": GREEN}), ("inside the flight envelope, with 8 real tests and an estimate.", {})],
        [("Covered by data, not called safe: 30% O₂ is more flammable than air.", {"size": 14, "color": GRAY, "space_before": 6})],
    ], size=18)
    d.footer(s, "Every timeline line links to a NASA page: Apollo 204 Review Board report, Beta fibre history, Orion fire-protection paper, NASA/TM-2008-215260.")

    # 6 · Business -----------------------------------------------------------------------------------------------
    s = d.slide()
    d.header(s, "The business", "An evidence workspace for spacecraft fire safety")
    cols = [
        ("Customers", BLUE, ["Commercial station and habitat teams (cabin, ECLSS, safety)",
                             "Materials suppliers qualifying for crewed vehicles",
                             "Agencies and microgravity combustion labs"]),
        ("What they pay for", EMBER, ["Team workspace: coverage verdict, ranking, cited exports",
                                      "API (contract 0.7.0) for in-house tools",
                                      "Signed coverage reports for review boards"]),
        ("How we start", GREEN, ["NASA SBIR / ESA BIC pilots",
                                 "2–3 design partners, single-tenant",
                                 "Then multi-tenant SaaS"]),
    ]
    for i, (title, color, items) in enumerate(cols):
        x = Inches(0.7 + i * 4.1)
        d.card(s, x, Inches(1.95), Inches(3.8), Inches(3.5))
        d.text(s, x + Inches(0.3), Inches(2.1), Inches(3.3), Inches(0.5), title, size=20, bold=True, color=color)
        d.text(s, x + Inches(0.3), Inches(2.7), Inches(3.3), Inches(2.6),
               [[("• " + it, {"size": 15, "space_before": 6 if j else 0})] for j, it in enumerate(items)])
    d.text(s, Inches(0.7), Inches(5.75), Inches(12), Inches(1.0), [
        [("Measured: ", {"bold": True, "color": EMBER}),
         ("outcome model macro-F1 0.54 vs 0.27 baseline (ROC-AUC 0.86, split by test day) · 100% of numbers cited · "
          "refuses outside its flight envelope", {})],
    ], size=17)

    # 7 · Close --------------------------------------------------------------------------------------------------
    s = d.slide(BLACK)
    d.text(s, Inches(0.9), Inches(2.0), Inches(11.5), Inches(2.6), [
        [("An AI in a spacecraft design review", {"size": 34, "color": GRAY})],
        [("must know when not to answer.", {"size": 50, "bold": True})],
    ], spacing=1.05)
    d.text(s, Inches(0.9), Inches(4.7), Inches(11.5), Inches(0.8), [[("Ours does, and shows you why.", {"color": EMBER, "bold": True})]], size=30)
    d.text(s, Inches(0.9), Inches(6.3), Inches(11.5), Inches(0.6), "Flame in Freefall · NASA Space Apps 2026", size=16, color=DIM)

    for slide, note in zip(d.prs.slides, notes):
        slide.notes_slide.notes_text_frame.text = note
    d.prs.save(OUT)
    return OUT


if __name__ == "__main__":
    print(f"wrote {build().relative_to(HERE.parents[1])}")
