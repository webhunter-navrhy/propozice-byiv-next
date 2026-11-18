"""Serializace dat do minifikovaného JS literálu jako v chunku 653 (modul 2525)."""
import re
def jstr(s, raw=False):
    q="'" if s.count('"')>s.count("'") else '"'
    o=q
    for ch in s:
        c=ord(ch)
        if ch==q: o+='\\'+q
        elif ch=='\\': o+='\\\\'
        elif ch=='\n': o+='\\n'
        elif ch=='\r': o+='\\r'
        elif ch=='\t': o+='\\t'
        elif 0x80<=c<=0xff and not raw: o+='\\x%02x'%c
        elif c<0x20: o+='\\x%02x'%c
        else: o+=ch
    return o+q
def js(v, raw=False):
    if v is None: return 'null'
    if v is True: return '!0'
    if v is False: return '!1'
    if isinstance(v,(int,float)): return str(v)
    if isinstance(v,str): return jstr(v,raw)
    if isinstance(v,list): return '['+','.join(js(x,raw) for x in v)+']'
    if isinstance(v,dict): return '{'+','.join(f'{k}:{js(x,raw)}' for k,x in v.items())+'}'
    raise TypeError(v)
def module(y2,xB,LD,Fz):
    return f'let i={js(y2,True)},n={js(xB)},s={js(LD)},l={js(Fz)}'
def replace_module(chunk,y2,xB,LD,Fz):
    a=chunk.index('2525:(a,e,o)=>{o.d(e,{Fz:()=>l,LD:()=>s,xB:()=>n,y2:()=>i});')
    a=chunk.index('let i=',a); b=chunk.index('}}]);',a) if chunk.rstrip().endswith('}}]);') else None
    return chunk[:a]+module(y2,xB,LD,Fz)+chunk[b:]
