"""Step 1: pull every game in SteamSpy's genre lists and keep the well-reviewed ones."""
import json, sys, time, urllib.request, urllib.parse

OUT = sys.argv[1]
GENRES = ["Action", "Adventure", "RPG", "Strategy", "Simulation", "Sports", "Racing",
          "Indie", "Casual", "Massively Multiplayer", "Free to Play", "Early Access"]
MIN_REVIEWS, MIN_RATIO = 2500, 0.75

def get(params):
    url = "https://steamspy.com/api.php?" + urllib.parse.urlencode(params)
    for attempt in range(4):
        try:
            with urllib.request.urlopen(url, timeout=120) as r:
                return json.load(r)
        except Exception as e:
            print("retry", params, e, file=sys.stderr); time.sleep(5 * (attempt + 1))
    return {}

seen = {}
for g in GENRES:
    data = get({"request": "genre", "genre": g})
    print(g, len(data), file=sys.stderr)
    for k, v in data.items():
        pos, neg = v.get("positive", 0), v.get("negative", 0)
        if pos + neg >= MIN_REVIEWS and pos / (pos + neg) >= MIN_RATIO:
            seen[int(k)] = {"name": v["name"], "pos": pos, "neg": neg}
    time.sleep(61)  # genre/all requests are limited to 1 per minute
json.dump(seen, open(OUT, "w"))
print("candidates", len(seen), file=sys.stderr)
