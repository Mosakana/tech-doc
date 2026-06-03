---
description: Generate a Chinese-language Markdown technical document (Obsidian-friendly) from a topic — typically either a "踩坑记 / lessons-learned" (chronological debugging story with root cause + fixes attempted + final config) or a "学习材料 / study guide" (background → why-this-stack → key concepts → integration details). Use whenever the user asks to "写文档", "记录一下", "把这次的踩坑写下来", "整理成学习材料", or similar; also for vault maintenance like "刷新 reference / 检查 reference 有没有更新 / 更新 prd 快照". Output is Markdown into the Obsidian knowledge vault at $KNOWLEDGE_VAULT/. PDF, if wanted, is exported manually from Obsidian (File → Export to PDF). A legacy LaTeX (.tex) path is available only if explicitly requested.
allowed-tools: Bash Read Write Edit Grep Glob Agent
---

# tech-doc — generate a Chinese technical Markdown doc (Obsidian vault)

This skill produces a polished **Markdown** learning / debugging document, written
straight to disk (no generator script — Markdown needs no escaping layer), with
Obsidian-friendly frontmatter, callouts, mermaid diagrams, and `[[wikilinks]]`.

The output lives in the Obsidian knowledge vault at **`$KNOWLEDGE_VAULT/`**
(Windows `D:\Knowledge`). Markdown is the **source of truth** — it's searchable,
linkable, updatable, and machine-queryable (you can one day run RAG over your own
notes). **PDF is a derived artifact**, exported by hand from Obsidian when wanted — not the source.

> **Why Markdown, not LaTeX/PDF:** a knowledge base wants to be grep-able, linkable
> into a graph, editable-in-place (fix one note, not generate `v2.pdf`), and
> machine-indexable. PDF is frozen on all four. We keep PDF only as a final
> share/print export. A legacy LaTeX path still exists (see bottom) for when the
> user explicitly wants advanced typeset `.tex`/`.docx` output.

## Setup (per machine)

Two env vars configure this skill; the scripts read them and the docs reference them.

- **`KNOWLEDGE_VAULT`** — the Obsidian vault root (e.g. `/mnt/d/Knowledge` on WSL).
  Scripts default to `$KNOWLEDGE_VAULT`, then `~/Knowledge`.
- **`SKILL_PYTHON`** — a python with `python-docx` (only for the `.docx` migration helper;
  `pip install python-docx`). The index/link checkers run under plain `python3`.

**Set them where the agent's Bash tool will see them — that means `settings.json`'s `env`,
NOT just `~/.bashrc`** (a non-interactive shell hits `~/.bashrc`'s "if not interactive, return"
guard and never reaches the exports, so the vars come up empty). In `~/.claude/settings.json`:

```json
"env": { "KNOWLEDGE_VAULT": "/mnt/d/Knowledge", "SKILL_PYTHON": "/path/to/python" }
```

> [!IMPORTANT] How the agent must handle these vars (read before acting)
> - **Resolve once, up front:** run `echo "$KNOWLEDGE_VAULT"` and use the **concrete** result
>   (e.g. `/mnt/d/Knowledge`) for the rest of the task.
> - **Bash expands `$VARS`; Read / Write / Edit do NOT.** Those tools take a literal path — if you
>   pass `$KNOWLEDGE_VAULT/llm/foo.md` to Write you'll create a folder literally named
>   `$KNOWLEDGE_VAULT`. So in Read/Write/Edit always use the **resolved** path
>   (`/mnt/d/Knowledge/llm/foo.md`). In Bash you can use `$KNOWLEDGE_VAULT` directly.

- **Author** — generated docs' frontmatter `author:` should be the user's own name/email (templates
  show a `<Your Name>` placeholder). The agent uses the actual user identity from context.

## Workflow

### 0. Read the guides first (MANDATORY — before anything else)

**Before identifying the doc type, gathering material, or writing a line, read both:**

1. `${CLAUDE_SKILL_DIR}/FORMAT_GUIDE.md` — how a single `.md` doc must be written
   (frontmatter schema, headings without hand-numbering, callout types, mermaid
   conventions, tables, code fences, wikilinks, emoji policy, image-caption rule).
2. `${CLAUDE_SKILL_DIR}/VAULT_STRUCTURE.md` — where it goes (category folders,
   flat notes, `attachments/`, and the `reference/<project>/` rules for source docs).

Read them top to bottom with the Read tool. They encode rules easy to violate from
memory. If anything here conflicts with them, **the guides win**. The example
skeletons in `${CLAUDE_SKILL_DIR}/examples/` already follow them.

### 1. Identify the document type

Ask the user only if not already obvious from their request:

