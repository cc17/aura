"""HTML PPT builder — generates a self-contained HTML presentation file.

The ppt_agent calls this tool with a JSON outline; the tool renders a
polished single-file HTML presentation (no CDN, no external dependencies)
and returns a download link.

Outline schema:
{
  "title": "Deck Title",
  "theme": "dark|light|minimal",   // optional, default "dark"
  "slides": [
    {"type": "title",   "title": "...", "subtitle": "..."},
    {"type": "section", "title": "Part 1", "number": "01"},
    {"type": "bullets", "title": "...", "subtitle": "...", "bullets": ["..."]},
    {"type": "two_col", "title": "...",
     "left_label": "...", "left_items": ["..."],
     "right_label": "...", "right_items": ["..."]},
    {"type": "quote",   "quote": "...", "author": "..."},
    {"type": "end",     "title": "谢谢", "subtitle": "Q & A"}
  ]
}
"""

from __future__ import annotations

import json
import logging
from html import escape
from typing import Any

from backend.storage.file_store import file_store
from backend.tools.base import BaseTool, ToolDefinition, ToolParameter

logger = logging.getLogger(__name__)

# ── Themes ────────────────────────────────────────────────────────────────────

_THEMES: dict[str, dict[str, str]] = {
    "dark": {
        "primary":  "#16213E",
        "accent":   "#E94F37",
        "bg":       "#1A1A2E",
        "text":     "#F0F0F0",
        "subtext":  "rgba(240,240,240,0.55)",
        "card_bg":  "rgba(255,255,255,0.06)",
        "body_bg":  "#0f0f1a",
    },
    "light": {
        "primary":  "#1E3A5F",
        "accent":   "#2563EB",
        "bg":       "#FAFAFA",
        "text":     "#1A1A2E",
        "subtext":  "#64748B",
        "card_bg":  "#F1F5F9",
        "body_bg":  "#E2E8F0",
    },
    "minimal": {
        "primary":  "#111111",
        "accent":   "#111111",
        "bg":       "#FFFFFF",
        "text":     "#111111",
        "subtext":  "#888888",
        "card_bg":  "#F5F5F5",
        "body_bg":  "#DDDDDD",
    },
}

# ── CSS template ──────────────────────────────────────────────────────────────

_CSS = """
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
body{background:{body_bg};display:flex;flex-direction:column;align-items:center;
  justify-content:center;min-height:100vh;
  font-family:-apple-system,BlinkMacSystemFont,'PingFang SC','Microsoft YaHei',
  'Noto Sans CJK SC',sans-serif;overflow:hidden;user-select:none}
.deck{position:relative;width:960px;height:540px;box-shadow:0 25px 80px rgba(0,0,0,.5)}
.slide{position:absolute;inset:0;display:none;flex-direction:column;
  padding:60px 64px;background:{bg};overflow:hidden}
.slide.active{display:flex}

/* ── Nav ── */
.nav{display:flex;align-items:center;gap:12px;margin-top:14px}
.nav button{background:rgba(255,255,255,.1);border:1px solid rgba(255,255,255,.18);
  color:#ccc;padding:7px 22px;border-radius:6px;cursor:pointer;font-size:13px;
  transition:background .15s}
.nav button:hover{background:rgba(255,255,255,.2)}
.nav button:disabled{opacity:.3;cursor:default}
.counter{flex:1;text-align:center;color:#888;font-size:13px}
.progress-wrap{width:960px;height:3px;background:rgba(255,255,255,.08);margin-top:6px}
.progress-bar{height:100%;background:{accent};transition:width .3s ease;border-radius:2px}

/* ── Title slide ── */
.s-title{background:{primary};justify-content:flex-end}
.s-title .tag{font-size:11px;letter-spacing:3px;text-transform:uppercase;
  color:{accent};font-weight:700;margin-bottom:18px}
.s-title h1{font-size:54px;font-weight:800;color:#fff;line-height:1.12;max-width:740px}
.s-title .line{width:44px;height:4px;background:{accent};border-radius:2px;margin:22px 0}
.s-title p{font-size:19px;color:rgba(255,255,255,.6);max-width:600px;line-height:1.5}

/* ── Section slide ── */
.s-section{background:{accent};justify-content:flex-end}
.s-section .num{position:absolute;top:16px;right:48px;font-size:110px;font-weight:900;
  color:rgba(255,255,255,.12);line-height:1}
.s-section h2{font-size:46px;font-weight:800;color:#fff;line-height:1.2;max-width:700px}
.s-section p{margin-top:12px;font-size:17px;color:rgba(255,255,255,.7)}

/* ── Bullets slide ── */
.s-bullets{}
.slide-hdr{border-left:4px solid {accent};padding-left:16px;margin-bottom:32px}
.slide-hdr h2{font-size:30px;font-weight:700;color:{text};line-height:1.25}
.slide-hdr p{font-size:14px;color:{subtext};margin-top:4px}
ul.bullets{list-style:none;display:flex;flex-direction:column;gap:13px}
ul.bullets li{display:flex;align-items:flex-start;gap:14px;
  font-size:19px;color:{text};line-height:1.45}
ul.bullets li::before{content:'';width:8px;height:8px;min-width:8px;
  border-radius:50%;background:{accent};margin-top:8px}

/* ── Two-column slide ── */
.s-two-col .cols{display:grid;grid-template-columns:1fr 1fr;gap:36px;flex:1;margin-top:4px}
.col-label{font-size:11px;font-weight:700;letter-spacing:2px;text-transform:uppercase;
  color:{accent};margin-bottom:12px}
.col-items{display:flex;flex-direction:column;gap:10px}
.col-item{font-size:16px;color:{text};padding:10px 14px;background:{card_bg};
  border-radius:6px;line-height:1.45}

/* ── Quote slide ── */
.s-quote{background:{primary};justify-content:center;align-items:center;text-align:center}
.s-quote blockquote{font-size:27px;font-weight:500;color:#fff;line-height:1.55;
  max-width:680px;position:relative;padding:0 16px}
.s-quote blockquote::before{content:'"';font-size:130px;color:{accent};opacity:.35;
  position:absolute;top:-44px;left:-10px;line-height:1;font-family:Georgia,serif}
.s-quote cite{display:block;margin-top:28px;font-size:15px;
  color:rgba(255,255,255,.55);font-style:normal;letter-spacing:.5px}

/* ── End slide ── */
.s-end{background:{primary};justify-content:center;align-items:center;text-align:center}
.s-end h2{font-size:52px;font-weight:800;color:#fff}
.s-end p{margin-top:14px;font-size:19px;color:rgba(255,255,255,.55)}
.s-end .dot{width:10px;height:10px;border-radius:50%;background:{accent};
  margin:28px auto 0}
"""

