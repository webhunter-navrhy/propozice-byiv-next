"""Generátor stránky produktu (HTML + RSC) z dat; ověřeno orákulem proti stávajícím stránkám."""
import json, re, sys
import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rscx
from rscx import esc_text, dumps
from variants import enrich

NB = ' '
def kc(n):
    s = str(round(n)); out = ''
    while len(s) > 3: out = NB + s[-3:] + out; s = s[:-3]
    return s + out + NB + 'Kč'
def sleva(p):
    return round((1 - p['cena'] / p['puvodni']) * 100) if p['puvodni'] and p['puvodni'] > p['cena'] else None
def nb_dph(): return ''

def el(tag, props=None, key=None, children=None):
    pr = dict(props or {})
    if children is not None: pr['children'] = children
    return ['$', tag, key, pr]
def L8(href, children, cls=None, key=None):
    pr = {'href': href, 'children': children}
    if cls: pr = {'className': cls, **pr}
    return ['$', '$L8', key, pr]

def card_tree(p):
    d = sleva(p)
    foto = [el('img', {'src': f'/images/produkty/{p["fotky"][0]}', 'alt': p['nazev'], 'width': 570, 'height': 760, 'loading': 'lazy', 'decoding': 'async'})]
    foto.append(el('img', {'src': f'/images/produkty/{p["fotky"][1]}', 'alt': '', 'width': 570, 'height': 760, 'loading': 'lazy', 'decoding': 'async', 'aria-hidden': 'true'}) if 1 < len(p['fotky']) <= 4 else '$undefined')
    foto.append(el('div', {'className': 'stitky'}, children=[
        el('span', {'className': 'pill pill--pryc'}, children='Vyprodáno') if p['vyprodano'] else False,
        el('span', {'className': 'pill pill--sleva'}, children=['−', d, ' %']) if d else None,
        el('span', {'className': 'pill'}, children='Novinka') if (not d and p['novinka']) else False]))
    meta = ('Velikosti ' + ' · '.join(p['velikosti'])) if p['velikosti'] else 'Jedna velikost'
    cena = [el('b', children=kc(p['cena'])), el('s', children=kc(p['puvodni'])) if p['puvodni'] and p['puvodni'] > p['cena'] else None]
    return ['$', '$L8', p['slug'], {'href': f'/produkt/{p["slug"]}/', 'className': 'karta', 'children': [
        el('div', {'className': 'karta__foto'}, children=foto),
        el('div', {'className': 'karta__telo'}, children=[
            el('span', {'className': 'karta__nazev'}, children=p['nazev']),
            el('span', {'className': 'karta__meta'}, children=meta),
            el('span', {'className': 'karta__cena'}, children=cena)])]}]

def kat_info(y2, slug):
    for c in y2:
        if c['slug'] == slug: return c
    return None

def ld_json(p, katnazev):
    o = {"@context": "https://schema.org", "@type": "Product", "name": p['nazev'],
         "image": [f'https://byiv.cz/images/produkty/{f}' for f in p['fotky']],
         "description": (' '.join(l[2:] if l.startswith('• ') else l for l in p['popis'] if not l.startswith('Fotografie jsou seřazené'))) or 'Dámský model značky by IV, šitý v české dílně.', "brand": {"@type": "Brand", "name": "by IV"},
         **({"material": p['material']} if p['material'] else {}), "category": katnazev,
         "offers": {"@type": "Offer", "price": p['cena'], "priceCurrency": "CZK",
                    "availability": "https://schema.org/OutOfStock" if p['vyprodano'] else "https://schema.org/InStock",
                    "itemCondition": "https://schema.org/NewCondition", "seller": {"@type": "Organization", "name": "by IV"}}}
    return dumps(o)

def meta_desc(p):
    v = (' Velikosti ' + ', '.join(p['velikosti']) + '.') if p['velikosti'] else ' Velikosti jedna velikost.'
    return (f'{p["popis"][0] if p["popis"] else "Dámský model značky by IV, šitý v české dílně."}{v} Cena {p["cena"]} Kč. Šito v české dílně, chybějící velikost ušijeme do 14 pracovních dnů.')

