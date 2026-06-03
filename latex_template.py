r"""
latex_template.py — drop-in replacement for docx_template.py that emits
LuaLaTeX (.tex) instead of .docx.

Mirrors the docx_template API exactly (same function names, same args),
so any existing generate_xxx.py can switch backends with a one-line
import change:

    # before
    from docx_template import new_doc, add_title_page, ..., save
    save(doc, '/path/to/out.docx')

    # after
    from latex_template import new_doc, add_title_page, ..., save
    save(doc, '/path/to/out.tex')

Compile the resulting .tex with LuaLaTeX (TeX Live ships with it):

    cd /path/to/output_dir
    latexmk -lualatex .\out.tex     # latexmk handles multi-pass automatically

Or use the convenience function:

    from latex_template import compile_to_pdf
    compile_to_pdf('/path/to/out.tex')

Why LuaLaTeX, not XeLaTeX: LuaLaTeX with the HarfBuzz renderer is the only
mainstream TeX engine that can read OpenType color glyph tables (COLR/CPAL,
sbix). Pre-installed system emoji fonts (Segoe UI Emoji on Windows, Apple
Color Emoji on macOS, Noto Color Emoji on Linux) all use those tables, so
LuaLaTeX is the path to true color emoji in our docs. XeLaTeX would render
the same emoji as flat monochrome silhouettes.

Visual style matches docx_template:
  - Latin font: Calibri
  - CJK font: 微软雅黑 (Microsoft YaHei)
  - Code font: Consolas
  - Color emoji font: Segoe UI Emoji (Windows default)
  - Heading color: dark blue #1A365D
  - Heading sizes: H1=18pt, H2=15pt, H3=12.5pt, H4=11.5pt
  - Body 11pt, line-spacing 1.5
  - Table header bg = HeadingBlue, white text
  - `**bold**` markdown inside add_para / add_bullet / add_table cells
    is converted to \textbf{...} automatically.
  - Emoji codepoints (🔵 ✅ ⭐ ❓ etc.) anywhere in body text are auto-wrapped
    with the {\colorEmoji ...} font face so they render in color.

Requires:
  - LuaLaTeX (TeX Live, MacTeX, MiKTeX — all bundle it by default)
  - Packages: ctex, fontspec, xcolor, titlesec, listings, tabularx,
    booktabs, colortbl, enumitem, fancyvrb, hyperref, geometry
    (all in standard TeX Live install). ctex auto-loads luatexja-fontspec
    on LuaLaTeX, so xeCJK is intentionally NOT loaded.
  - System fonts: Calibri, 微软雅黑, Consolas, Segoe UI Emoji (all native
    on Windows). macOS substitutes: Calibri/Consolas via Office, Apple Color
    Emoji built-in. Linux substitutes: Carlito + Noto Sans CJK SC + JetBrains
    Mono + Noto Color Emoji.
"""

import os
import re
import subprocess
from dataclasses import dataclass, field
from typing import List, Optional


# ============================================================
# Style constants — change here to retheme everything
# ============================================================

FONT_LATIN = 'Calibri'
FONT_CJK = 'Microsoft YaHei'
FONT_CODE = 'Consolas'

# Color hex values (no leading #)
COLOR_HEADING = '1A365D'        # dark blue, used for H1-H4 + table header bg
COLOR_SUBTITLE = '555577'       # gray-blue, title page subtitle
COLOR_META = '666666'           # mid gray, title page meta lines (date / author)
COLOR_TABLE_HEADER_BG = '1A365D'  # match headings
COLOR_TABLE_HEADER_TEXT = 'FFFFFF'

# Code block — GitHub-light-mode palette. These are the colors GitHub uses
# in its rendered code blocks; they're well-tested for print readability
# and match what most readers see day-to-day in repo browsing.
COLOR_CODE_BG = 'F6F8FA'        # GitHub's code-block background (very light blue-gray)
COLOR_CODE_TEXT = '24292E'      # GitHub's near-black body text
COLOR_CODE_KEYWORD = 'D73A49'   # GitHub's red, used for language keywords
COLOR_CODE_STRING = '032F62'    # GitHub's deep blue, used for string literals
COLOR_CODE_COMMENT = '6A737D'   # GitHub's gray, used for comments

# Heading sizes — in pt; line-spacing factor 1.3 applied via titlesec
HEADING_SIZES = {1: 18, 2: 15, 3: 12.5, 4: 11.5}
BODY_FONT_SIZE = 11

# Spacing (in pt unless noted)
HEADING_SPACE_BEFORE = 18
HEADING_SPACE_AFTER = 10
BODY_SPACE_AFTER = 8
BODY_LINE_SPACING = 1.5
BULLET_SPACE_AFTER = 4
BULLET_LINE_SPACING = 1.4
CODE_LINE_SPACING = 1.25
CODE_FONT_SIZE = 9.5


