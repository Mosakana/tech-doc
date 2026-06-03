# tech-doc — a Claude Code skill for a Markdown / Obsidian knowledge base

Turn debugging sessions and learning into clean, **Obsidian-friendly Markdown** notes
in a nested, graph-linked knowledge vault — and keep that vault healthy with scripts.

The skill writes Chinese-language technical docs (踩坑记 / lessons-learned and 学习材料 /
study guides) as Markdown with frontmatter, callouts, mermaid diagrams, and `[[wikilinks]]`,
into an Obsidian vault organized by **nested domains** with auto-generated index (MOC) notes.

## What's in here

| File | Purpose |
|---|---|
| `SKILL.md` | Orchestration: how the agent gathers material, picks the directory, writes the doc. |
| `FORMAT_GUIDE.md` | How a single `.md` doc is written (frontmatter, callouts, mermaid, the **link protocol**). |
| `VAULT_STRUCTURE.md` | Where docs go: nested categories, domain MOCs, the `reference/` snapshot rules. |
| `examples/*.md` | Markdown skeletons for the two doc types. |
| `scripts/build_indexes.py` | Generate per-domain MOC notes so the folder hierarchy shows in the graph. |
| `scripts/check_links.py` | Audit wikilinks: broken, asymmetric `related`, refs-in-related, orphans. |
| `scripts/check_references.sh` · `refresh_reference.sh` | Hash-based protocol to snapshot & refresh cited source docs cheaply. |
| `scripts/docx_extract.py` | First-pass `.docx → md` for migrating legacy docs (needs `python-docx`). |
| `latex_template.py` · `docx_template.py` · `examples/*.py` | **Legacy** LaTeX/.docx generators (only if you explicitly want typeset output). |

## Install

Drop this directory into your Claude Code skills folder (or symlink it):

```bash
git clone <this-repo> ~/src/tech-doc
ln -s ~/src/tech-doc ~/.claude/skills/tech-doc
```

## Setup

Set two env vars in your shell profile:

```bash
export KNOWLEDGE_VAULT="$HOME/Knowledge"   # your Obsidian vault root
export SKILL_PYTHON="python3"              # a python with python-docx (only for .docx migration)
```

Optional dep for `.docx` migration: `pip install python-docx`.

## The vault shape

```
$KNOWLEDGE_VAULT/
├── _home.md                 # root MOC → links to each top-level domain index
├── <domain>/                # broad area (llm/, ops/, ...); top level is NOT a narrow technique
│   ├── <domain>.md          # auto-generated MOC (folder-note): links down to docs + up to parent
│   ├── <sub>/               # nest finer sub-topics (llm/ai-ask/, ...)
│   └── attachments/
└── reference/               # snapshots of cited private source docs (PRDs/specs), by project
    └── reference.md         # provenance ledger + reference-domain MOC
```

The MOC notes make the **hierarchy** visible in Obsidian's graph (which otherwise only shows links,
not folders), while `related` frontmatter + in-body `[[ ]]` carry the **real cross-doc relationships**.

## Maintenance loop

After adding/moving docs:

```bash
python3 scripts/build_indexes.py     # refresh domain MOCs
python3 scripts/check_links.py       # fix BROKEN / RELATED-ASYM / RELATED-BADTGT
bash    scripts/check_references.sh   # which cited source docs changed (hash compare)
```

The link & reference protocols (so this isn't vibes-based) are documented in
`FORMAT_GUIDE.md` § 9 and `VAULT_STRUCTURE.md` § 4.