- **A. 踩坑记 (lessons-learned)** — chronological debugging story. Each problem
  numbered, failed fixes inline, root cause at the end of each chain, then a global
  lessons section + final landing config. Skeleton:
  `examples/lessons_learned_skeleton.md`.
- **B. 学习材料 (study guide)** — conceptual deep-dive. Background → selection
  rationale → key concepts → component-by-component → request flow → gotchas.
  Skeleton: `examples/study_guide_skeleton.md`.
- **C. 自由 / mixed** — rare; pick the closer skeleton and adapt.

### 2. Gather material

**For 踩坑记 (A):**
- Re-read the current conversation for the timeline: what broke, what was tried,
  what worked, what didn't.
- If the topic maps to a git repo, run `git log --oneline -20` and read relevant
  commits (messages often capture decisions and false starts); use
  `git log -p --follow <file>` for files that churned a lot.
- Read the current state of relevant files so the "final landing config" is accurate.

**For 学习材料 (B):**
- Identify the topic; read the relevant code, `README.md`, `CLAUDE.md` for
  pre-existing rationale to cite rather than re-derive.

**Optional — external research:** if the topic needs community best practices or
comparison the user isn't already familiar with, spawn a fork:

```
Agent({ description: "Research <topic>",
        prompt: "Research <specific question>. Report concise findings in 600-1000 words with citations." })
```

Don't waste a research fork if the project's own code + history is enough.

**Note any private source docs you'll cite** (PRDs, specs, design notes from other
repos) — they become `reference/` snapshots in Step 4.

### 3. Pick the category and write the Markdown

**3a. Choose the directory path (categories nest).** Categories are a **nested
tree**: pick the broad top-level domain first, then a finer sub-folder. Don't use a
narrow technique as the top level (that scatters docs of the same system). **Reuse
the best fit at every level**; only create a new folder (short English kebab-case)
if nothing fits. Full rules + current layout in `VAULT_STRUCTURE.md` § 2.

```bash
find $KNOWLEDGE_VAULT -maxdepth 2 -type d   # see the existing nested categories
mkdir -p "$KNOWLEDGE_VAULT/<域>/<子主题>"    # e.g. llm/ai-ask — only if genuinely needed
```

Example: a new "Bota AI Ask 工具调用" doc → `llm/ai-ask/` (same system as 检索/流式/分支),
not a new top-level `tool-use/`.

**3b. Write the note** directly with the Write tool to
`$KNOWLEDGE_VAULT/<域>/<子主题>/<中文主题名>.md`, modelled on the chosen skeleton.
No generator script, no escaping — Markdown is literal. Apply FORMAT_GUIDE.md
throughout:

- Open with complete **frontmatter** (title, today's real date, author, type,
  audience, tags ≥2-3, optional aliases/related).
- Headings via `#`/`##`/`###`, **no hand-written section numbers**.
- Use **callouts** (`> [!warning]`, `> [!important]`, `> [!quote]`, `> [!todo]`)
  to grade key info; **mermaid** for any flow/architecture/pipeline diagram (never
  ASCII line-art); fenced code blocks with a language tag.
- Wire it into the graph with **`[[wikilinks]]`** to related notes and reference
  docs, plus a `related:` list in frontmatter.

**3c. Images** (if any) go in the note's own `attachments/` subfolder; reference
them `![[attachments/foo.png]]`. Read each image first to confirm it matches its
caption (FORMAT_GUIDE.md § 11).

**3d. Wire links per the protocol (FORMAT_GUIDE.md § 9).** Add `related` (curated
peers — strong-tie test, reciprocal, no references/MOCs) and in-body `[[ ]]` at real
citation points. Don't reflexively cross-link "same author/company".

**3e. Rebuild indexes + check links.** After adding/moving a doc, regenerate the
folder-note MOCs (so it shows up in its domain index and the graph hierarchy stays
correct), then run the link checker and fix what it flags:

```bash
$SKILL_PYTHON ${CLAUDE_SKILL_DIR}/scripts/build_indexes.py
python3 ${CLAUDE_SKILL_DIR}/scripts/check_links.py     # fix BROKEN / RELATED-ASYM / RELATED-BADTGT
```

If you created a brand-new top-level domain, also add a row to `_home.md`'s table
linking its index (e.g. `[[llm]]`).

### 4. Snapshot any referenced source docs into reference/

If the doc cites private source docs from other repos (PRD, spec, design notes),
snapshot them per `VAULT_STRUCTURE.md` § 4 so the `[[wikilinks]]` resolve and the
evidence is preserved at the version you cited:

1. `mkdir -p $KNOWLEDGE_VAULT/reference/<project>/`
2. Copy each source doc in (keep its original name): e.g.
   `reference/cosmind/prd.md`. **First check** if a snapshot already exists —
   update it (overwrite + bump `snapshot_date`) instead of making a second copy.
