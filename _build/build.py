#!/usr/bin/env python3
"""Přestaví byiv.cz z dat (_data/*.json): produktové stránky, e-shop, úvod, řady, počty, sitemap, chunk s daty.
Spuštění z kořene webu: python3 _build/build.py   (idempotentní: nad nezměněnými daty nic nezmění)"""
import os, sys, re, json, shutil, hashlib, glob
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.getcwd()
import rscx; rscx.BASE = ''
import katalog; katalog.BASE = ''
import produkt as P, stranka as S, derive, chunkjs, variants
from rsc import Page, PUSH_RE, esc
from katalog import pl, kc

NB = ' '
def rd(f): return open(f, encoding='utf-8').read()
def wr(f, s):
    if os.path.exists(f) and rd(f) == s: return False
    os.makedirs(os.path.dirname(f) or '.', exist_ok=True)
    open(f, 'w', encoding='utf-8').write(s); return True

# ---------- data ----------
Z = json.load(open('_data/zaklad.json', encoding='utf-8'))
F = json.load(open('_data/produkty.json', encoding='utf-8'))
UV = json.load(open('_data/uvod.json', encoding='utf-8'))
# nahrané fotky (img/uploads/…) se zkopírují mezi produktové a v datech nahradí názvem souboru
for p in F:
    nf = []
    for f in p['fotky']:
        if f.startswith('img/uploads/'):
            assert os.path.exists(f), f'chybí nahraná fotka {f}'
            n = 'up-' + f[len('img/uploads/'):].replace('/', '-')
            if not os.path.exists('images/produkty/' + n): shutil.copyfile(f, 'images/produkty/' + n)
            f = n
        nf.append(f)
    p['fotky'] = nf
slugs = [p['slug'] for p in F]; assert len(set(slugs)) == len(slugs), 'duplicitní slug'
for p in F:
    assert p['fotky'], p['slug'] + ': bez fotky'
    assert re.fullmatch(r'[a-z0-9-]+', p['slug']), p['slug']
    for f in p['fotky']: assert os.path.exists('images/produkty/' + f), f'chybí foto {f}'
Y2 = derive.y2_counts(Z['y2'], F)
XB = derive.xB_derive(Z['xB'], F, Z['y2'])
LD = Z['LD']
BY = {p['slug']: p for p in F}
changed = []

# ---------- 1. chunk s daty (cache busting) ----------
def chunk():
    cur = glob.glob('_next/static/chunks/653-*.js'); refd = None
    # aktuální = ta, na kterou odkazuje index.html
    h = rd('index.html')
    m = re.search(r'chunks/(653-[0-9a-f]{16})\.js', h); assert m, 'chunk 653 není odkazován'
    name = m.group(1); f = f'_next/static/chunks/{name}.js'
    new = chunkjs.replace_module(rd(f), Y2, XB, LD, F)
    hh = hashlib.md5(new.encode('utf-8')).hexdigest()[:16]
    nn = f'653-{hh}'
    if nn == name: return
    wr(f'_next/static/chunks/{nn}.js', new)
    for g in cur:
        if os.path.basename(g)[:-3] != nn: os.remove(g)
    n = 0
    for root, ds, fs in os.walk('.'):
        if root.startswith(('./.git', './_build', './_data', './images')): continue
        for fn in fs:
            if fn.endswith(('.html', '.txt', '.js')):
                p = os.path.join(root, fn); s = rd(p)
                if name in s: wr(p, s.replace(name, nn)); n += 1
    changed.append(f'chunk {name[4:]} → {hh} ({n} souborů)')

# ---------- 2. produktové stránky ----------
def produkty():
    E = variants.enrich(F)
    sab = {}
    for d, slug in (('body-bodyslim-diorko', 'body-bodyslim-diorko'), ('leginy-s-krajkou-tessuti', 'leginy-s-krajkou-tessuti')):
        x = S.Sablona(os.path.join(HERE, 'sablony', d), slug, None, slug + '-1.jpg'); sab[x.T] = x
    assert len(sab) == 2
    n = 0
    for p in F:
        html, rsc = S.build_page(sab[S.need_T(p, Y2)], p, E, F, Y2)
        d = f'produkt/{p["slug"]}'
        a = wr(d + '/index.html', html); b = wr(d + '/index.txt', rsc)
        n += a or b
    for d in os.listdir('produkt'):
        if d not in BY and os.path.isdir('produkt/' + d):
            shutil.rmtree('produkt/' + d); changed.append('smazán produkt ' + d)
    if n: changed.append(f'produktových stránek přepsáno: {n}')

