"""Does the recommender learn anything? Compare against recommending the same three to everyone."""
import json, random, sys, collections, statistics
sys.path.insert(0, "/home/user/SuperWritingEngine/house-hunt/scripts")
import recommender as R

D = json.load(open("/home/user/SuperWritingEngine/house-hunt/site/concierge_data.json"))
P = D["meta"]["recommender"]
B = D["buildings"]
S = D["recommender_samples"]
feats = P["features"]

def true_best(w):
    gs = R.group_scores(w, B, P)
    return sorted(gs, key=lambda g: (-gs[g], g))[0], gs

def top3_of(w):
    r = R.recommend_from_weights(w, B, P)
    return [n["neighborhood_id"] for n in r["neighborhoods"]]

rng = random.Random(11)
users = []
for _ in range(200):
    g = [rng.gammavariate(1.0, 1.0) for _ in feats]
    s = sum(g)
    users.append([x / s for x in g])

prior = [statistics.mean(s[i] for s in S) for i in range(len(feats))]
fixed = top3_of(prior)
gs_any = R.group_scores(prior, B, P)
popular = collections.Counter()
for w in users:
    popular[true_best(w)[0]] += 1
pop3 = [g for g, _ in popular.most_common(3)]

def rate(pick):
    hit = within = 0
    for w in users:
        best, gs = true_best(w)
        three = pick(w)
        hit += best in three
        within += max(gs[g] for g in three) >= 0.98 * gs[best]
    return hit / len(users), within / len(users)

# perfect knowledge of her weights (the ceiling): recommend with her true weights
print("groups eligible:", len(R.group_scores(prior, B, P)))
print("true-best distribution (top 6):", popular.most_common(6))
print("A. same three for everyone, from what we assume before any answer:", fixed, rate(lambda w: fixed))
print("B. same three for everyone, the three most often best (hindsight):", pop3, rate(lambda w: pop3))
rr = random.Random(5)
el = list(R.group_scores(prior, B, P))
print("C. three at random:", rate(lambda w: rr.sample(el, 3)))
print("D. ceiling, her exact weights known:", rate(lambda w: top3_of(w)))
