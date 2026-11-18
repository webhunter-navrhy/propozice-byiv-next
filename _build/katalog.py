"""SSR HTML katalogu e-shopu (klientská komponenta 4809 v chunku 594) – musí odpovídat JS 1:1."""
from rscx import esc_text as E, BASE

NB = ' '
def kc(n):
    s = str(round(n)); out = ''
    while len(s) > 3: out = NB + s[-3:] + out; s = s[:-3]
    return s + out + NB + 'Kč'
def pl(n, a, b, c):
    return f'{n} {a}' if n == 1 else (f'{n} {b}' if 2 <= n <= 4 else f'{n} {c}')

VIRT = {
    'novinky': lambda p: p['novinka'],
    'slevy': lambda p: p['vyprodej'] or (p['puvodni'] is not None and p['puvodni'] > p['cena']),
}
PRIPRAVUJEME = ('inspirace', 'imperial', 'komplety')

def produkty_kategorie(Fz, kat):
    if not kat: r = list(Fz)
    elif kat in VIRT: r = [p for p in Fz if p['kategorie'] == kat or VIRT[kat](p)]
    else: r = [p for p in Fz if p['kategorie'] == kat]
    return sorted(r, key=lambda p: p['poradi'])

def karta(p, i):
    t = p['fotky'][0]; r = p['fotky'][1] if len(p['fotky']) > 1 else None
    d = round((1 - p['cena'] / p['puvodni']) * 100) if p['puvodni'] and p['puvodni'] > p['cena'] else None
    prio = i < 4
    h = f'<a class="karta" href="{BASE}/produkt/{p["slug"]}/"><div class="karta__foto">'
    h += f'<img src="{BASE}/images/produkty/{E(t)}" alt="{E(p["nazev"])}" width="570" height="760" loading="{"eager" if prio else "lazy"}" decoding="async"{" fetchpriority=\"high\"" if prio else ""}/>'
    if r: h += f'<img src="{BASE}/images/produkty/{E(r)}" alt="" width="570" height="760" loading="lazy" decoding="async" aria-hidden="true"/>'
    h += '<div class="stitky">'
    if p['vyprodano']: h += '<span class="pill pill--pryc">Vyprodáno</span>'
    if d: h += f'<span class="pill pill--sleva">−<!-- -->{d}<!-- --> %</span>'
    if not d and p['novinka']: h += '<span class="pill">Novinka</span>'
    h += '</div></div><div class="karta__telo">'
    h += f'<span class="karta__nazev">{E(p["nazev"])}</span>'
    meta = ('Velikosti ' + ' · '.join(p['velikosti'])) if p['velikosti'] else 'Jedna velikost'
    h += f'<span class="karta__meta">{E(meta)}</span>'
    h += f'<span class="karta__cena"><b>{kc(p["cena"])}</b>'
    if p['puvodni'] and p['puvodni'] > p['cena']: h += f'<s>{kc(p["puvodni"])}</s>'
    h += '</span></div></a>'
    return h

def odkazy(y2, Fz, kat):
    h = '<div class="filtr__odkazy">'
    h += f'<a{"" if kat else " aria-current=\"page\""} href="{BASE}/eshop/">Celá nabídka <span class="tnum">{len(Fz)}</span></a>'
    for c in y2:
        cur = ' aria-current="page"' if kat == c['slug'] else ''
        h += f'<a{cur} href="{BASE}/eshop/{c["slug"]}/">{E(c["nazev"])}<!-- --> <span class="tnum">{c["pocet"]}</span></a>'
    return h + '</div>'

def vypis(Fz, kat, novy=False):
    """od <p class="katalog__pocet"> po konec výpisu (bez uzavíracích divů katalogu)"""
    C = produkty_kategorie(Fz, kat)
    prazdna = not C and novy and kat in PRIPRAVUJEME
    h = f'<p class="katalog__pocet" aria-live="polite">{("Připravujeme" if prazdna else "Žádný model neodpovídá filtru") if not C else pl(len(C), "model", "modely", "modelů")}</p>'
    h += '<div class="pole" style="max-width:240px"><label for="f-razeni" class="sr-skryty">Řazení</label><select id="f-razeni"><option value="doporucene" selected="">Doporučujeme</option><option value="levne">Od nejlevnějšího</option><option value="drahe">Od nejdražšího</option><option value="nazev">Podle názvu</option></select></div></div>'
    if not C:
        if novy and kat in PRIPRAVUJEME:
            h += PRAZDNO_NOVE
        else:
            h += '<div class="prazdno"><h2>Tomuhle filtru zatím nic neodpovídá</h2><p>Zkuste zrušit část filtrů — nebo nám napište, rádi vám model ušijeme na míru.</p><button type="button" class="btn btn--primar">Zrušit filtry</button></div>'
    else:
        h += '<div class="produkty">' + ''.join(karta(p, i) for i, p in enumerate(C[:24])) + '</div>'
        if 24 < len(C):
            h += f'<div style="display:flex;justify-content:center;margin-top:var(--sp-7)"><button type="button" class="btn btn--obrys">Načíst dalších <!-- -->{min(24, len(C) - 24)}<!-- --> modelů</button></div>'
    return h

PRAZDNO_NOVE = (f'<div class="prazdno prazdno--kolekce"><h2>Kolekci právě připravujeme</h2>'
                '<p>Modely sem doplníme co nejdřív. Zatím se podívejte na celou nabídku, nebo se zastavte v butiku ve Zlíně.</p>'
                f'<a class="btn btn--primar" href="{BASE}/eshop/">Celá nabídka</a></div>')

def katalog_replace(html, y2, Fz, kat, novy=False, chip_old='Výprodej', chip_new='Slevy'):
    i = html.index('<div class="filtr__odkazy">'); j = html.index('</div>', i) + 6
    html = html[:i] + odkazy(y2, Fz, kat) + html[j:]
    i = html.index('<p class="katalog__pocet"'); j = html.index('</section>', i)
    tail = '</div></div></div>'
    assert html[j - len(tail):j] == tail, html[j-60:j]
    html = html[:i] + vypis(Fz, kat, novy) + tail + html[j:]
    old = f'<button type="button" class="chip" aria-pressed="false">{chip_old}</button>'
    assert html.count(old) == 1
    return html.replace(old, f'<button type="button" class="chip" aria-pressed="false">{chip_new}</button>')