# ============================================================
# Internal: LaTeX special-char escape + inline bold parsing
# ============================================================

_LATEX_ESCAPES = {
    '\\': r'\textbackslash{}',
    '&':  r'\&',
    '%':  r'\%',
    '$':  r'\$',
    '#':  r'\#',
    '_':  r'\_',
    '{':  r'\{',
    '}':  r'\}',
    '~':  r'\textasciitilde{}',
    '^':  r'\textasciicircum{}',
    '<':  r'\textless{}',
    '>':  r'\textgreater{}',
}


# Emoji codepoint ranges. Anything matching this gets wrapped in
# {\colorEmoji ...} so LuaLaTeX uses the color-emoji font face instead of
# falling back to a CJK/Latin font that doesn't have the glyph.
# Covers:
#   U+1F300–U+1FAFF  — main emoji blocks (Misc Symbols & Pictographs,
#                      Emoticons, Transport, Symbols Extended-A, etc.)
#   U+2600–U+27BF    — older Misc Symbols + Dingbats (✅ ❓ ☀ ⚠ etc.)
#   U+2B00–U+2BFF    — Misc Symbols and Arrows (⭐ U+2B50, ⬛ ⬜)
#   U+1F1E6–U+1F1FF  — regional indicator pairs (flags)
# We intentionally don't strip variation selectors (U+FE0F) or ZWJ
# (U+200D); HarfBuzz handles those inside the font shaping pass.
_EMOJI_RANGES = re.compile(
    r'([\U0001F300-\U0001FAFF'
    r'\U00002600-\U000027BF'
    r'\U00002B00-\U00002BFF'
    r'\U0001F1E6-\U0001F1FF]+)'
)


def _wrap_emoji(text: str) -> str:
    r"""Wrap any run of emoji codepoints with the \colorEmoji font face.

    Runs (not single chars) are wrapped together so adjacent emoji share a
    font group — important for ZWJ sequences and flag-pair emoji which
    HarfBuzz needs to see contiguously.
    """
    return _EMOJI_RANGES.sub(r'{\\colorEmoji \1}', text)


def _escape_latex(text: str) -> str:
    """Escape LaTeX-special characters, then wrap emoji codepoints.

    NOTE: emoji wrap MUST run AFTER escape, because wrap inserts `{` `}`
    (LaTeX-special) and we don't want those to be re-escaped.
    """
    # Backslash first — otherwise we'd double-escape the backslashes in
    # the replacements themselves.
    out = []
    for ch in text:
        out.append(_LATEX_ESCAPES.get(ch, ch))
    return _wrap_emoji(''.join(out))


def _render_inline(text: str) -> str:
    """Convert a plain string with **bold** markers to a LaTeX fragment.

    Pipeline:
      1. Split on **...** while preserving the markers' bold/non-bold
         alternation pattern.
      2. Escape each segment for LaTeX.
      3. Wrap odd-index (bold) segments in \textbf{...}.
    """
    parts = re.split(r'\*\*(.+?)\*\*', text)
    rendered = []
    for i, part in enumerate(parts):
        if not part:
            continue
        escaped = _escape_latex(part)
        if i % 2 == 1:
            rendered.append(r'\textbf{' + escaped + '}')
        else:
            rendered.append(escaped)
    return ''.join(rendered)


def _render_cell(text: str) -> str:
    r"""Render a table cell: inline markdown + intra-token break opportunities.

    TeX never breaks a line at "/", so a slash-joined token like
    "256/512/1024/1536" or "int8/binary" is treated as one unbreakable word.
    In a narrow column that word can't fit, so it juts out past the cell's
    right edge and collides with the next column (the classic
    "256/512/1024/1536int8/binary" run-together). Inserting \allowbreak after
    each slash lets such tokens wrap inside their own cell. (Hyphens, e.g.
    "text-embedding-3-large", are already TeX break points, so they need no
    help — only the ragged-right column type to stop the stretch.)
    """
    return _render_inline(text).replace('/', r'/\allowbreak{}')


# ============================================================
# Document object — accumulates body content + title-page metadata
# ============================================================

@dataclass
class Document:
    """Simple LaTeX document container.

    Mirrors the role of python-docx's Document, but instead of a
    structured XML tree it just holds a list of LaTeX-source chunks
    that get concatenated at save time.
    """
    body_chunks: List[str] = field(default_factory=list)
    title_page: Optional[dict] = None
    has_toc: bool = False
    extra_preamble: List[str] = field(default_factory=list)


# ============================================================
# Public API — same signatures as docx_template
# ============================================================

def new_doc() -> Document:
    """Create an empty Document. Style applied at save() time via preamble."""
    return Document()


