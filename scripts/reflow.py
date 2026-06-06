#!/usr/bin/env python3
"""reflow.py — fix hard-wrapped paragraphs (house style is ONE line per paragraph).

A paragraph split across several source lines makes Obsidian (default settings)
render mid-sentence `<br>` breaks. This joins soft-wrapped continuation lines back
into one line, while protecting frontmatter, fenced code blocks, lists, tables,
and callout structure. Each in-place rewrite is gated by a structural-safety check
(heading/fence/table/list/wikilink counts must be unchanged + code blocks byte-equal);
if it fails, the file is skipped.

Usage:
  python3 reflow.py --check [VAULT]      # list docs with mid-paragraph hard wraps
                                         # (VAULT defaults to $KNOWLEDGE_VAULT / ~/Knowledge)
  python3 reflow.py <file.md> [file...]  # reflow those files in place

Note: reference/ snapshots are LEFT ALONE in --check (they're verbatim copies of
their source; the wrapping is inherited, not ours to "fix").
"""
import os, re, sys, glob

# ---- core reflow -----------------------------------------------------------

def _qprefix(line):
    m = re.match(r'^(\s*>\s?)+', line)
    return m.group(0) if m else ''

def _is_blockstart(inner):
    if inner.strip() == '':
        return True
    st = inner.lstrip()
    if st.startswith(('#', '```', '~~~', '|', '![', '<', '[!')):
        return True
    if re.match(r'^[-*+] ', st):           # bullet
        return True
    if re.match(r'^\d+[.)] ', st):         # ordered
        return True
    if re.match(r'^[-*_]{3,}\s*$', st):    # hr
        return True
    return False

def _joinable_prev(p):
    if p is None:
        return False
    inner = p[len(_qprefix(p)):]
    st = inner.lstrip()
    if st == '' or st.startswith(('#', '```', '~~~', '|', '[!')):
        return False
    if re.match(r'^[-*_]{3,}\s*$', st):
        return False
    return True  # prose / bullet / continuation = joinable text content

def reflow(text):
    lines = text.split('\n')
    out, i = [], 0
    if lines and lines[0].strip() == '---':          # frontmatter passthrough
        out.append(lines[0]); i = 1
        while i < len(lines):
            out.append(lines[i])
            if lines[i].strip() == '---':
                i += 1; break
            i += 1
    in_code = False
    for line in lines[i:]:
        if line.strip().startswith(('```', '~~~')):
            in_code = not in_code; out.append(line); continue
        if in_code:
            out.append(line); continue
        pre = _qprefix(line)
        inner = line[len(pre):]
        if _is_blockstart(inner):
            out.append(line); continue
        prev = out[-1] if out else None
        if prev is not None and _joinable_prev(prev) and _qprefix(prev) == pre:
            out[-1] = prev.rstrip() + ' ' + inner.lstrip()
        else:
            out.append(line)
    return '\n'.join(out)

# ---- structural-safety check ----------------------------------------------

def _counts(t):
    code = '\n'.join(l for l, c in _codelines(t))
    return (len(re.findall(r'(?m)^#{1,6} ', t)),
            len(re.findall(r'(?m)^```', t)),
            len(re.findall(r'(?m)^\|', t)),
            len(re.findall(r'(?m)^\s*[-*+] |^\s*\d+[.)] ', t)),
            len(re.findall(r'\[\[[^\]]+\]\]', t)),
            code)

def _codelines(t):
    inc = False
    for l in t.split('\n'):
        if l.strip().startswith('```'):
            inc = not inc; yield l, True; continue
        yield l, inc

def safe(before, after):
    return _counts(before) == _counts(after)

# ---- mid-paragraph detector (for --check) ----------------------------------

def hardwrap_hits(text):
    in_fm = in_code = False; fm = 0; run = h = 0
    for l in text.split('\n'):
        if l.strip() == '---' and not in_code:
            fm += 1
            if fm == 1: in_fm = True; continue
            if fm == 2: in_fm = False; continue
        if in_fm: continue
        if l.strip().startswith('```'): in_code = not in_code; run = 0; continue
        if in_code: continue
        st = l.lstrip()
        prose = (l.strip() and not st.startswith(('#', '- ', '* ', '+ ', '|', '>', '![', '<'))
                 and not re.match(r'^\d+[.)] ', st) and not re.match(r'^[-*_]{3,}$', l.strip()))
        if prose:
            run += 1; h += (run >= 2)
        else:
            run = 0
    return h

# ---- CLI -------------------------------------------------------------------

def main(argv):
    if argv and argv[0] == '--check':
        vault = (argv[1] if len(argv) > 1
                 else os.environ.get('KNOWLEDGE_VAULT') or os.path.expanduser('~/Knowledge'))
        bad = []
        for p in sorted(glob.glob(vault + '/**/*.md', recursive=True)):
            if '/.obsidian/' in p or '/reference/' in p:
                continue
            n = hardwrap_hits(open(p, encoding='utf-8').read())
            if n: bad.append((n, os.path.relpath(p, vault)))
        for n, f in sorted(bad, reverse=True):
            print(f"  {n:>3}  {f}")
        print("(空 = 无段落内硬折行;reference/ 快照不算)" if not bad
              else "对每个跑:  reflow.py <file>")
        return
    if not argv:
        sys.exit(__doc__)
    for f in argv:
        before = open(f, encoding='utf-8').read()
        after = reflow(before)
        if after == before:
            print(f"=  {os.path.basename(f)} (无改动)")
        elif safe(before, after):
            open(f, 'w', encoding='utf-8').write(after)
            print(f"✅ {os.path.basename(f)}")
        else:
            print(f"⚠  {os.path.basename(f)} — 结构校验未过,已跳过(请人工检查)")

if __name__ == '__main__':
    main(sys.argv[1:])
