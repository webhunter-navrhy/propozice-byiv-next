import collections
def y2_counts(y2,F):
    out=[]
    for c in y2:
        s=c['slug']
        if s=='novinky': n=sum(1 for p in F if p['novinka'])
        elif s=='slevy': n=sum(1 for p in F if p['vyprodej'] or (p['puvodni'] and p['puvodni']>p['cena']))
        else: n=sum(1 for p in F if p['kategorie']==s)
        out.append({**c,'pocet':n})
    return out
def xB_derive(xB,F,y2):
    kn={c['slug']:c['nazev'] for c in y2}
    out=[]
    for r in xB:
        P=sorted([p for p in F if p['rada']==r['nazev']],key=lambda p:p['poradi'])
        mc=collections.Counter(p['material'] for p in P if p['material'])
        kc=collections.Counter(kn[p['kategorie']] for p in P)
        mats=[m for m,_ in mc.most_common(3)]
        e=dict(r)
        if not P:   # nová řada bez modelů
            e.update(pocet=0,material=None,materialy=[],kategorie=[],cenaOd=0,cenaDo=0,ukazka='')
            out.append(e); continue
        e.update(pocet=len(P),material=mats[0] if mats else None,materialy=mats,
          kategorie=[k for k,_ in kc.most_common(3)],cenaOd=min(p['cena'] for p in P),cenaDo=max(p['cena'] for p in P),ukazka=P[0]['slug'])
        out.append(e)
    return out