def add_title_page(doc: Document, title: str, subtitle: Optional[str] = None,
                   meta_lines: Optional[List[str]] = None) -> None:
    """Set up the title page.

    Stored on the doc object and emitted at save time, in the standard
    "vertical center, large title, subtitle below, meta lines underneath"
    layout that matches docx_template's title-page style.
    """
    doc.title_page = {
        'title': title,
        'subtitle': subtitle,
        'meta_lines': list(meta_lines or []),
    }


def add_toc(doc: Document, toc_heading: str = '目录') -> None:
    r"""Mark that a table-of-contents page should be inserted.

    LuaLaTeX needs two compile passes for the TOC to populate. Use
    compile_to_pdf() or run `latexmk -lualatex .\<file>.tex` (latexmk
    handles multi-pass automatically).
    """
    doc.has_toc = True
    # toc_heading is set globally via \renewcommand in the preamble, but
    # we capture it here in case anyone wants to override it per-doc.
    doc.extra_preamble.append(
        r'\renewcommand{\contentsname}{' + _escape_latex(toc_heading) + '}'
    )


def add_heading(doc: Document, text: str, level: int = 1,
                page_break_before: Optional[bool] = None) -> None:
    """Add a numbered section heading at the given level (1-4).

    By default H1 starts a new page (matches docx_template behaviour);
    pass page_break_before=False to suppress.
    """
    level = max(1, min(level, 4))

    if page_break_before is None:
        page_break_before = (level == 1)
    if page_break_before:
        doc.body_chunks.append(r'\clearpage')

    cmd = {1: 'section', 2: 'subsection', 3: 'subsubsection',
           4: 'paragraph'}[level]
    # All levels render with our custom dark-blue style; titlesec handles
    # the visual differentiation by font size (set in the preamble).
    doc.body_chunks.append(r'\%s{%s}' % (cmd, _render_inline(text)))


def add_para(doc: Document, text: str, bold: bool = False,
             italic: bool = False) -> None:
    """Add a body paragraph.

    If bold=True the entire paragraph is bold, AND any inline ** markers
    are stripped (matching docx_template wrapper semantics — no double
    emphasis).
    """
    if bold:
        # Strip ** markers when whole paragraph is already bold
        text = text.replace('**', '')
        body = _escape_latex(text)
        body = r'\textbf{' + body + '}'
    else:
        body = _render_inline(text)

    if italic:
        body = r'\textit{' + body + '}'

    # `\par` ensures explicit paragraph break even when called between
    # other LaTeX environments.
    doc.body_chunks.append(body + r'\par')


def add_bullet(doc: Document, text: str, level: int = 0,
               bold_prefix: Optional[str] = None) -> None:
    """Add a bullet item.

    A run of consecutive add_bullet calls is collapsed into a single
    `itemize` environment at save time (we don't want to start/end one
    per item — that would break LaTeX). The collapsing happens in
    _flush_pending_bullets, called by save() and by any non-bullet
    helper that comes after a bullet.
    """
    parts = []
    if bold_prefix:
        parts.append(r'\textbf{' + _escape_latex(bold_prefix) + '}')
        # Match docx_template behaviour where there's no extra whitespace
        # between prefix and rest — caller decides if they want a space.
    parts.append(_render_inline(text))
    body = ''.join(parts)

    # Tag this chunk so save() can group it with adjacent bullets.
    # Format: ['__BULLET__', level, body]
    doc.body_chunks.append(('__BULLET__', level, body))


def add_code(doc: Document, text: str, language: Optional[str] = None) -> None:
    """Add a code block in modern GitHub-light style.

    Uses the `listings` package — currently the most common code-block
    engine in LaTeX tech docs (vs. older `verbatim` / `fancyvrb`, vs.
    syntax-highlighter `minted` which requires --shell-escape and a
    Pygments install).

    Visual style: light blue-gray background (#F6F8FA), no border,
    monospace, comfortable padding. Matches the look of code blocks
    rendered on GitHub / VS Code light theme.

    Args:
        text: Code content. ALL characters (`\\`, `{`, `}`, `&`, `%`,
              etc.) render literally — no escaping needed. The only
              forbidden substring is the closing tag `\\end{lstlisting}`,
              which is a hard limitation of `listings`.
        language: Optional listings language identifier for syntax
              highlighting. Common values:
                  'bash', 'sh'         — shell scripts / commands
                  'python'             — Python
                  'TypeScript', 'Java' — built-in to listings
                  'json'               — defined in our preamble below
                  'yaml'               — basic, no built-in keywords
              Pass None (default) for plain monospace with no token
              coloring — best for mixed-language snippets, file dumps,
              error logs, ASCII diagrams, anything where syntax color
              would be wrong or distracting.
    """
    lang_attr = f'[language={language}]' if language else ''
    doc.body_chunks.append(
        r'\begin{lstlisting}' + lang_attr + '\n' +
        text + '\n' +
        r'\end{lstlisting}'
    )


