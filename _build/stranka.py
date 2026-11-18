"""Celá stránka produktu (HTML + index.txt) ze šablonové stránky + dat. Ověřeno oracle3.py."""
import sys, re, json, html as H
import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import produkt as P, rscx
from rsc import Page, parse_rows, ser_rows, PUSH_RE, esc

def ld_text(p, y2):
    kat = P.kat_info(y2, p['kategorie'])
    return P.ld_json(p, kat['nazev'] if kat else '')

def need_T(p, y2):
    # empiricky z produkce: T řádek od ~1010 znaků, u produktů s mnoha fotkami inline
    return len(ld_text(p, y2)) >= 1010 and len(p['fotky']) <= 10

class Sablona:
    def __init__(self, dirpath, slug, nazev, prvni):
        self.pg = Page(dirpath); self.slug = slug; self.nazev = nazev; self.prvni = prvni
        self.T = any(r[1] == 'T' and r[0] != '2' for r in self.pg.rows)

def build_page(sab, p, E, F, y2):
    """vrací (html, rsc) pro produkt p podle šablony sab"""
    pg = sab.pg; ep = E[p['slug']]
    rows = [list(r) for r in pg.rows]
    parts = list(pg.parts)
    ld = ld_text(p, y2)
    T = need_T(p, y2); assert T == sab.T, 'špatná šablona'
    ref = '$L12' if T else '$L11'
    tr = P.row9_tree(ep, E, F, y2)
    s9 = P.dumps(tr).replace('$LCL', ref)
    if T: s9 = s9.replace(json.dumps(ld, ensure_ascii=False), '"$11"')
    desc = P.meta_desc(p); title = p['nazev'] + ' — by IV & Italy brands'
    for r in rows:
        if r[0] == '0': r[2] = r[2].replace(f'"{sab.slug}"', json.dumps(p['slug']))
        elif r[0] == '9': r[2] = s9
        elif r[0] == 'd':
            r[2] = P.dumps([["$", "meta", "0", {"charSet": "utf-8"}], ["$", "title", "1", {"children": title}],
                            ["$", "meta", "2", {"name": "description", "content": desc}]])
        elif r[0] == '11' and r[1] == 'T': r[2] = ld
    rsc = ser_rows(rows)
    # HTML: sudé části
    E_ = rscx.esc_text
    for k in range(0, len(parts), 2):
        s = parts[k]
        s = s.replace(f'<link rel="preload" as="image" href="/images/produkty/{sab.prvni}"/>', f'<link rel="preload" as="image" href="/images/produkty/{E_(p["fotky"][0])}"/>')
        s = re.sub(r'<title>.*?</title>', lambda m: f'<title>{E_(title)}</title>', s, flags=re.S)
        s = re.sub(r'<meta name="description" content=".*?"/>', lambda m: f'<meta name="description" content="{E_(desc)}"/>', s, flags=re.S)
        s = re.sub(r'<main id="obsah">.*?</main>', lambda m: P.main_html(p, E, F, y2), s, flags=re.S)
        parts[k] = s
    out = []; first = True
    for k, s in enumerate(parts):
        if k % 2 == 0: out.append(s)
        elif first: out.append('<script>self.__next_f.push(' + esc(rsc) + ')</script>'); first = False
    return ''.join(out), rsc