# ── JS ────────────────────────────────────────────────────────────────────────

_JS = """
const slides=document.querySelectorAll('.slide');
let cur=0;
function update(){
  slides.forEach((s,i)=>s.classList.toggle('active',i===cur));
  document.getElementById('ctr').textContent=(cur+1)+' / '+slides.length;
  document.getElementById('pb').style.width=((cur+1)/slides.length*100)+'%';
  document.getElementById('prev').disabled=cur===0;
  document.getElementById('next').disabled=cur===slides.length-1;
}
function go(d){cur=Math.max(0,Math.min(slides.length-1,cur+d));update();}
document.addEventListener('keydown',e=>{
  if(['ArrowRight','ArrowDown',' '].includes(e.key)){e.preventDefault();go(1);}
  if(['ArrowLeft','ArrowUp'].includes(e.key)){e.preventDefault();go(-1);}
});
document.getElementById('deck').addEventListener('click',()=>go(1));
update();
"""

# ── Slide renderers ───────────────────────────────────────────────────────────

def _e(s: str) -> str:
    return escape(str(s), quote=True)


def _render_title(s: dict) -> str:
    tag = _e(s.get("tag", "PRESENTATION"))
    title = _e(s.get("title", ""))
    subtitle = _e(s.get("subtitle", ""))
    sub_html = f'<p>{subtitle}</p>' if subtitle else ""
    return f"""<div class="slide s-title">
  <span class="tag">{tag}</span>
  <h1>{title}</h1>
  <div class="line"></div>
  {sub_html}
</div>"""


def _render_section(s: dict, idx: int) -> str:
    num = _e(s.get("number", f"{idx:02d}"))
    title = _e(s.get("title", ""))
    subtitle = _e(s.get("subtitle", ""))
    sub_html = f'<p>{subtitle}</p>' if subtitle else ""
    return f"""<div class="slide s-section">
  <span class="num">{num}</span>
  <h2>{title}</h2>
  {sub_html}
</div>"""


def _render_bullets(s: dict) -> str:
    title = _e(s.get("title", ""))
    subtitle = _e(s.get("subtitle", ""))
    sub_html = f'<p>{subtitle}</p>' if subtitle else ""
    items = "".join(f"<li>{_e(b)}</li>" for b in s.get("bullets", []))
    return f"""<div class="slide s-bullets">
  <div class="slide-hdr"><h2>{title}</h2>{sub_html}</div>
  <ul class="bullets">{items}</ul>
</div>"""