def add_table(doc: Document, rows: List[List[str]],
              col_widths: Optional[List[float]] = None) -> None:
    """Add a table with a styled header row.

    First row is the header (dark blue background, white bold text). Data
    rows alternate as plain text. Cells support **inline bold** markdown.

    col_widths (in inches) is optional; if omitted, columns auto-size
    via tabularx with all columns flexible.
    """
    if not rows:
        return
    n_cols = len(rows[0])

    if col_widths and len(col_widths) == n_cols:
        # Fixed widths → longtable (page-breakable; centers itself by default
        # via \LTleft/\LTright = \fill). P{w} = ragged-right fixed width.
        col_spec = '|' + '|'.join(
            f'P{{{w:.2f}in}}' for w in col_widths
        ) + '|'
        env_open = r'\begin{longtable}{' + col_spec + '}'
        env_close = r'\end{longtable}'
    else:
        # Auto-flex → xltabular (longtable + tabularx): Y columns fill text
        # width (ragged-right) AND the table breaks across pages.
        col_spec = '|' + '|'.join(['Y'] * n_cols) + '|'
        env_open = r'\begin{xltabular}{\textwidth}{' + col_spec + '}'
        env_close = r'\end{xltabular}'

    lines = []
    # \par\bigskip + \noindent gives the table vertical breathing room and
    # defends against leftover first-line indent. We deliberately do NOT wrap
    # it in a `center` environment: longtable/xltabular must sit directly in
    # the main vertical list to break across pages (a center box would make
    # it unbreakable again, reintroducing the overflow + blank-page bug).
    # Both environments center themselves by default.
    lines.append(r'\par\bigskip')
    lines.append(r'\noindent')
    lines.append(env_open)
    lines.append(r'\hline')

    # Header row — dark blue bg + white bold text.
    header = rows[0]
    header_cells = ' & '.join(
        r'\textbf{\textcolor[HTML]{' + COLOR_TABLE_HEADER_TEXT + '}{' +
        _render_cell(cell) + '}}'
        for cell in header
    )
    lines.append(
        r'\rowcolor[HTML]{' + COLOR_TABLE_HEADER_BG + '} ' +
        header_cells + r' \\'
    )
    lines.append(r'\hline')
    # \endhead → everything above repeats at the top of each page the table
    # spills onto, so a multi-page table keeps its header on every page.
    lines.append(r'\endhead')

    # Data rows
    for row in rows[1:]:
        # Pad short rows so column alignment doesn't break the build
        padded = row + [''] * (n_cols - len(row))
        data_cells = ' & '.join(_render_cell(c) for c in padded[:n_cols])
        lines.append(data_cells + r' \\')
        lines.append(r'\hline')

    lines.append(env_close)
    lines.append(r'\bigskip')
    doc.body_chunks.append('\n'.join(lines))


def add_image(doc: Document, filename: str, caption: str,
              width: str = '0.85', max_height: str = '0.55') -> None:
    """Add a centered figure with caption.

    Graceful degradation: if the file does not exist at compile time, LaTeX
    emits a placeholder box (the caption still shows) instead of crashing —
    so you can write the .tex first and add images later, and the build
    survives missing assets.

    Args:
        filename: image path relative to the .tex file's directory.
            For a project layout like `project/foo.tex` + `project/images/bar.png`,
            pass `'images/bar.png'`. graphicx resolves this via the standard
            graphics search path.
        caption: caption text. LaTeX special chars (`& % $ # _ { } ~ ^`) are
            escaped automatically, and `**inline bold**` markdown works
            (same convention as add_para / add_bullet / add_table cells).
        width: width as a fraction of `\\textwidth`, given as a string.
            Default `'0.85'` gives a comfortable centred figure.
        max_height: max height as a fraction of `\\textheight`, as a string.
            Default `'0.55'` prevents tall portrait images (mobile screenshots,
            App Store screenshots, etc.) from overflowing the page.
    """
    caption_tex = _render_inline(caption)
    block = (
        r'\begin{figure}[H]' + '\n'
        r'\centering' + '\n'
        r'\IfFileExists{' + filename + '}{'
        r'\includegraphics[width=' + width + r'\textwidth,'
        r'keepaspectratio,max height=' + max_height + r'\textheight]{' + filename + '}'
        r'}{'
        r'\imgplaceholder{' + filename + '}{' + caption_tex + '}'
        r'}' + '\n'
        r'\caption{' + caption_tex + '}' + '\n'
        r'\end{figure}'
    )
    doc.body_chunks.append(block)


