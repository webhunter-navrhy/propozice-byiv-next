import collections
def cap(s): return s[:1].upper()+s[1:]
def enrich(F):
    """p z RSC = položka dat + barva/varianty (skupina podle názvu před ' – ')"""
    grp=collections.defaultdict(list)
    for p in F:
        if ' – ' in p['nazev']: grp[p['nazev'].split(' – ')[0]].append(p)
    out={}
    for p in F:
        e=dict(p)
        g=grp.get(p['nazev'].split(' – ')[0]) if ' – ' in p['nazev'] else None
        if g and len(g)>1:
            g=sorted(g,key=lambda q:q['poradi'])
            e['barva']=cap(p['nazev'].split(' – ',1)[1])
            e['varianty']=[{'slug':q['slug'],'barva':cap(q['nazev'].split(' – ',1)[1])} for q in g]
        out[p['slug']]=e
    return out