def row9_tree(p, E, F, y2):
    ep = E[p['slug']]
    kat = kat_info(y2, p['kategorie'])
    rel = [q for q in F if q['kategorie'] == p['kategorie'] and q['slug'] != p['slug']][:4]
    drob = ['$', 'nav', None, {'className': 'drobecky drobecky--tmave', 'aria-label': 'Drobečková navigace', 'children': [
        L8('/', 'Úvod'), ' / ', L8('/eshop/', 'E-shop'),
        [' / ', L8(f'/eshop/{kat["slug"]}/', kat['nazev'])] if kat else None]}]
    s1 = el('section', {'className': 'sekce sekce--uzka'}, children=el('div', {'className': 'obal'}, children=[drob, ['$', '$LCL', None, {'p': ep}]]))
    s2 = None
    if rel:
        katl = kat['nazev'].lower() if kat else ''
        s2 = el('section', {'className': 'sekce plocha'}, children=el('div', {'className': 'obal'}, children=[
            el('div', {'className': 'sekce-hlava'}, children=[
                el('div', children=[el('h2', children='Podobné modely'), el('p', children=['Další kousky z kategorie ', katl, '.'])]),
                L8(f'/eshop/{kat["slug"]}/', 'Celá kategorie →', cls='odkaz-vice vice')]),
            el('div', {'className': 'produkty'}, children=[card_tree(q) for q in rel])]))
    ld = el('script', {'type': 'application/ld+json', 'dangerouslySetInnerHTML': {'__html': ld_json(p, kat['nazev'] if kat else '')}})
    return [ld, s1] + ([s2] if s2 else [])


# ---------- HTML detailu (SSR komponenty 6178) ----------
import re as _re
from rscx import esc_text as _E
import rscx

def _svg(size, cls, inner):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
            f'stroke-width="2" stroke-linecap="round" stroke-linejoin="round"{cls} aria-hidden="true">{inner}</svg>')
SVG_CUT = _svg(18, ' class="lucide lucide-scissors"', '<circle cx="6" cy="6" r="3"></circle><path d="M8.12 8.12 12 12"></path><path d="M20 4 8.12 15.88"></path><circle cx="6" cy="18" r="3"></circle><path d="M14.8 14.8 20 20"></path>')
SVG_TRUCK = _svg(18, ' class="lucide lucide-truck"', '<path d="M14 18V6a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2v11a1 1 0 0 0 1 1h2"></path><path d="M15 18H9"></path><path d="M19 18h2a1 1 0 0 0 1-1v-3.65a1 1 0 0 0-.22-.624l-3.48-4.35A1 1 0 0 0 17.52 8H14"></path><circle cx="17" cy="18" r="2"></circle><circle cx="7" cy="18" r="2"></circle>')
SVG_MSG = _svg(17, '', '<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>')

