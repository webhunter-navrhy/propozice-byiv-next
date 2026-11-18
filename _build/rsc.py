"""Úpravy Next.js static exportu (HTML + RSC payload v <script> + index.txt) bez zdrojáků.
Každá úprava se musí provést v HTML i v RSC, jinak React při hydrataci vrátí starý obsah."""
import re, json

PUSH_RE = re.compile(r'<script>self\.__next_f\.push\((\[1,.*?\])\)</script>', re.S)

def parse_rows(text):
    b = text.encode('utf-8'); rows = []; i = 0
    while i < len(b):
        c = b.index(b':', i); rid = b[i:c].decode(); j = c + 1
        m = re.match(rb'T([0-9a-f]+),', b[j:j+20])
        if m:
            n = int(m.group(1), 16); s = j + m.end()
            rows.append([rid, 'T', b[s:s+n].decode('utf-8')]); i = s + n
        else:
            e = b.index(b'\n', j); rows.append([rid, '', b[j:e].decode('utf-8')]); i = e + 1
    return rows

def ser_rows(rows):
    out = []
    for rid, typ, content in rows:
        if typ == 'T':
            out.append(f'{rid}:T{len(content.encode("utf-8")):x},{content}')
        else:
            out.append(f'{rid}:{content}\n')
    return ''.join(out)

def esc(s):
    j = json.dumps([1, s], ensure_ascii=False, separators=(',', ':'))
    return (j.replace('&', '\\u0026').replace('<', '\\u003c').replace('>', '\\u003e')
             .replace('\u2028', '\\u2028').replace('\u2029', '\\u2029'))

class Page:
    def __init__(self, dirpath):
        self.dir = dirpath
        self.html = open(dirpath + '/index.html', encoding='utf-8').read()
        try: self.txt = open(dirpath + '/index.txt', encoding='utf-8').read()
        except FileNotFoundError: self.txt = None
        pushes = PUSH_RE.findall(self.html)
        self.rsc = ''.join(json.loads(p)[1] for p in pushes)
        if self.txt is not None and self.txt != self.rsc:
            raise SystemExit(f'{dirpath}: index.txt != RSC v HTML')
        self.rows = parse_rows(self.rsc)
        assert ser_rows(self.rows) == self.rsc, 'round-trip fail'
        # HTML bez RSC skriptů
        self.parts = PUSH_RE.split(self.html)  # sudé = HTML, liché = push argumenty

    def h(self, old, new, count=1):
        """Úprava ve viditelném HTML (mimo RSC skripty)."""
        n = sum(self.parts[k].count(old) for k in range(0, len(self.parts), 2))
        if n != count: raise SystemExit(f'{self.dir} HTML: "{old[:70]}" nalezeno {n}x, čekáno {count}x')
        for k in range(0, len(self.parts), 2): self.parts[k] = self.parts[k].replace(old, new)

    def r(self, old, new, count=1):
        """Úprava v RSC (po řádcích, T řádky dostanou novou délku)."""
        n = sum(row[2].count(old) for row in self.rows)
        if n != count: raise SystemExit(f'{self.dir} RSC: "{old[:70]}" nalezeno {n}x, čekáno {count}x')
        for row in self.rows: row[2] = row[2].replace(old, new)

    def both(self, old, new, count_h=1, count_r=1):
        self.h(old, new, count_h); self.r(old, new, count_r)

    def save(self):
        rsc = ser_rows(self.rows)
        # všechny push([1,...]) nahradí jeden push na místě prvního
        out = []; first = True
        for k, p in enumerate(self.parts):
            if k % 2 == 0: out.append(p)
            elif first: out.append('<script>self.__next_f.push(' + esc(rsc) + ')</script>'); first = False
        html = ''.join(out)
        open(self.dir + '/index.html', 'w', encoding='utf-8').write(html)
        if self.txt is not None: open(self.dir + '/index.txt', 'w', encoding='utf-8').write(rsc)

# ---- mini renderer: stejný prvek do RSC i do HTML ----
import html as _html
VOID = {'img','br','hr','input','meta','link'}
ATTR = {'className':'class','htmlFor':'for'}

def E(tag, props=None, *children, key=None):
    return ('el', tag, props or {}, list(children), key)

def to_rsc(node):
    if isinstance(node, str): return node
    _, tag, props, ch, key = node
    p = dict(props)
    if ch:
        p['children'] = to_rsc(ch[0]) if len(ch) == 1 else [to_rsc(c) for c in ch]
    return ['$', tag, key, p]

def rsc_json(node):
    return json.dumps(to_rsc(node), ensure_ascii=False, separators=(',', ':'))

def to_html(node):
    if isinstance(node, str): return _html.escape(node, quote=False)
    _, tag, props, ch, key = node
    attrs = ''.join(f' {ATTR.get(k,k)}="{_html.escape(str(v), quote=True)}"' for k, v in props.items())
    if tag in VOID: return f'<{tag}{attrs}/>'
    inner = ''; prev_text = False
    for c in ch:
        is_text = isinstance(c, str)
        if is_text and prev_text: inner += '<!-- -->'
        inner += to_html(c); prev_text = is_text
    return f'<{tag}{attrs}>{inner}</{tag}>'

SINGLE = r'(?<![\wÀ-ž])([vVuUaAkKsSzZoOiI]) '
def nb(s):
    """nezlomitelná mezera po jednopísmenných slovech, jak to dělá původní build"""
    return re.sub(SINGLE, lambda m: m.group(1) + ' ', s)

def loose(s):
    return re.compile('[ \u00a0]'.join(re.escape(x) for x in re.split('[ \u00a0]', s)))

def actual(page, s):
    """najde skutečný zápis textu v RSC (mezery/nbsp volně)"""
    found = set()
    for row in page.rows: found.update(loose(s).findall(row[2]))
    if len(found) != 1: raise SystemExit(f'{page.dir}: "{s[:60]}" → {found}')
    return found.pop()