# Public alias for the inline-text escape + bold-marker handler.
# Useful when writing project-specific custom helpers that emit raw LaTeX —
# always run user-provided strings through this before splicing into LaTeX,
# otherwise stray "&" / "_" / "%" will break compilation.
escape_inline = _render_inline


# ============================================================
# Internal: assemble preamble + body and write .tex
# ============================================================

def _build_preamble(doc: Document) -> str:
    """Construct the LaTeX preamble — packages, fonts, color, heading style."""
    return r'''\documentclass[11pt,a4paper]{ctexart}

% --- Geometry ---
\usepackage[margin=1in]{geometry}

% --- Fonts (LuaLaTeX) ---
% ctex auto-loads luatexja-fontspec on LuaLaTeX, which provides the same
% \setCJKmainfont / \setCJKmonofont API that xeCJK does on XeLaTeX — so
% we don't load xeCJK explicitly. (Loading both would conflict.)
\usepackage{fontspec}
\setmainfont{''' + FONT_LATIN + r'''}
\setCJKmainfont{''' + FONT_CJK + r'''}
\setmonofont{''' + FONT_CODE + r'''}
% CJK in code blocks (e.g. Chinese comments) — use the same CJK family
% so character spacing stays consistent with surrounding mono text.
\setCJKmonofont{''' + FONT_CJK + r'''}

% --- Color emoji (LuaLaTeX + HarfBuzz) ---
% Renderer=HarfBuzz is required for LuaLaTeX to read color glyph tables
% (COLR/CPAL, sbix) — without it, emoji render as monochrome silhouettes.
% Swap "Segoe UI Emoji" to "Apple Color Emoji" on macOS or "Noto Color
% Emoji" on Linux if the user is compiling outside Windows.
\newfontfamily\colorEmoji{Segoe UI Emoji}[Renderer=HarfBuzz]

% --- Color ---
\usepackage[table]{xcolor}
\definecolor{HeadingBlue}{HTML}{''' + COLOR_HEADING + r'''}
\definecolor{Subtitle}{HTML}{''' + COLOR_SUBTITLE + r'''}
\definecolor{Meta}{HTML}{''' + COLOR_META + r'''}

% --- Headings: dark-blue bold, custom sizes, custom spacing ---
\usepackage{titlesec}
\titleformat{\section}
  {\color{HeadingBlue}\bfseries\fontsize{''' + str(HEADING_SIZES[1]) + r'''}{''' + str(HEADING_SIZES[1] * 1.3) + r'''}\selectfont}
  {\thesection}{1em}{}
\titleformat{\subsection}
  {\color{HeadingBlue}\bfseries\fontsize{''' + str(HEADING_SIZES[2]) + r'''}{''' + str(HEADING_SIZES[2] * 1.3) + r'''}\selectfont}
  {\thesubsection}{1em}{}
\titleformat{\subsubsection}
  {\color{HeadingBlue}\bfseries\fontsize{''' + str(HEADING_SIZES[3]) + r'''}{''' + str(HEADING_SIZES[3] * 1.3) + r'''}\selectfont}
  {\thesubsubsection}{1em}{}
\titleformat{\paragraph}[hang]
  {\color{HeadingBlue}\bfseries\fontsize{''' + str(HEADING_SIZES[4]) + r'''}{''' + str(HEADING_SIZES[4] * 1.3) + r'''}\selectfont}
  {}{0pt}{}

\titlespacing*{\section}{0pt}{''' + str(HEADING_SPACE_BEFORE) + r'''pt}{''' + str(HEADING_SPACE_AFTER) + r'''pt}
\titlespacing*{\subsection}{0pt}{''' + str(HEADING_SPACE_BEFORE) + r'''pt}{''' + str(HEADING_SPACE_AFTER) + r'''pt}
\titlespacing*{\subsubsection}{0pt}{''' + str(HEADING_SPACE_BEFORE) + r'''pt}{''' + str(HEADING_SPACE_AFTER) + r'''pt}

% --- Body line spacing ---
\usepackage{setspace}
\setstretch{''' + str(BODY_LINE_SPACING) + r'''}

% --- Paragraph style: Western tech-doc convention ---
% No first-line indent; visual paragraph break comes from \parskip.
% (ctexart's default is Chinese-book-style 2-char first-line indent,
% which in code-heavy tech docs reads as inconsistent — first paragraph
% after a heading is flush-left, subsequent ones are indented.)
\setlength{\parindent}{0pt}
\setlength{\parskip}{''' + str(BODY_SPACE_AFTER) + r'''pt}

% --- Bullets (enumitem for tight list spacing) ---
\usepackage{enumitem}
\setlist[itemize]{itemsep=''' + str(BULLET_SPACE_AFTER) + r'''pt,topsep=4pt,parsep=0pt,partopsep=0pt}

% --- Code blocks: GitHub-light-mode style via the `listings` package ---
% (Currently the most common modern setup for code in LaTeX tech docs:
% pure-LaTeX, no --shell-escape needed, optional per-language syntax
% highlighting. For heavier syntax highlighting needs, consider switching
% to `minted` — same look, better tokenization, but external Python deps.)
\usepackage{listings}
\definecolor{CodeBg}{HTML}{''' + COLOR_CODE_BG + r'''}
\definecolor{CodeText}{HTML}{''' + COLOR_CODE_TEXT + r'''}
\definecolor{CodeKeyword}{HTML}{''' + COLOR_CODE_KEYWORD + r'''}
\definecolor{CodeString}{HTML}{''' + COLOR_CODE_STRING + r'''}
\definecolor{CodeComment}{HTML}{''' + COLOR_CODE_COMMENT + r'''}

% Define a few language modes that listings doesn't ship with by default
% but show up often in tech docs.
\lstdefinelanguage{json}{
    morestring=[b]",
    morecomment=[l]{//},
    morecomment=[s]{/*}{*/},
    sensitive=true,
    literate=
        *{0}{{{\color{CodeString}0}}}{1}
         {1}{{{\color{CodeString}1}}}{1}
         {2}{{{\color{CodeString}2}}}{1}
         {3}{{{\color{CodeString}3}}}{1}
         {4}{{{\color{CodeString}4}}}{1}
         {5}{{{\color{CodeString}5}}}{1}
         {6}{{{\color{CodeString}6}}}{1}
         {7}{{{\color{CodeString}7}}}{1}
         {8}{{{\color{CodeString}8}}}{1}
         {9}{{{\color{CodeString}9}}}{1},
}

\lstdefinelanguage{TypeScript}{
    morekeywords={async, await, break, case, catch, class, const, continue,
        debugger, default, delete, do, else, enum, export, extends, false,
        finally, for, from, function, if, implements, import, in, instanceof,
        interface, let, new, null, of, private, protected, public, return,
        static, super, switch, this, throw, true, try, type, typeof, var,
        void, while, with, yield},
    morestring=[b]',
    morestring=[b]",
    morestring=[b]`,
    morecomment=[l]{//},
    morecomment=[s]{/*}{*/},
    sensitive=true,
}

% Default style — plain monospace by default, color tokens when language
% is specified.
\lstdefinestyle{techdoc}{
    backgroundcolor=\color{CodeBg},
    basicstyle=\fontsize{''' + str(CODE_FONT_SIZE) + r'''}{''' + str(CODE_FONT_SIZE * CODE_LINE_SPACING) + r'''}\ttfamily\color{CodeText},
    keywordstyle=\color{CodeKeyword}\bfseries,
    stringstyle=\color{CodeString},
    commentstyle=\color{CodeComment}\itshape,
    numberstyle=\tiny\color{CodeComment},
    numbers=none,
    frame=none,
    framesep=10pt,
    xleftmargin=14pt,
    xrightmargin=14pt,
    aboveskip=12pt,
    belowskip=12pt,
    breaklines=true,
    breakatwhitespace=false,
    showstringspaces=false,
    columns=fullflexible,
    keepspaces=true,
    upquote=true,
    extendedchars=true,
    captionpos=b,
}
\lstset{style=techdoc}

% --- Tables ---
\usepackage{array}      % \newcolumntype, \arraybackslash for ragged cells
\usepackage{tabularx}
\usepackage{booktabs}
% xltabular = longtable + tabularx: page-breakable tables that keep the
% auto-flex X columns and repeat the header row on each page. Without this,
% a tabularx/tabular taller than the remaining page is a single unbreakable
% box — it gets shoved whole onto the next page (leaving a blank gap) and
% overflows the bottom margin if it's taller than a full page.
\usepackage{xltabular}

% Ragged-right cell variants. Plain p{} and X columns are FULLY JUSTIFIED,
% which in narrow columns stretches the white space to fill the line: Latin
% words spread apart ("OpenAI      text-...") and — worse with CJK — every
% character gets pushed apart ("多 语 言 最 强"). Left-aligning the text
% (ragged-right) removes that stretch entirely. \arraybackslash restores \\
% as the row terminator, which the \raggedright redefinition would otherwise
% clobber. Y = ragged flexible (replaces X); P{w} = ragged fixed-width.
\newcolumntype{Y}{>{\raggedright\arraybackslash}X}
\newcolumntype{P}[1]{>{\raggedright\arraybackslash}p{#1}}

% --- Hyperlinks (TOC) ---
\usepackage[hidelinks]{hyperref}

% --- TOC heading also uses our dark-blue color ---
\usepackage{tocloft}
\renewcommand{\cfttoctitlefont}{\color{HeadingBlue}\bfseries\Large}

% --- Suppress page numbers on title page ---
\usepackage{titling}

% --- Images ---
% graphicx for \includegraphics; float for [H] (here-and-nowhere-else placement);
% adjustbox lets \includegraphics accept "max height=..." keys.
\usepackage{graphicx}
\usepackage{float}
\usepackage[export]{adjustbox}

% --- Long URLs / unbreakable Latin words: give LaTeX stretch budget to avoid
%     Overfull \hbox warnings in the references section. Slight extra word
%     spacing is preferable to ragged-right-with-overrun.
\setlength{\emergencystretch}{3em}

% --- Image placeholder for missing files (used by add_image's \IfFileExists fallback).
%     \detokenize on the filename arg prevents underscores from triggering math mode
%     inside the \textit{} (which would crash compile with "Missing $ inserted").
%     \par + \vspace inside parbox is more stable than \\[em].
\newcommand{\imgplaceholder}[2]{%
  \fbox{\parbox{0.75\textwidth}{\centering%
    \vspace{1.5em}%
    {\itshape [\,image not provided:\ \texttt{\detokenize{#1}}\,]}\par%
    \vspace{0.6em}%
    {\small #2}%
    \vspace{1.5em}%
  }}%
}

''' + '\n'.join(doc.extra_preamble)