def detail_html(p):
    e = _E; d = sleva(p); f = p['fotky']; v = p.get('varianty') or []
    h = '<div class="detail"><div>'
    h += f'<button type="button" class="detail__hlavni" aria-label="Zvětšit fotografii"><img src="/images/produkty/{e(f[0])}" alt="{e(p["nazev"])} — fotografie 1 z {len(f)}" width="570" height="760" decoding="async" fetchpriority="high"/></button>'
    if len(f) > 1:
        h += '<div class="detail__nahledy">' + ''.join(
            f'<button type="button" aria-current="{"true" if i == 0 else "false"}" aria-label="Fotografie {i+1}"><img src="/images/produkty/{e(x)}" alt="" width="570" height="760" loading="lazy" decoding="async"/></button>' for i, x in enumerate(f)) + '</div>'
    h += '</div><div class="detail__panel">'
    h += f'<h1>{e(p["nazev"])}</h1><div class="detail__cena tnum"><b>{kc(p["cena"])}</b>'
    if p['puvodni'] and p['puvodni'] > p['cena']: h += f'<s>{kc(p["puvodni"])}</s>'
    if d: h += f'<span class="pill pill--sleva">−<!-- -->{d}<!-- --> %</span>'
    h += '</div><p class="detail__dph">Cena je konečná, včetně DPH.</p>'
    if len(v) > 1:
        h += f'<div style="margin-top:var(--sp-6)"><div id="lbl-barva" style="font-weight:600;font-size:15px">Barva: <span style="font-weight:400">{e(p["barva"])}</span></div><div class="barvy" role="list" aria-labelledby="lbl-barva">'
        for x in v:
            akt = x['slug'] == p['slug']
            h += (f'<a class="barva{" barva--akt" if akt else ""}"{" aria-current=\"page\"" if akt else ""} role="listitem" title="{e(x["barva"])}" href="/produkt/{e(x["slug"])}/">'
                  f'<img src="/images/barvy/{e(x["slug"])}.jpg" alt="" width="64" height="85" loading="lazy"/><span>{e(x["barva"])}</span></a>')
        h += '</div></div>'
    else:
        h += '<div style="margin-top:var(--sp-6)"><div id="lbl-barva" style="font-weight:600;font-size:15px">Barva: <span style="font-weight:400">Nevybráno</span></div><select class="barva-vyber" aria-labelledby="lbl-barva"><option value="" selected="">Vyberte možnost</option>'
        if p.get('barvy'):
            h += ''.join(f'<option value="{e(o)}">{e(o)}</option>' for o in p['barvy'])
        elif ' – ' in p['nazev'] and p['nazev'].index(' – ') > 0:
            o = p['nazev'].split(' – ', 1)[1]; o = o[:1].upper() + o[1:]
            h += f'<option value="{e(o)}">{e(o)}</option>'
        h += '</select></div>'
    if p['velikosti']:
        h += '<div style="margin-top:var(--sp-6)"><div id="lbl-velikost" style="font-weight:600;font-size:15px">Velikost</div><div class="velikosti" role="group" aria-labelledby="lbl-velikost">'
        h += ''.join(f'<button type="button" class="velikost" aria-pressed="{"true" if len(p["velikosti"]) == 1 else "false"}">{e(s)}</button>' for s in p['velikosti']) + '</div></div>'
    h += '<div style="display:flex;gap:var(--sp-3);margin-top:var(--sp-5);flex-wrap:wrap">'
    h += f'<button type="button" class="btn btn--primar"{" disabled=\"\"" if p["vyprodano"] else ""}>{"Momentálně vyprodáno" if p["vyprodano"] else "Přidat do košíku"}</button><a class="btn btn--obrys" href="/kosik/">Přejít do košíku</a></div>'
    h += f'<button type="button" class="btn btn--dotaz">{SVG_MSG}Dotaz na tento produkt</button>'
    h += f'<div class="info-pruh">{SVG_CUT}<span>Nemáme vaši velikost skladem? Ušijeme ji na zakázku — doba ušití je obvykle 14 pracovních dnů. Délku i šířku umíme upravit na míru, stačí napsat do poznámky k objednávce. <b>Šití na míru: platba předem.</b></span></div>'
    if p['popis']:
        h += '<div class="detail__popis" style="margin-top:var(--sp-6)">' + ''.join(f'<p>{e(l)}</p>' for l in p['popis']) + '</div>'
    h += f'<table class="parametry"><caption class="sr-skryty">Parametry modelu <!-- -->{e(p["nazev"])}</caption><tbody>'
    if p['material']: h += f'<tr><th scope="row">Materiál</th><td>{e(_re.sub(r"(\d)\s*%", lambda m: m.group(1)+NB+"%", p["material"]))}</td></tr>'
    if p['rada']: h += f'<tr><th scope="row">Materiálová řada</th><td>{e(p["rada"])}</td></tr>'
    h += f'<tr><th scope="row">Dostupné velikosti</th><td>{e(" · ".join(p["velikosti"]) if p["velikosti"] else "Jedna velikost")}</td></tr>'
    h += '<tr><th scope="row">Výroba</th><td>Šito v české dílně</td></tr></tbody></table>'
    h += f'<div class="info-pruh" style="background:var(--brand-soft)">{SVG_TRUCK}<span>Doprava po ČR od 99 Kč, nad <!-- -->{kc(3000)}<!-- --> zdarma. Osobní odběr v butiku ve Zlíně je vždy zdarma.</span></div>'
    return h + '</div></div>'

def main_html(p, E, F, y2):
    rscx.BASE = ''
    t = row9_tree(p, E, F, y2); p = E[p['slug']]
    ld, s1, *rest = t
    drob = s1[3]['children'][3]['children'][0]
    out = '<main id="obsah">' + rscx.render(ld) + '<section class="sekce sekce--uzka"><div class="obal">' + rscx.render(drob) + detail_html(p) + '</div></section>'
    out += ''.join(rscx.render(x) for x in rest) + '</main>'
    return out
