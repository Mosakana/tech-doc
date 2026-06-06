#!/usr/bin/env python3
"""fullwidth.py — make Chinese body punctuation full-width (，。：；！？（）).

Half-width / ASCII punctuation in Chinese prose looks cramped. This converts a
half-width mark to full-width ONLY when it's adjacent to a CJK character (so it
leaves numbers like 0.8.0, code, URLs, English clauses, and enumerations alone).
Parentheses are handled as PAIRS (both go full-width if either side touches CJK,
either contains CJK, or either side is already full-width — avoids `（vector)`).

Protected (never touched): fenced code blocks, inline code `` `…` ``, wikilinks
`[[…]]`, markdown-link URLs `](…)`, autolinks/bare URLs, YAML frontmatter, and
HEADING lines (`#…`) — headings are skipped so `[[#anchor]]` links keep matching.

Each in-place rewrite is gated by a structural-safety check (code blocks byte-equal
+ wikilinks unchanged); if it fails, the file is skipped.

Usage:
  python3 fullwidth.py --check [VAULT]    # list docs with CJK-adjacent half-width punct
  python3 fullwidth.py <file.md> [file…]  # convert in place

Skips reference/ in --check (verbatim source snapshots).
"""
import os, re, sys, glob

def CJK(c):
    return bool(c) and ('一' <= c <= '鿿' or '㐀' <= c <= '䶿'
                        or '　' <= c <= '〿' or '＀' <= c <= '￯')

PH0, PH1 = '', ''   # private-use sentinels (not CJK, no punct)

def _protect(line):
    store = []
    def stash(m):
        store.append(m.group(0)); return f"{PH0}{len(store)-1}{PH1}"
    line = re.sub(r'`[^`]*`', stash, line)
    line = re.sub(r'\[\[[^\]]*\]\]', stash, line)
    line = re.sub(r'\]\([^)]*\)', stash, line)
    line = re.sub(r'<[^>]+>', stash, line)
    line = re.sub(r'https?://[^\s)）]+', stash, line)
    return line, store

def _restore(line, store):
    return re.sub(PH0 + r'(\d+)' + PH1, lambda m: store[int(m.group(1))], line)

PAIR = {',': '，', ';': '；', ':': '：', '!': '！', '?': '？'}

def _conv(s):
    s = list(s)
    stack, tofull = [], set()
    for i, c in enumerate(s):
        if c in '(（':
            stack.append(i)
        elif c in ')）' and stack:
            o = stack.pop()
            inside = any(CJK(s[k]) for k in range(o + 1, i))
            before = o - 1 >= 0 and CJK(s[o - 1])
            after = i + 1 < len(s) and CJK(s[i + 1])
            if before or after or inside or s[o] == '（' or s[i] == '）':
                tofull.add(o); tofull.add(i)
    for k in tofull:
        s[k] = '（' if s[k] in '(（' else '）'
    n = len(s)
    for i in range(n):
        c = s[i]; p = s[i - 1] if i > 0 else ''; q = s[i + 1] if i + 1 < n else ''
        if c in PAIR and (CJK(p) or CJK(q)):
            s[i] = PAIR[c]
        elif c == '.' and CJK(p):
            s[i] = '。'
    return ''.join(s)

def convert(text):
    lines = text.split('\n'); out = []; i = 0
    if lines and lines[0].strip() == '---':                 # frontmatter passthrough
        out.append(lines[0]); i = 1
        while i < len(lines):
            out.append(lines[i])
            if lines[i].strip() == '---': i += 1; break
            i += 1
    in_code = False
    for line in lines[i:]:
        if line.strip().startswith(('```', '~~~')):
            in_code = not in_code; out.append(line); continue
        if in_code or line.lstrip().startswith('#'):         # skip code + headings
            out.append(line); continue
        prot, store = _protect(line)
        out.append(_restore(_conv(prot), store))
    return '\n'.join(out)

# ---- safety gate -----------------------------------------------------------

def _codeblock(t):
    inc = False; buf = []
    for l in t.split('\n'):
        if l.strip().startswith('```'): inc = not inc; buf.append(l); continue
        if inc: buf.append(l)
    return '\n'.join(buf)

def safe(before, after):
    return (_codeblock(before) == _codeblock(after)
            and re.findall(r'\[\[[^\]]+\]\]', before) == re.findall(r'\[\[[^\]]+\]\]', after))

# ---- detector for --check --------------------------------------------------

def needs(text):
    n = 0; in_fm = in_code = False; fm = 0
    for line in text.split('\n'):
        if line.strip() == '---' and not in_code:
            fm += 1
            if fm == 1: in_fm = True; continue
            if fm == 2: in_fm = False; continue
        if in_fm: continue
        if line.strip().startswith('```'): in_code = not in_code; continue
        if in_code or line.lstrip().startswith('#'): continue
        prot, _ = _protect(line)
        s = list(prot)
        for i, c in enumerate(s):
            if c in ',;:!?().':
                p = s[i - 1] if i > 0 else ''; q = s[i + 1] if i + 1 < len(s) else ''
                if (c == '.' and CJK(p)) or (c in ',;:!?()' and (CJK(p) or CJK(q))):
                    n += 1
    return n

def main(argv):
    if argv and argv[0] == '--check':
        vault = (argv[1] if len(argv) > 1
                 else os.environ.get('KNOWLEDGE_VAULT') or os.path.expanduser('~/Knowledge'))
        bad = []
        for p in sorted(glob.glob(vault + '/**/*.md', recursive=True)):
            if '/.obsidian/' in p or '/reference/' in p:
                continue
            k = needs(open(p, encoding='utf-8').read())
            if k: bad.append((k, os.path.relpath(p, vault)))
        for k, f in sorted(bad, reverse=True):
            print(f"  {k:>4}  {f}")
        print("(空 = 中文正文标点已全角;reference/ 不算)" if not bad else "对每个跑:  fullwidth.py <file>")
        return
    if not argv:
        sys.exit(__doc__)
    for f in argv:
        before = open(f, encoding='utf-8').read()
        after = convert(before)
        if after == before:
            print(f"=  {os.path.basename(f)} (无改动)")
        elif safe(before, after):
            open(f, 'w', encoding='utf-8').write(after)
            print(f"✅ {os.path.basename(f)}")
        else:
            print(f"⚠  {os.path.basename(f)} — 结构校验未过,已跳过(人工检查)")

if __name__ == '__main__':
    main(sys.argv[1:])