def _emit_title_page(tp: dict) -> str:
    """Build the title page LaTeX block from add_title_page args."""
    title = _escape_latex(tp['title'])
    subtitle = tp.get('subtitle')
    meta_lines = tp.get('meta_lines') or []

    # Use a vertically centered titlepage env
    parts = []
    parts.append(r'\begin{titlepage}')
    parts.append(r'\centering')
    parts.append(r'\vspace*{4cm}')
    parts.append(
        r'{\color{HeadingBlue}\bfseries\fontsize{28}{34}\selectfont ' +
        title + r'}\par'
    )
    parts.append(r'\vspace{1cm}')
    if subtitle:
        parts.append(
            r'{\color{Subtitle}\fontsize{18}{22}\selectfont ' +
            _escape_latex(subtitle) + r'}\par'
        )
        parts.append(r'\vspace{2cm}')
    for line in meta_lines:
        parts.append(
            r'{\color{Meta}\fontsize{11}{14}\selectfont ' +
            _escape_latex(line) + r'}\par'
        )
        parts.append(r'\vspace{0.3cm}')
    parts.append(r'\end{titlepage}')
    return '\n'.join(parts)


def _emit_body(doc: Document) -> str:
    """Concatenate body chunks, collapsing consecutive bullets into itemize envs."""
    out = []
    pending_bullets: List[tuple] = []  # list of (level, body) tuples

    def flush_bullets():
        if not pending_bullets:
            return
        # Group by level — when level increases we open a nested itemize,
        # when it decreases we close back. Simple state machine.
        out.append(r'\begin{itemize}')
        current_level = 0
        for lvl, body in pending_bullets:
            while lvl > current_level:
                out.append(r'\begin{itemize}')
                current_level += 1
            while lvl < current_level:
                out.append(r'\end{itemize}')
                current_level -= 1
            out.append(r'\item ' + body)
        while current_level > 0:
            out.append(r'\end{itemize}')
            current_level -= 1
        out.append(r'\end{itemize}')
        pending_bullets.clear()

    for chunk in doc.body_chunks:
        if isinstance(chunk, tuple) and chunk[0] == '__BULLET__':
            _, level, body = chunk
            pending_bullets.append((level, body))
        else:
            flush_bullets()
            out.append(chunk)
    flush_bullets()  # in case bullets are the very last thing

    return '\n\n'.join(out)


