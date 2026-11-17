"""Which neighborhood wins when she cares about only one thing, or two things equally?"""
import json, sys, itertools
sys.path.insert(0, "/home/user/SuperWritingEngine/house-hunt/scripts")
import recommender as R
D = json.load(open("/home/user/SuperWritingEngine/house-hunt/site/concierge_data.json"))
P = D["meta"]["recommender"]; B = D["buildings"]; F = P["features"]
def best(w):
    gs = R.group_scores(w, B, P)
    return sorted(gs, key=lambda g: (-gs[g], g))[0]
print("only one thing matters:")
for i, f in enumerate(F):
    w = [0.0] * len(F); w[i] = 1.0
    print("  ", f, "->", best(w))
wins = {}
for i, j in itertools.combinations(range(len(F)), 2):
    w = [0.0] * len(F); w[i] = w[j] = 0.5
    wins.setdefault(best(w), []).append(F[i] + "+" + F[j])
print("two things equally (15 pairs):")
for g, v in sorted(wins.items(), key=lambda x: -len(x[1])):
    print("  ", g, len(v), v)
