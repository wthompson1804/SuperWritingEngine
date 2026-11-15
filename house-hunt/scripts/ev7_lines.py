"""Evidence batch 7 helper: print visible-text lines of a cached page that match a regex (deduped). Usage: ev7_lines.py <path> <regex> [maxchars]"""
import sys, re
sys.path.insert(0, 'scripts')
import ev6_text as T
def lines(path, rx, mx=400):
    seen = []
    for l in T.text(path).split('\n'):
        if re.search(rx, l, re.I) and l not in seen:
            seen.append(l)
    return [l[:mx] for l in seen]
if __name__ == '__main__':
    for l in lines(sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 400): print('  -', l)