def save(doc: Document, path: str) -> None:
    """Render the document to a .tex file at the given path."""
    if not path.endswith('.tex'):
        # Encourage the .tex extension but don't refuse — user might
        # want .latex or no extension for some pipeline.
        pass

    pieces = [_build_preamble(doc)]
    pieces.append(r'\begin{document}')
    if doc.title_page:
        pieces.append(_emit_title_page(doc.title_page))
    if doc.has_toc:
        # Wrap \tableofcontents in a group that locally resets \parskip.
        # The global 8pt parskip (Western paragraph spacing) makes TOC
        # entries look uncomfortably far apart; inside the TOC we want
        # them tight. The {} group scopes the change so body paragraphs
        # afterward resume the global 8pt.
        pieces.append(r'{\setlength{\parskip}{0pt}\tableofcontents}')
        pieces.append(r'\clearpage')
    pieces.append(_emit_body(doc))
    pieces.append(r'\end{document}')

    content = '\n\n'.join(pieces)
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f'Saved: {path}')


# ============================================================
# Convenience: compile .tex to PDF via XeLaTeX
# ============================================================

def compile_to_pdf(tex_path: str, runs: int = 2) -> str:
    """Run lualatex on a .tex file (twice by default, for TOC + cross-refs).

    Returns the resulting .pdf path on success; raises RuntimeError on
    compile failure (with the lualatex log tail in the exception message).
    """
    if not os.path.isfile(tex_path):
        raise FileNotFoundError(tex_path)
    work_dir = os.path.dirname(os.path.abspath(tex_path))
    base = os.path.splitext(os.path.basename(tex_path))[0]

    for i in range(runs):
        result = subprocess.run(
            ['lualatex', '-interaction=nonstopmode', '-halt-on-error',
             os.path.basename(tex_path)],
            cwd=work_dir,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            tail = '\n'.join((result.stdout or '').splitlines()[-30:])
            raise RuntimeError(
                f'lualatex failed on pass {i + 1}/{runs}:\n{tail}'
            )

    pdf_path = os.path.join(work_dir, base + '.pdf')
    print(f'Compiled: {pdf_path}')
    return pdf_path


# ============================================================
# Self-test — run this file directly to generate a sample doc
# ============================================================

if __name__ == '__main__':
    doc = new_doc()
    add_title_page(
        doc,
        title='示例文档',
        subtitle='演示 LaTeX 模板支持的所有元素',
        meta_lines=[
            '文档日期:2026 年 5 月 6 日',
            '适用范围:Bota 技术文档模板',
        ],
    )
    add_toc(doc)

    add_heading(doc, '引言', level=1)
    add_para(doc, '本示例演示了模板支持的所有元素:标题、副标题、正文、'
                  '**加粗**、斜体、列表、代码、表格。')

    add_heading(doc, '段落与列表', level=2)
    add_para(doc, '这是普通正文。')
    add_para(doc, '这是整段加粗正文。', bold=True)
    add_para(doc, '这是整段斜体正文。', italic=True)
    add_bullet(doc, '第一条要点')
    add_bullet(doc, '带 **inline 加粗** 的要点')
    add_bullet(doc, '带粗体前缀的要点,用于强调类别。', bold_prefix='要点 3:')

    add_heading(doc, '代码与表格', level=1)
    add_heading(doc, '代码块', level=2)

    add_para(doc, '不指定语言 — 纯等宽,适合 shell 命令、错误输出、ASCII 图等:')
    add_code(doc, 'aws --profile dev logs filter-log-events \\\n'
                  '    --log-group-name /eks/bota-api \\\n'
                  '    --filter-pattern "ERROR"')

    add_para(doc, 'Python(关键字加粗高亮):')
    add_code(doc,
        'def find_or_create_user(email: str) -> User:\n'
        '    # 看 DDB 里有没有这个人\n'
        '    existing = users_table.get_item(Key={"email": email})\n'
        '    if existing.get("Item"):\n'
        '        return User.from_dict(existing["Item"])\n'
        '    return _create_new_user(email)',
        language='python')

    add_para(doc, 'JSON(string / number / 关键字着色):')
    add_code(doc,
        '{\n'
        '  "user_pool_id": "us-west-2_pJr7fveBL",\n'
        '  "ttl_seconds": 3600,\n'
        '  "enabled": true\n'
        '}',
        language='json')

    add_para(doc, 'TypeScript / JavaScript(关键字 + 字符串 + 注释):')
    add_code(doc,
        "// list memberships for the calling user\n"
        "const memberships = await ddb.send(\n"
        "  new QueryCommand({\n"
        "    TableName: MEMBERSHIPS_TABLE,\n"
        "    KeyConditionExpression: 'cognitoSub = :sub',\n"
        "    ExpressionAttributeValues: { ':sub': cognitoSub },\n"
        "  })\n"
        ");",
        language='TypeScript')

    add_heading(doc, '表格', level=2)
    add_table(doc, [
        ['字段', '类型', '说明'],
        ['id', 'string', '记录的唯一标识'],
        ['createdAt', 'timestamp', '创建时间(UTC)'],
        ['status', 'enum', '**pending** / processing / done'],
    ])

    add_heading(doc, '图片', level=2)
    add_para(doc, '图片用 add_image 添加,缺图时自动渲染占位框(下方就是占位示范):')
    # Deliberately reference a non-existent file to exercise the placeholder branch.
    add_image(doc,
              'images/_does_not_exist.png',
              'caption 可以写 **inline 加粗**,LaTeX 特殊字符 (& % $ # _) 也会自动 escape。')

    add_heading(doc, '结语', level=1)
    add_para(doc, '这份模板涵盖了常见的技术文档元素。')

    save(doc, '_example_output.tex')
    # Uncomment to also compile to PDF (requires lualatex):
    # compile_to_pdf('_example_output.tex')
