"""Rozšíření rsc.py pro byIV: JSON strom RSC řádků + render RSC uzlu do HTML jako React SSR."""
import json, re, html as _h
from rsc import Page

BASE = '/propozice-byiv-next'
VOID = {'img','br','hr','input','meta','link','source','area','col','embed','wbr'}
ATTR = {'className':'class','htmlFor':'for','charSet':'charset','httpEquiv':'http-equiv','crossOrigin':'crossorigin',
        'fetchPriority':'fetchpriority','colSpan':'colspan','rowSpan':'rowspan','tabIndex':'tabindex','readOnly':'readonly',
        'autoComplete':'autocomplete','maxLength':'maxlength','strokeWidth':'stroke-width','strokeLinecap':'stroke-linecap',
        'strokeLinejoin':'stroke-linejoin','viewBox':'viewBox','srcSet':'srcset','dateTime':'datetime'}
UNITLESS = {'lineHeight','fontWeight','opacity','zIndex','flex','flexGrow','flexShrink','order','zoom','aspectRatio','gridRow','gridColumn','columnCount','orphans','widows'}
LINKS = {'$L8'}   # next/link reference ids (per page ověřit)

def esc_text(s):
    return s.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;').replace('"','&quot;').replace("'",'&#x27;')
def kebab(k):
    return re.sub(r'([A-Z])', lambda m: '-' + m.group(1).lower(), k)
def style_str(st):
    out = []
    for k, v in st.items():
        if v is None or v == '$undefined' or v is False or v == '': continue
        if isinstance(v, (int, float)) and not isinstance(v, bool) and v != 0 and k not in UNITLESS:
            v = f'{v}px'
        out.append(f'{kebab(k)}:{v}')
    return ';'.join(out)

def attrs(props):
    s = ''
    for k, v in props.items():
        if k in ('children','dangerouslySetInnerHTML','key','prefetch','scroll','replace') or v is None or v == '$undefined' or v is False: continue
        name = ATTR.get(k, k)
        if k == 'style': s += f' style="{esc_text(style_str(v))}"'; continue
        if v is True: s += f' {name}=""'; continue
        if k == 'href' and isinstance(v, str) and v.startswith('/') and not v.startswith(BASE) and props.get('_link'): v = BASE + v
        if k == '_link': continue
        s += f' {name}="{esc_text(str(v))}"'
    return s

def is_el(n): return isinstance(n, list) and len(n) == 4 and n[0] == '$' and isinstance(n[1], str)

def render(n, links=LINKS):
    if n is None or n is False or n is True or n == '$undefined': return ''
    if isinstance(n, str): return esc_text(n)
    if isinstance(n, (int, float)): return str(n)
    if is_el(n):
        _, tag, key, props = n
        props = props or {}
        if tag in links:
            props = dict(props); props['_link'] = True; tag = 'a'
            href = props.pop('href', None); props.pop('_link')
            if isinstance(href, str) and href.startswith('/'): href = BASE + href
            props['href'] = href
        if tag.startswith('$'): raise ValueError('neznámý ref ' + tag)
        a = attrs(props)
        if tag in VOID: return f'<{tag}{a}/>'
        if 'dangerouslySetInnerHTML' in props: return f'<{tag}{a}>{props["dangerouslySetInnerHTML"]["__html"]}</{tag}>'
        return f'<{tag}{a}>{render_children(props.get("children"), links)}</{tag}>'
    if isinstance(n, list): return render_children(n, links)
    raise ValueError(repr(n)[:100])

def flat(ch, out):
    if isinstance(ch, list) and not is_el(ch):
        for c in ch: flat(c, out)
    else: out.append(ch)
    return out

def render_children(ch, links=LINKS):
    if ch is None: return ''
    items = flat(ch, []) if (isinstance(ch, list) and not is_el(ch)) else [ch]
    out = ''; prev_text = False
    for c in items:
        txt = isinstance(c, (str, int, float)) and not isinstance(c, bool) and c != '$undefined'
        if txt and prev_text: out += '<!-- -->'
        r = render(c, links)
        out += r
        if r == '' and not txt: continue
        prev_text = txt
    return out

def dumps(o): return json.dumps(o, ensure_ascii=False, separators=(',', ':'))

class JPage(Page):
    """Page s JSON stromy řádků; tree(rid) -> objekt, commit() zapíše zpět."""
    def __init__(self, d):
        super().__init__(d); self._t = {}
    def tree(self, rid):
        if rid not in self._t:
            row = [r for r in self.rows if r[0] == rid and r[1] == ''][0]
            self._t[rid] = (row, json.loads(row[2].rstrip('\n')) if not row[2].startswith('I[') else None)
            assert dumps(self._t[rid][1]) == row[2], f'{self.dir}: JSON round-trip řádku {rid} nesedí'
        return self._t[rid][1]
    def commit(self):
        for rid, (row, t) in self._t.items(): row[2] = dumps(t)
    def html_body(self): return ''.join(self.parts[0::2])
    def save(self):
        self.commit(); super().save()

def walk(n, fn, parent=None, idx=None):
    """projde strom; fn(node, parent, idx)"""
    if isinstance(n, list):
        if is_el(n):
            fn(n, parent, idx)
            p = n[3] or {}
            for k, v in list(p.items()):
                if isinstance(v, (list, dict)): walk(v, fn, p, k)
        else:
            for i, c in enumerate(list(n)): walk(c, fn, n, i)
    elif isinstance(n, dict):
        for k, v in list(n.items()):
            if isinstance(v, (list, dict)): walk(v, fn, n, k)

def find(n, pred):
    res = []
    walk(n, lambda x, p, i: pred(x) and res.append((x, p, i)))
    return res
def by_class(cls): return lambda x: (x[3] or {}).get('className') == cls