def _render_two_col(s: dict) -> str:
    title = _e(s.get("title", ""))
    ll = _e(s.get("left_label", ""))
    rl = _e(s.get("right_label", ""))
    li = "".join(f'<div class="col-item">{_e(x)}</div>' for x in s.get("left_items", []))
    ri = "".join(f'<div class="col-item">{_e(x)}</div>' for x in s.get("right_items", []))
    return f"""<div class="slide s-two-col">
  <div class="slide-hdr"><h2>{title}</h2></div>
  <div class="cols">
    <div><div class="col-label">{ll}</div><div class="col-items">{li}</div></div>
    <div><div class="col-label">{rl}</div><div class="col-items">{ri}</div></div>
  </div>
</div>"""


def _render_quote(s: dict) -> str:
    quote = _e(s.get("quote", ""))
    author = _e(s.get("author", ""))
    cite_html = f"<cite>— {author}</cite>" if author else ""
    return f"""<div class="slide s-quote">
  <blockquote>{quote}{cite_html}</blockquote>
</div>"""


def _render_end(s: dict) -> str:
    title = _e(s.get("title", "谢谢"))
    subtitle = _e(s.get("subtitle", "Q & A"))
    return f"""<div class="slide s-end">
  <h2>{title}</h2>
  <p>{subtitle}</p>
  <div class="dot"></div>
</div>"""


_RENDERERS = {
    "title":   _render_title,
    "section": _render_section,
    "bullets": _render_bullets,
    "two_col": _render_two_col,
    "quote":   _render_quote,
    "end":     _render_end,
}

_SECTION_IDX = 0


def _render_slide(s: dict, section_count: list) -> str:
    t = s.get("type", "bullets")
    if t == "section":
        section_count[0] += 1
        return _render_section(s, section_count[0])
    fn = _RENDERERS.get(t, _render_bullets)
    if t == "section":
        return fn(s, section_count[0])
    return fn(s)


def _build_html(outline: dict) -> str:
    theme_name = outline.get("theme", "dark")
    theme = _THEMES.get(theme_name, _THEMES["dark"])
    title = escape(outline.get("title", "Presentation"))

    css = _CSS
    for k, v in theme.items():
        css = css.replace(f"{{{k}}}", v)

    section_count = [0]
    slides_html = "\n".join(_render_slide(s, section_count) for s in outline.get("slides", []))

    return f"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title>
<style>{css}</style>
</head>
<body>
<div class="deck" id="deck">{slides_html}</div>
<div class="nav">
  <button id="prev">← 上一页</button>
  <span class="counter" id="ctr"></span>
  <button id="next">下一页 →</button>
</div>
<div class="progress-wrap"><div class="progress-bar" id="pb"></div></div>
<script>{_JS}</script>
</body>
</html>"""


# ── Tool ─────────────────────────────────────────────────────────────────────

class HtmlPptTool(BaseTool):
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="html_ppt_builder",
            description=(
                "Generate a self-contained HTML presentation from a JSON outline. "
                "Returns a download link the user can open in any browser."
            ),
            parameters=[
                ToolParameter(
                    name="outline",
                    type="string",
                    description=(
                        "JSON string with keys: title, theme (dark|light|minimal), slides[]. "
                        "Each slide has: type (title|section|bullets|two_col|quote|end) and type-specific fields."
                    ),
                ),
            ],
        )

    async def execute(self, **kwargs: Any) -> str:
        raw: str = kwargs.get("outline", "")
        try:
            outline: dict = json.loads(raw)
        except json.JSONDecodeError as exc:
            return f"Error: invalid JSON — {exc}"

        if not outline.get("slides"):
            return "Error: outline must contain at least one slide."

        try:
            html = _build_html(outline)
        except Exception as exc:
            logger.exception("html_ppt_builder render error")
            return f"Error generating HTML: {exc}"

        title_slug = outline.get("title", "presentation")[:30].replace(" ", "_")
        filename = f"{title_slug}.html"
        file_id, token = file_store.save(
            filename=filename,
            data=html.encode("utf-8"),
            content_type="text/html; charset=utf-8",
        )

        logger.info("html_ppt_builder: saved %s (%d bytes)", filename, len(html))
        return (
            f"[📊 打开 / 下载 {filename}](/api/files/{file_id}/{filename}?t={token})\n\n"
            f"在浏览器中打开，用**方向键**或**点击**翻页，支持全屏（F11）。"
        )
