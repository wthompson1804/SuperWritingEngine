"""How much does the result change from person to person (with her exact weights, the best the quiz could do)?"""
import json, random, sys, collections, statistics
sys.path.insert(0, "/home/user/SuperWritingEngine/house-hunt/scripts")
import recommender as R

D = json.load(open("/home/user/SuperWritingEngine/house-hunt/site/concierge_data.json"))
P = D["meta"]["recommender"]; B = D["buildings"]; S = D["recommender_samples"]; feats = P["features"]
def rec(w):
    r = R.recommend_from_weights(w, B, P)
    return [n["neighborhood_id"] for n in r["neighborhoods"]], [b["id"] for n in r["neighborhoods"] for b in n["buildings"]]
prior = [statistics.mean(s[i] for s in S) for i in range(len(feats))]
H0, B0 = rec(prior)
rng = random.Random(11)
same_hoods = same_set = same_order = 0; bdiff = []; firsts = collections.Counter(); sets = collections.Counter()
for _ in range(200):
    g = [rng.gammavariate(1.0, 1.0) for _ in feats]; s = sum(g); w = [x / s for x in g]
    H, Bs = rec(w)
    same_set += set(H) == set(H0); same_order += H == H0
    bdiff.append(len(set(Bs) - set(B0))); firsts[H[0]] += 1; sets[tuple(sorted(H))] += 1
print("default three:", H0)
print("same three neighborhoods as the default:", same_set / 2, "%; same order too:", same_order / 2, "%")
print("buildings different from the default nine: median", statistics.median(bdiff), "; share with >=3 different:", sum(d >= 3 for d in bdiff) / 2, "%")
print("first place:", firsts.most_common())
print("distinct three-sets:", len(sets), sets.most_common(5))