# ---------- 3. e-shop ----------
def eshop():
    for k in [None] + [c['slug'] for c in Y2]:
        d = 'eshop' if not k else f'eshop/{k}'
        h = rd(d + '/index.html')
        novy = k in katalog.PRIPRAVUJEME
        wr(d + '/index.html', katalog.katalog_replace(h, Y2, F, k, novy=novy, chip_old='Slevy'))
        pg = Page(d)
        cnt = len(katalog.produkty_kategorie(F, k)) if k else len(F)
        txt = pl(cnt, 'model', 'modely', 'modelů')
        pat = re.compile(r'\d+ (?:model|modely|modelů)(?= v této kategorii| ve velikostech XXS)')
        for i in range(0, len(pg.parts), 2): pg.parts[i] = pat.sub(txt, pg.parts[i])
        for r in pg.rows: r[2] = pat.sub(txt, r[2])
        pg.save()

# ---------- 4. úvod ----------
def uvod():
    E = variants.enrich(F)
    pg = Page('.')
    sections = [[BY[s] for s in UV['novinky'] if s in BY], [BY[s] for s in UV['slevy'] if s in BY]]
    full = ''.join(pg.parts[0::2])
    segs = [m.group(0) for m in re.finditer(r'<div class="produkty produkty--ctyri">(?:<a [^>]*>.*?</a>)*</div>', full, re.S)]
    assert len(segs) == 2, len(segs)
    for old, items in zip(segs, sections):
        new = '<div class="produkty produkty--ctyri">' + ''.join(rscx.render(P.card_tree(E[q['slug']])) for q in items) + '</div>'
        for i in range(0, len(pg.parts), 2): pg.parts[i] = pg.parts[i].replace(old, new)
    key = '"className":"produkty produkty--ctyri","children":'
    cnt = [0]
    for row in pg.rows:
        s = row[2]; out = ''; pos = 0
        while True:
            i = s.find(key, pos)
            if i < 0: break
            a = i + len(key); b = _match(s, a)
            items = sections[cnt[0]]; cnt[0] += 1
            out += s[pos:a] + P.dumps([P.card_tree(E[q['slug']]) for q in items]); pos = b
        row[2] = out + s[pos:]
    assert cnt[0] == 2, cnt
    for c in Y2:
        txt = pl(c['pocet'], 'model', 'modely', 'modelů') if c['pocet'] else None
        if txt is None: continue
        ph = re.compile(r'(<b>' + re.escape(c['nazev']) + r'</b><span class="tnum">)[^<]*(</span>)')
        for i in range(0, len(pg.parts), 2): pg.parts[i] = ph.sub(lambda m: m.group(1) + txt + m.group(2), pg.parts[i])
        pr = re.compile(r'(\["\$","b",null,\{"children":"' + re.escape(c['nazev']) + r'"\}\],\["\$","span",null,\{"className":"tnum","children":")[^"]*(")')
        for r in pg.rows: r[2] = pr.sub(lambda m: m.group(1) + txt + m.group(2), r[2])
    mn = min(p['cena'] for p in F); mx = max(p['cena'] for p in F)
    cena = lambda n: str(n) if n < 1000 else f'{n // 1000}{NB}{n % 1000:03d}'
    for i in range(0, len(pg.parts), 2):
        pg.parts[i] = re.sub(r'(Celá nabídka má <!-- -->)\d+(<!-- --> modelů\. Velikosti XXS až XL, ceny od )[^<]+?( do )[^<]+?( Kč\.)',
                             lambda m: f'{m.group(1)}{len(F)}{m.group(2)}{cena(mn)}{m.group(3)}{cena(mx)}{m.group(4)}', pg.parts[i])
    for r in pg.rows:
        r[2] = re.sub(r'(\["Celá nabídka má ",)\d+(," modelů\. Velikosti XXS až XL, ceny od )[^"]+?( do )[^"]+?( Kč\."\])',
                      lambda m: f'{m.group(1)}{len(F)}{m.group(2)}{cena(mn)}{m.group(3)}{cena(mx)}{m.group(4)}', r[2])
    pg.save()

