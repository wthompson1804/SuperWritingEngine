"""Evidence batch 14: turn cached pages listed in the scratch fetch log into plain text files for reading (no network)."""
import json,re,html as H,sys,hashlib
S='/tmp/claude-0/-home-user-SuperWritingEngine/8b31bcc0-2748-5d89-ba10-9e09ecbeef66/scratchpad/b14/'
def text(path):
    t=open(path,encoding='utf-8',errors='replace').read()
    t=re.sub(r'<script.*?</script>|<style.*?</style>|<svg.*?</svg>','',t,flags=re.S)
    t=re.sub(r'<(br|/p|/div|/li|/h\d|/tr)[^>]*>','\n',t)
    t=H.unescape(re.sub(r'<[^>]+>',' ',t)); t=re.sub(r'[ \t]+',' ',t); return re.sub(r'\n\s*\n+','\n',t)
if __name__=='__main__':
    for line in open(S+'fetch1.log'):
        try: u,st,n,path,ts=json.loads(line)
        except Exception: continue
        if st!=200 or 'trulia.com' in u: continue
        fn=S+'txt_'+re.sub(r'[^a-z0-9]+','_',u.split('//')[1].lower())[:70]+'.txt'
        open(fn,'w').write(text(path)); print(fn.split('/')[-1],len(open(fn).read()))
