"""Dump visible text of a cached html file (evidence batch 6 helper)."""
import sys, re, html as H
def text(path):
    s=open(path,encoding='utf-8',errors='replace').read()
    s=re.sub(r'(?is)<(script|style|svg|noscript)\b.*?</\1>',' ',s)
    s=re.sub(r'(?s)<[^>]+>','\n',s)
    s=H.unescape(s)
    lines=[l.strip() for l in s.split('\n')]
    return '\n'.join(l for l in lines if l)
if __name__=='__main__':
    t=text(sys.argv[1])
    if len(sys.argv)>2:
        for m in re.finditer(sys.argv[2],t,re.I):
            a=max(0,m.start()-int(sys.argv[3]) if len(sys.argv)>3 else m.start()-150); print('...',t[a:m.end()+ (int(sys.argv[3]) if len(sys.argv)>3 else 150)].replace('\n',' | '))
    else: print(t)
