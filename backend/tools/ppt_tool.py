"""PPT builder tool — generates a .pptx file from a structured outline.

The LLM (ppt_agent) calls this tool with a JSON outline; the tool produces
a real PowerPoint file, saves it to the FileStore, and returns a download URL.

Outline schema (JSON string):
{
  "title": "Presentation Title",
  "subtitle": "Optional subtitle",
  "theme": "modern|minimal|corporate",   // optional, default modern
  "slides": [
    {
      "title": "Slide Title",
      "layout": "bullet|two_column|image_text|section",  // optional
      "bullets": ["Point 1", "Point 2", ...],
      "notes": "Speaker notes"   // optional
    },
    ...
  ]
}
"""

from __future__ import annotations

import io
import json
import logging
from typing import Any

from backend.storage.file_store import file_store
from backend.tools.base import BaseTool, ToolDefinition, ToolParameter

logger = logging.getLogger(__name__)

# Theme colour palettes  (title bg, accent, text)
_THEMES: dict[str, dict[str, Any]] = {
    "modern": {
        "title_bg": (0x1A, 0x1A, 0x2E),   # deep navy
        "title_fg": (0xFF, 0xFF, 0xFF),
        "accent":   (0xE9, 0x4F, 0x37),   # coral red
        "slide_bg": (0xFF, 0xFF, 0xFF),
        "body_fg":  (0x33, 0x33, 0x33),
    },
    "minimal": {
        "title_bg": (0xFF, 0xFF, 0xFF),
        "title_fg": (0x22, 0x22, 0x22),
        "accent":   (0x00, 0x7A, 0xFF),
        "slide_bg": (0xFF, 0xFF, 0xFF),
        "body_fg":  (0x44, 0x44, 0x44),
    },
    "corporate": {
        "title_bg": (0x00, 0x33, 0x66),
        "title_fg": (0xFF, 0xFF, 0xFF),
        "accent":   (0xFF, 0xCC, 0x00),
        "slide_bg": (0xF4, 0xF6, 0xF8),
        "body_fg":  (0x1A, 0x1A, 0x1A),
    },
}


def _rgb(r: int, g: int, b: int):
    from pptx.util import Pt
    from pptx.dml.color import RGBColor

    return RGBColor(r, g, b)