def _match(s, a):
    """konec JSON pole začínajícího na s[a] == '['"""
    assert s[a] == '[', s[a:a + 20]
    d = 0; i = a; q = False
    while True:
        ch = s[i]
        if q:
            if ch == '\\': i += 1
            elif ch == '"': q = False
        else:
            if ch == '"': q = True
            elif ch == '[': d += 1
            elif ch == ']':
                d -= 1
                if d == 0: return i + 1
        i += 1

# ---------- 5. řady, o nás ----------
def rady():
    pg = Page('rady')
    def line(r):
        pc = kc(r['cenaOd']) if r['cenaOd'] == r['cenaDo'] else f'{kc(r["cenaOd"])} – {kc(r["cenaDo"])}'
        return pl(r['pocet'], 'model', 'modely', 'modelů'), pc
    ph = re.compile(r'(<span class="tnum">)[^<]*?<!-- --> ·<!-- --> <!-- -->[^<]*(</span>)')
    ms = ph.findall(''.join(pg.parts[0::2])); assert len(ms) == len(XB), (len(ms), len(XB))
    it = iter(XB)
    def sub_h(m):
        a, b = line(next(it)); return f'{m.group(1)}{a}<!-- --> ·<!-- --> <!-- -->{b}{m.group(2)}'
    for i in range(0, len(pg.parts), 2): pg.parts[i] = ph.sub(sub_h, pg.parts[i])
    pr = re.compile(r'(\["\$","span",null,\{"className":"tnum","children":\[)"[^"]*"(," ·"," ",)"[^"]*"(\]\}\])')
    it = iter(XB); n = [0]
    def sub_r(m):
        a, b = line(next(it)); n[0] += 1
        return f'{m.group(1)}{json.dumps(a, ensure_ascii=False)}{m.group(2)}{json.dumps(b, ensure_ascii=False)}{m.group(3)}'
    for r in pg.rows: r[2] = pr.sub(sub_r, r[2])
    assert n[0] == len(XB), n
    pg.save()
    pg = Page('o-nas')
    for i in range(0, len(pg.parts), 2): pg.parts[i] = re.sub(r'(<b class="tnum">)\d+(<!-- --> modelů</b>)', lambda m: f'{m.group(1)}{len(F)}{m.group(2)}', pg.parts[i])
    for r in pg.rows: r[2] = re.sub(r'(\["\$","b",null,\{"className":"tnum","children":\[)\d+(," modelů"\])', lambda m: f'{m.group(1)}{len(F)}{m.group(2)}', r[2])
    pg.save()

# ---------- 6. sitemap, verze ----------
def sitemap():
    s = rd('sitemap.xml')
    head = s[:s.index('<loc>https://byiv.cz/produkt/')] if '<loc>https://byiv.cz/produkt/' in s else None
    i = s.index('<url>\n<loc>https://byiv.cz/produkt/'); head = s[:i]
    body = ''.join(f'<url>\n<loc>https://byiv.cz/produkt/{p["slug"]}/</loc>\n<changefreq>weekly</changefreq>\n<priority>0.6</priority>\n</url>\n' for p in F)
    wr('sitemap.xml', head + body + '</urlset>\n')

if __name__ == '__main__':
    steps = [chunk, produkty, eshop, uvod, rady, sitemap]
    if os.environ.get('GITHUB_SHA'): wr('version.json', json.dumps({'sha': os.environ['GITHUB_SHA']}) + '\n')
    for st in steps:
        st(); print('ok', st.__name__, flush=True)
    for c in changed: print(' -', c)