3. Prepend **provenance frontmatter** to each snapshot (`type: reference`,
   `source_project`, `source_path`, `snapshot_date`, `snapshot_reason`, `tags`).
4. Add/update a one-line entry in `reference/reference.md` (the anti-pileup ledger,
   which doubles as the reference-domain MOC linked from `_home`:
   wikilink · source project · snapshot date · why it's here).

Do NOT pull in public web pages / papers / official docs — those stay as plain
URLs in the body. `reference/` is only for private, in-repo source docs that get
re-read (VAULT_STRUCTURE.md § 4).

### 5. PDF export — leave it to Obsidian (manual)

Default is **Markdown only**. Do **not** build a PDF toolchain. When the user wants
a PDF, they export it themselves from Obsidian: **File → Export to PDF** (or right-
click the note). Obsidian renders callouts, mermaid diagrams, tables, and the
Microsoft YaHei / system fonts natively — better and zero-setup compared to any
pandoc/LaTeX pipeline. The Markdown stays the source; the PDF is an occasional,
hand-exported share artifact.

So: don't generate PDFs, don't install pandoc/TeX/mermaid-filter. Just point the
user at Obsidian's exporter if they ask.

### 5b. Reference maintenance (refresh on demand)

When the user asks to refresh references ("刷新 reference", "检查 reference 有没有更新",
"prd 改了,更新快照"), use the hash-based protocol in `VAULT_STRUCTURE.md`「更新协议」 — it's
designed to cost ~0 tokens on unchanged docs:

- Check all: `bash ${CLAUDE_SKILL_DIR}/scripts/check_references.sh` → lists only the
  CHANGED / NO-HASH / MISSING ones (sha256 compare, all in shell).
- Refresh one: `bash ${CLAUDE_SKILL_DIR}/scripts/refresh_reference.sh <reference/...md>`
  → preserves curated frontmatter, swaps in the latest source body, bumps
  `snapshot_date` + `source_sha256`.
- After refreshing, run the link scan; only re-apply rule-7 internal-link fixes if the
  changed doc's new body introduced relative links — that's the only token cost, and
  only for docs that actually changed.

### 6. Report back

Tell the user:
- The `.md` path (full), and which **category** it landed in (and whether that
  category was new).
- The section outline (so they know what to expect).
- Which **reference** snapshots were added/updated under `reference/<project>/`.
- Anything deferred or guessed (so they can correct).
- That it's Markdown only; if they want a PDF, they can export it from Obsidian
  (File → Export to PDF).

To refine, **edit the `.md` directly** — it's the source now, not a compile
artifact. (This is the big change from the LaTeX era, where you edited the
generator script.)

---

## Style guide for the body

- **Tone**: direct, conversational, technical — an experienced engineer writing to a
  junior teammate. No fluff, no marketing, no "Introduction"/"Conclusion" shells.
- **Code blocks**: full file paths in comments, real runnable commands, language tag
  on single-language blocks (logs/prompts/trees left bare). Literal — no escaping.
- **Tables**: for compare-and-contrast or "tried this → result". Short cells; bold OK.
- **Callouts over inline asides**: grade key info with `> [!important]` /
  `> [!warning]` / `> [!quote]` / `> [!todo]` instead of burying it in prose.
- **Diagrams as mermaid**, not ASCII. Flow/pipeline/architecture/sequence/decision.
- **Bold within text**: `**...**`. Italic for asides: `*...*`.
- **Emoji**: only as reused semantic markers (🔵 locked / ✅ done / ⚠️ warning).
  Never decorative, never in headings. Full policy in FORMAT_GUIDE.md § 10.
- **Avoid**: exclamation points, marketing language, claiming certainty about things
  you didn't verify in the project files.

---

## Legacy: LaTeX (.tex) / .docx path — only if explicitly requested

The old generator-script workflow still works for when the user **explicitly** wants
advanced LaTeX typesetting or a `.docx`:

- `latex_template.py` (in this skill dir) + `examples/lessons_learned_skeleton.py` /
  `study_guide_skeleton.py` produce a `generate_<topic>.py` → `.tex` → PDF via
  `latexmk -lualatex`. `docx_template.py` is the even-older .docx path (same API).
- That path writes to per-topic dirs under `~/claude-report/` and is documented in
  git history of this SKILL.md (pre-Markdown rewrite) if you need the full details:
  read `examples/*.py` headers and `latex_template.py` docstrings.
- **Do not default to it.** Markdown into `$KNOWLEDGE_VAULT/` is the default. Only
  reach for LaTeX when the user says they want `.tex` / advanced print typesetting,
  or for `.docx` when they ask for Word output.

When in doubt, produce Markdown.
