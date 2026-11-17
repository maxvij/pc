"""Fetch a big PC games dataset from SteamSpy (tags, reviews, playtime) and the Steam
store (release date, header art). Resumable: every response is cached under CACHE.

usage: python3 fetch_games.py CACHE_DIR [pages=4] [limit=1500]
"""
import json, os, re, sys, threading, time, urllib.request, urllib.parse

CACHE = sys.argv[1]
PAGES = int(sys.argv[2]) if len(sys.argv) > 2 else 4
LIMIT = int(sys.argv[3]) if len(sys.argv) > 3 else 1500
MIN_REVIEWS, MIN_RATIO = 2500, 0.75
os.makedirs(f"{CACHE}/spy", exist_ok=True); os.makedirs(f"{CACHE}/store", exist_ok=True)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def get(url, tries=4):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "pc-games-quiz/1.0"})
            with urllib.request.urlopen(req, timeout=90) as r:
                return json.load(r)
        except Exception as e:
            print("retry", url, e, file=sys.stderr, flush=True); time.sleep(8 * (i + 1))
    return None

def rating(pos, neg):
    """SteamDB-style rating: pulls low-review games towards 50%."""
    import math
    n = pos + neg; r = pos / n
    return r - (r - 0.5) * 2 ** (-math.log10(n + 1))

# 1. Candidates from the owner-sorted "all" pages (1 request per minute).
cands = {}
for p in range(PAGES):
    path = f"{CACHE}/all{p}.json"
    if not os.path.exists(path):
        d = get(f"https://steamspy.com/api.php?request=all&page={p}")
        json.dump(d or {}, open(path, "w"))
        if p < PAGES - 1: time.sleep(61)
    for k, v in json.load(open(path)).items():
        pos, neg = v.get("positive", 0), v.get("negative", 0)
        if pos + neg >= MIN_REVIEWS and pos / (pos + neg) >= MIN_RATIO:
            cands[int(k)] = rating(pos, neg)
ids = sorted(cands, key=lambda k: -cands[k])[:LIMIT]
# Always include the hand-tagged games.
html = open(f"{ROOT}/games.html").read()
hand = [int(x) for x in re.findall(r'^\["[^\n]*?",(\d+),', html, re.M) if int(x)]
ids = list(dict.fromkeys(hand + ids))
json.dump(ids, open(f"{CACHE}/ids.json", "w"))
print("fetching", len(ids), "games", file=sys.stderr, flush=True)

# 2. Details, two hosts in parallel, each at its own polite rate.
def spy():
    for i, a in enumerate(ids):
        f = f"{CACHE}/spy/{a}.json"
        if os.path.exists(f): continue
        d = get(f"https://steamspy.com/api.php?request=appdetails&appid={a}")
        if d: json.dump(d, open(f, "w"))
        if i % 100 == 0: print("spy", i, file=sys.stderr, flush=True)
        time.sleep(1.05)

def store():
    for i, a in enumerate(ids):
        f = f"{CACHE}/store/{a}.json"
        if os.path.exists(f): continue
        d = get(f"https://store.steampowered.com/api/appdetails?appids={a}&cc=nz&l=english")
        if d is None: time.sleep(60); continue
        x = d.get(str(a), {})
        keep = {}
        if x.get("success"):
            x = x["data"]
            keep = {k: x.get(k) for k in ("type", "name", "release_date", "header_image", "is_free", "metacritic", "genres", "categories")}
        json.dump(keep, open(f, "w"))
        if i % 100 == 0: print("store", i, file=sys.stderr, flush=True)
        time.sleep(1.6)

ts = [threading.Thread(target=spy), threading.Thread(target=store)]
[t.start() for t in ts]; [t.join() for t in ts]
print("done", file=sys.stderr, flush=True)