def _build_pptx(outline: dict) -> bytes:
    from pptx import Presentation
    from pptx.util import Inches, Pt, Emu
    from pptx.enum.text import PP_ALIGN
    from pptx.dml.color import RGBColor

    theme_name = outline.get("theme", "modern")
    theme = _THEMES.get(theme_name, _THEMES["modern"])

    prs = Presentation()
    prs.slide_width = Inches(13.33)
    prs.slide_height = Inches(7.5)

    slide_layouts = prs.slide_layouts

    def _fill_bg(slide, colour):
        from pptx.oxml.ns import qn
        import lxml.etree as etree

        r, g, b = colour
        bg = slide.background
        fill = bg.fill
        fill.solid()
        fill.fore_color.rgb = RGBColor(r, g, b)

    def _add_textbox(slide, text, left, top, width, height,
                     size_pt=24, bold=False, colour=(0, 0, 0), align=PP_ALIGN.LEFT, wrap=True):
        from pptx.util import Inches, Pt

        txBox = slide.shapes.add_textbox(
            Inches(left), Inches(top), Inches(width), Inches(height)
        )
        tf = txBox.text_frame
        tf.word_wrap = wrap
        p = tf.paragraphs[0]
        p.alignment = align
        run = p.add_run()
        run.text = text
        run.font.size = Pt(size_pt)
        run.font.bold = bold
        run.font.color.rgb = RGBColor(*colour)
        return txBox

    # ── Title slide ──────────────────────────────────────────────────────────
    title_slide = prs.slides.add_slide(slide_layouts[6])  # blank
    _fill_bg(title_slide, theme["title_bg"])

    title_text = outline.get("title", "Presentation")
    subtitle_text = outline.get("subtitle", "")

    _add_textbox(
        title_slide, title_text,
        left=1.0, top=2.5, width=11.33, height=1.5,
        size_pt=44, bold=True,
        colour=theme["title_fg"],
        align=PP_ALIGN.CENTER,
    )
    if subtitle_text:
        _add_textbox(
            title_slide, subtitle_text,
            left=1.0, top=4.2, width=11.33, height=0.8,
            size_pt=24, bold=False,
            colour=theme["title_fg"],
            align=PP_ALIGN.CENTER,
        )

    # ── Content slides ────────────────────────────────────────────────────────
    for slide_data in outline.get("slides", []):
        slide = prs.slides.add_slide(slide_layouts[6])  # blank
        _fill_bg(slide, theme["slide_bg"])

        slide_title = slide_data.get("title", "")
        bullets = slide_data.get("bullets", [])
        notes_text = slide_data.get("notes", "")
        layout = slide_data.get("layout", "bullet")

        # Title bar (accent strip)
        from pptx.util import Inches, Pt

        title_bar = slide.shapes.add_shape(
            1,  # MSO_SHAPE_TYPE.RECTANGLE
            Inches(0), Inches(0), prs.slide_width, Inches(1.1),
        )
        title_bar.fill.solid()
        title_bar.fill.fore_color.rgb = RGBColor(*theme["accent"])
        title_bar.line.fill.background()

        # Slide title text over the bar
        tf = title_bar.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        from pptx.enum.text import PP_ALIGN
        p.alignment = PP_ALIGN.LEFT
        run = p.add_run()
        run.text = f"  {slide_title}"
        run.font.size = Pt(28)
        run.font.bold = True
        run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)

        # Bullets
        if bullets:
            from pptx.util import Inches, Pt

            body_box = slide.shapes.add_textbox(
                Inches(0.5), Inches(1.3), Inches(12.3), Inches(5.8)
            )
            tf = body_box.text_frame
            tf.word_wrap = True

            for i, bullet in enumerate(bullets):
                if i == 0:
                    p = tf.paragraphs[0]
                else:
                    p = tf.add_paragraph()
                p.text = f"• {bullet}"
                p.space_before = Pt(6)
                for run in p.runs:
                    run.font.size = Pt(20)
                    run.font.color.rgb = RGBColor(*theme["body_fg"])

        # Speaker notes
        if notes_text:
            notes_slide = slide.notes_slide
            notes_slide.notes_text_frame.text = notes_text

    buf = io.BytesIO()
    prs.save(buf)
    return buf.getvalue()


class PptBuilderTool(BaseTool):
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="ppt_builder",
            description=(
                "Generate a PowerPoint (.pptx) presentation from a JSON outline. "
                "Returns a download URL for the generated file. "
                "The outline must be valid JSON with a 'title' field and 'slides' array."
            ),
            parameters=[
                ToolParameter(
                    name="outline_json",
                    type="string",
                    description=(
                        "JSON string describing the presentation. Required fields: "
                        "'title' (string), 'slides' (array of {title, bullets[]}). "
                        "Optional: 'subtitle', 'theme' (modern|minimal|corporate), "
                        "per-slide 'notes'."
                    ),
                ),
                ToolParameter(
                    name="filename",
                    type="string",
                    description="Desired filename for the download (no extension needed)",
                    required=False,
                ),
            ],
        )

    async def execute(self, **kwargs: Any) -> str:
        outline_json: str = kwargs.get("outline_json", "")
        filename_hint: str = kwargs.get("filename") or "presentation"

        if not outline_json.strip():
            return "Error: outline_json is required."

        try:
            outline = json.loads(outline_json)
        except json.JSONDecodeError as exc:
            return f"Error: outline_json is not valid JSON — {exc}"

        if "title" not in outline:
            return "Error: outline must contain a 'title' field."
        if "slides" not in outline or not isinstance(outline["slides"], list):
            return "Error: outline must contain a 'slides' array."

        try:
            pptx_bytes = _build_pptx(outline)
        except Exception as exc:
            logger.exception("ppt_builder failed")
            return f"Error generating PowerPoint: {exc}"

        safe_name = filename_hint.replace(" ", "_").replace("/", "-")
        file_id = file_store.save(
            filename=f"{safe_name}.pptx",
            data=pptx_bytes,
            content_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        )

        slide_count = len(outline.get("slides", []))
        title = outline.get("title", "")
        return (
            f"PPT generated successfully!\n"
            f"  Title      : {title}\n"
            f"  Slides     : {slide_count} content slides + 1 title slide\n"
            f"  Theme      : {outline.get('theme', 'modern')}\n"
            f"  Download   : /api/files/{file_id}\n"
            f"  File ID    : {file_id}"
        )
