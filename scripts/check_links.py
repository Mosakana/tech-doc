#!/usr/bin/env python3
"""check_links.py — audit wikilink health across the vault. READ-ONLY; prints a
report you act on (like check_references.sh). Run after writing/moving/editing docs.

Checks:
  1. BROKEN          [[target]] resolves to no note (code spans excluded).
  2. RELATED-ASYM    A lists B in frontmatter `related`, but B doesn't list A back.
                     (`related` is a CURATED relationship → must be reciprocal.
                      One-way links TO a reference snapshot are fine — citations,
                      not relationships — so those are excluded.)
  3. RELATED-BADTGT  a `related` entry is missing, or points to a MOC/index or a
                     reference (related should point to a sibling KNOWLEDGE doc).
  4. ORPHAN          a knowledge doc nothing links to except its auto-generated MOC,
                     and with empty `related` — i.e. reachable only via the folder
                     hierarchy. Advisory: consider whether it should relate to something.

Usage:  python3 check_links.py [VAULT]
        (VAULT defaults to $KNOWLEDGE_VAULT, then ~/Knowledge)
"""
import os, re, sys, glob

VAULT = (sys.argv[1] if len(sys.argv) > 1
         else os.environ.get("KNOWLEDGE_VAULT") or os.path.expanduser("~/Knowledge"))


def strip_code(t):
    return re.sub(r"`[^`]*`", "", re.sub(r"```.*?```", "", t, flags=re.S))


def parse(path):
    raw = open(path, encoding="utf-8").read()
    fm = re.match(r"^---\n(.*?)\n---", raw, re.S)
    front = fm.group(1) if fm else ""
    body = raw[fm.end():] if fm else raw
    typ = (re.search(r"^type:\s*(.+)$", front, re.M) or [None, ""])[1].strip()
    related = []
    m = re.search(r"^related:\n((?:\s*-\s*.+\n?)+)", front, re.M)
    if m:
        related = [re.sub(r'[\[\]"]', "", l.split("|")[0]).strip().lstrip("-").strip()
                   for l in m.group(1).splitlines() if l.strip()]
    bodylinks = [x.split("|")[0].split("#")[0].replace("\\", "").strip()
                 for x in re.findall(r"\[\[([^\]]+)\]\]", strip_code(body))]
    return {"type": typ, "related": [r for r in related if r],
            "bodylinks": [b for b in bodylinks if b], "raw_body": strip_code(body)}


files = [p for p in glob.glob(VAULT + "/**/*.md", recursive=True) if "/.obsidian/" not in p]
meta = {p: parse(p) for p in files}
# resolution maps
by_base, by_rel = {}, {}
for p in files:
    by_base.setdefault(os.path.splitext(os.path.basename(p))[0], p)
    by_rel[os.path.relpath(p, VAULT)[:-3]] = p


def resolve(tgt):
    return by_rel.get(tgt) or by_base.get(tgt)


def is_ref(p):     return p is not None and os.path.relpath(p, VAULT).startswith("reference/")
def is_moc(p):     return p is not None and meta[p]["type"] == "moc"
def is_home(p):    return p is not None and os.path.basename(p) == "_home.md"
def base(p):       return os.path.splitext(os.path.basename(p))[0]

broken, asym, badtgt, orphan = [], [], [], []

# 1. broken (all wikilinks: related + body)
for p, m in meta.items():
    for tgt in set(m["related"] + m["bodylinks"]):
        if not resolve(tgt):
            broken.append((os.path.relpath(p, VAULT), tgt))

# 2 & 3. related asymmetry + bad target  (only for knowledge docs)
for p, m in meta.items():
    if is_moc(p) or is_ref(p) or is_home(p):
        continue
    for tgt in m["related"]:
        tp = resolve(tgt)
        if tp is None:
            badtgt.append((os.path.relpath(p, VAULT), tgt, "目标不存在")); continue
        if is_moc(tp) or is_ref(tp):
            kind = "指向 MOC/索引" if is_moc(tp) else "指向 reference(应是单向正文引用,不放 related)"
            badtgt.append((os.path.relpath(p, VAULT), tgt, kind)); continue
        # reciprocity: tp.related should contain p (by basename)
        back = {resolve(r) for r in meta[tp]["related"]}
        if p not in back:
            asym.append((base(p), "→", tgt))

# 4. orphan: knowledge doc with no incoming link except MOC/_home, and empty related
incoming = {p: set() for p in files}
for p, m in meta.items():
    for tgt in set(m["related"] + m["bodylinks"]):
        tp = resolve(tgt)
        if tp:
            incoming[tp].add(p)
for p, m in meta.items():
    if is_moc(p) or is_ref(p) or is_home(p):
        continue
    real_in = [q for q in incoming[p] if not (is_moc(q) or is_home(q))]
    out = {resolve(t) for t in m["related"] + m["bodylinks"]}
    real_out = [q for q in out if q and not (is_moc(q) or is_home(q))]
    if not real_in and not real_out:    # 进、出都只有层级 → 真孤立
        orphan.append(os.path.relpath(p, VAULT))


def section(title, rows, fmt):
    print(f"\n=== {title} ({len(rows)}) ===")
    for r in rows:
        print("  " + fmt(r))


section("1. BROKEN 断链", broken, lambda r: f"{r[0]}  →  [[{r[1]}]]")
section("2. RELATED-ASYM 单向 related(应互链)", asym, lambda r: f"{r[0]} {r[1]} {r[2]}   (在 [[{r[2]}]] 里补回 [[{r[0]}]],或从这边删)")
section("3. RELATED-BADTGT related 目标不当", badtgt, lambda r: f"{r[0]}  →  [[{r[1]}]]  ({r[2]})")
section("4. ORPHAN 仅靠层级连接的孤立文档", orphan, lambda r: f"{r}  (没有任何文档链它、它 related 也空 — 考虑是否该关联)")

total = len(broken) + len(asym) + len(badtgt)
print(f"\n--- 须修复: {total}  (broken={len(broken)} asym={len(asym)} badtgt={len(badtgt)})；orphan(仅提示)={len(orphan)} ---")
