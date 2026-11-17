"""Turn the cached SteamSpy + Steam store data into games-data.js.

Each game's Steam user tags come with vote counts. A tag's strength is its votes
divided by the top tag's votes (0..1). Traits are weighted sums of tag strengths,
squashed to 0..3, so they line up with the hand-tagged rows in games.html.
Hand-tagged games keep their hand traits; everything else is derived.

usage: python3 build_games.py CACHE_DIR
"""
import json, math, os, re, sys

CACHE = sys.argv[1]
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIMS = "s a t x c z b r g h k".split()

# trait -> {tag: weight}. Negative weights pull a trait down.
TRAIT_TAGS = {
    "s": {"Story Rich": 1.2, "Narrative": .8, "Choices Matter": .8, "Multiple Endings": .5, "Visual Novel": 1,
          "Interactive Fiction": 1, "Lore-Rich": .5, "Emotional": .6, "Cinematic": .5, "Dialogue": .5, "Detective": .4,
          "CRPG": .5, "JRPG": .5, "Walking Simulator": .6,
          "Arcade": -.5, "PvP": -.6, "Sandbox": -.4, "Racing": -.6, "Sports": -.6, "Competitive": -.6, "Score Attack": -.5,
          "Automation": -.5, "Puzzle": -.2, "Building": -.3, "Battle Royale": -.8, "MOBA": -.8},
    "a": {"Action": .7, "FPS": 1, "Fast-Paced": 1, "Shooter": .8, "Hack and Slash": 1, "Bullet Hell": 1, "Fighting": 1,
          "Twin Stick Shooter": .9, "Character Action Game": 1, "Precision Platformer": .9, "Racing": .6, "Arcade": .5,
          "Shoot 'Em Up": 1, "Beat 'em up": .9, "Spectacle fighter": 1, "Souls-like": .6, "Action Roguelike": .8,
          "Turn-Based": -1, "Turn-Based Strategy": -1, "Turn-Based Tactics": -1, "Card Game": -.8, "Puzzle": -.6,
          "Walking Simulator": -1, "Visual Novel": -1, "City Builder": -.8, "Management": -.6, "Grand Strategy": -.8,
          "Relaxing": -.5, "Point & Click": -.8},
    "t": {"Strategy": .9, "Turn-Based Tactics": 1, "Tactical": .7, "Puzzle": .9, "4X": 1, "Grand Strategy": 1,
          "RTS": .9, "Deckbuilding": .9, "Management": .8, "Logic": .9, "Automation": 1, "Card Game": .7,
          "Economy": .7, "Resource Management": .7, "Turn-Based Strategy": 1, "Colony Sim": .8, "City Builder": .6,
          "Investigation": .6, "Tactical RPG": .9, "Roguelike Deckbuilder": .9, "Programming": 1, "Political Sim": .7,
          "Hack and Slash": -.4, "Bullet Hell": -.2, "Walking Simulator": -.4, "Shooter": -.3, "Casual": -.3},
    "x": {"Open World": 1.2, "Exploration": .9, "Sandbox": .6, "Open World Survival Craft": 1, "Space Sim": .5,
          "Survival": .4, "Metroidvania": .4, "Linear": -1, "Puzzle": -.4, "Card Game": -.6, "Arena Shooter": -.6,
          "Fighting": -.8, "Score Attack": -.6, "Roguelike Deckbuilder": -.6},
    "c": {"Difficult": 1.3, "Souls-like": 1.2, "Precision Platformer": 1, "Permadeath": .6, "Competitive": .6,
          "Roguelike": .4, "Roguelite": .3, "Bullet Hell": .6, "Hardcore": .5, "Tactical": .3, "Unforgiving": 1,
          "Relaxing": -1, "Casual": -1, "Cozy": -1, "Family Friendly": -.6, "Wholesome": -.8, "Walking Simulator": -1,
          "Visual Novel": -.8, "Cute": -.4, "Life Sim": -.6},
    "z": {"Relaxing": 1.2, "Casual": .8, "Cozy": 1.2, "Cute": .6, "Wholesome": 1, "Farming Sim": .9, "Life Sim": .7,
          "Walking Simulator": .6, "Family Friendly": .5, "Beautiful": .3, "Building": .2, "Atmospheric": .2,
          "Horror": -1, "Psychological Horror": -1, "Survival Horror": -1, "Difficult": -.8, "Gore": -.8, "Violent": -.6,
          "Fast-Paced": -.8, "PvP": -.7, "Competitive": -.9, "Souls-like": -1, "Bullet Hell": -.8, "Battle Royale": -1},
    "b": {"Building": 1.1, "Base Building": 1.1, "Crafting": .7, "City Builder": 1.2, "Colony Sim": 1, "Automation": 1.2,
          "Sandbox": .7, "Level Editor": .5, "Open World Survival Craft": .8, "Design & Illustration": .6,
          "Management": .4, "Voxel": .4, "Base-Building": 1.1, "Farming Sim": .5},
    "r": {"Realistic": 1.2, "Simulation": .8, "Military": .5, "Tactical": .3, "Physics": .5, "Historical": .4,
          "Automobile Sim": 1, "Flight": .5, "Driving": .4, "Immersive Sim": .2, "Hunting": .5, "Sports": .2,
          "Arcade": -.9, "Cartoony": -.9, "Cute": -.7, "Anime": -.6, "Stylized": -.6, "Pixel Graphics": -.6,
          "Fantasy": -.3, "Magic": -.4, "Comedy": -.4, "Funny": -.4, "Colorful": -.4, "Hand-drawn": -.6, "Superhero": -.5},
    "g": {"Realistic": .6, "Beautiful": .6, "Photorealistic": 1, "Open World": .3, "Cinematic": .5, "Atmospheric": .2,
          "3D": .2, "Third Person": .2,
          "Pixel Graphics": -1.2, "2D": -.8, "Retro": -.8, "Minimalist": -.8, "Old School": -.6, "Hand-drawn": -.4,
          "Text-Based": -1, "Top-Down": -.4, "Cartoony": -.3, "1990's": -.6, "Isometric": -.3, "Card Game": -.6},
    "k": {"Roguelike": .8, "Roguelite": .8, "Arcade": .9, "Casual": .6, "Score Attack": .9, "Racing": .7, "Sports": .7,
          "Fighting": .8, "Short": .7, "PvP": .5, "Party Game": .8, "Puzzle": .4, "Rhythm": .8, "Action Roguelike": .9,
          "Roguelike Deckbuilder": .8, "Battle Royale": .6, "Arena Shooter": .7, "Replay Value": .3,
          "Story Rich": -.7, "RPG": -.4, "Open World": -.5, "Grand Strategy": -.9, "CRPG": -.9, "JRPG": -.8,
          "4X": -.8, "Visual Novel": -.4, "Colony Sim": -.5, "Massively Multiplayer": -.4},
}

# theme/genre tags for the page (match the THEMES table in games.html)
THEME_TAGS = {
    "bikes": ["Motorbike", "Bikes", "Cycling", "BMX", "Motocross"],
    "motor": ["Racing", "Automobile Sim", "Motorbike", "Offroad", "Driving", "Motocross"],
    "driving": ["Driving"],
    "racing": ["Racing"],
    "football": ["Football (Soccer)"],
    "sport": ["Sports", "Football (Soccer)", "Basketball", "Golf", "Tennis", "Skateboarding", "Snowboarding", "Skiing",
              "Boxing", "Baseball", "Hockey", "Cycling", "Extreme Sports", "Mini Golf", "Wrestling",
              "Football (American)", "Rugby", "Cricket", "Bowling", "Pool", "Martial Arts", "Snooker", "Volleyball"],
    "fantasy": ["Fantasy", "Dark Fantasy", "Magic", "Dragons", "Mythology"],
    "scifi": ["Sci-fi", "Cyberpunk", "Futuristic", "Aliens", "Robots", "Mechs", "Post-apocalyptic", "Space"],
    "space": ["Space", "Space Sim"],
    "history": ["Historical", "Medieval", "World War II", "World War I", "Cold War", "Alternate History", "Western",
                "Pirates", "Rome", "Vikings", "Feudal Japan"],
    "war": ["War", "Military", "World War II", "World War I", "Tanks", "Naval Combat"],
    "modern": ["Modern"],
    "crime": ["Crime", "Heist", "Mafia", "Police"],
    "city": ["City Builder", "Urban"],
    "nature": ["Nature", "Open World Survival Craft", "Hunting", "Fishing", "Farming", "Underwater"],
    "cozy": ["Cozy", "Relaxing", "Wholesome", "Farming Sim", "Life Sim"],
    "anime": ["Anime", "JRPG", "Visual Novel"],
    "mystery": ["Mystery", "Detective", "Investigation"],
    "puzzle": ["Puzzle", "Logic"],
    "horror": ["Horror", "Survival Horror", "Psychological Horror"],
}
GENRE_ORDER = [
    ("soulslike", ["Souls-like"]), ("roguelike", ["Roguelike", "Roguelite", "Action Roguelike", "Roguelike Deckbuilder"]),
    ("metroidvania", ["Metroidvania"]), ("racing", ["Racing"]), ("sport", ["Sports"]), ("fighting", ["Fighting"]),
    ("city-builder", ["City Builder"]), ("management", ["Colony Sim", "Management"]),
    ("strategy", ["Grand Strategy", "4X", "RTS", "Strategy"]), ("tactics", ["Turn-Based Tactics", "Tactical RPG"]),
    ("cards", ["Card Game", "Deckbuilding"]), ("puzzle", ["Puzzle"]), ("horror", ["Survival Horror", "Horror"]),
    ("survival", ["Open World Survival Craft", "Survival"]), ("shooter", ["FPS", "Shooter"]),
    ("platformer", ["Platformer"]), ("rpg", ["RPG", "CRPG", "JRPG", "Action RPG"]), ("sim", ["Simulation"]),
    ("sandbox", ["Sandbox"]), ("narrative", ["Walking Simulator", "Visual Novel", "Story Rich"]),
    ("stealth", ["Stealth"]), ("immersive", ["Immersive Sim"]),
]
NOT_GAMES = {"Utilities", "Software", "Design & Illustration", "Animation & Modeling", "Video Production",
             "Audio Production", "Game Development", "Photo Editing", "Web Publishing", "Education", "Software Training"}
ADULT = {"Sexual Content", "Nudity", "Hentai", "NSFW", "Mature"}


def load(path):
    try:
        return json.load(open(path))
    except Exception:
        return None


def strengths(tags):
    if not isinstance(tags, dict) or not tags:
        return {}
    top = max(tags.values()) or 1
    return {k: v / top for k, v in tags.items()}


def squash(x, lo, hi):
    """Map a raw score onto 0..3."""
    return max(0, min(3, round((x - lo) / (hi - lo) * 3)))


def raw_traits(st, median_min, year):
    """Raw, unscaled score per trait from tag strengths (plus playtime and year)."""
    out = {d: sum(w * st.get(t, 0) for t, w in TRAIT_TAGS[d].items()) for d in "satxczbrgk"}
    out["g"] += (year - 2016) / 8 if year else 0
    hrs = (median_min or 0) / 60
    endless = any(st.get(t, 0) > .4 for t in ("Massively Multiplayer", "Replay Value", "Sandbox", "Grand Strategy", "Automation", "MOBA"))
    out["h"] = math.log1p(hrs) + (1 if endless else 0)
    return [out[d] for d in DIMS]


def calibrate(pairs):
    """Quantile mapping per trait: a derived game lands on the hand-tag value at the same
    percentile of raw scores among the hand-tagged games. Keeps the 0-3 spread honest."""
    maps = []
    for i in range(len(DIMS)):
        raws = sorted(r[i] for r, _ in pairs)
        vals = sorted(int(h[i]) for _, h in pairs)
        maps.append((raws, vals))
    def apply(raw):
        out = ""
        for i, x in enumerate(raw):
            raws, vals = maps[i]
            # percentile of x among hand raws -> hand value at that percentile
            lo, hi = 0, len(raws)
            while lo < hi:
                mid = (lo + hi) // 2
                if raws[mid] < x: lo = mid + 1
                else: hi = mid
            out += str(vals[min(lo, len(vals) - 1)])
        return out
    return apply


def modes(st, store):
    cats = {c["description"] for c in (store or {}).get("categories") or []}
    m = ""
    if st.get("Singleplayer", 0) > .15 or "Single-player" in cats: m += "S"
    if any(st.get(t, 0) > .15 for t in ("Co-op", "Online Co-Op", "Local Co-Op", "Massively Multiplayer")) or {"Online Co-op", "Co-op", "LAN Co-op"} & cats: m += "C"
    if any(st.get(t, 0) > .2 for t in ("PvP", "Competitive", "eSports", "Battle Royale", "MOBA", "Online PvP")) or "Online PvP" in cats and st.get("Singleplayer", 0) < .5: m += "P"
    return m or "S"


def rating(pos, neg):
    n = pos + neg
    r = pos / n
    return r - (r - 0.5) * 2 ** (-math.log10(n + 1))


def year_of(store):
    m = re.search(r"(19|20)\d\d", ((store or {}).get("release_date") or {}).get("date") or "")
    return int(m.group(0)) if m else None


def main():
    ids = load(f"{CACHE}/ids.json") or []
    html = open(f"{ROOT}/hand-tags.js").read()
    hand = {}
    for m in re.finditer(r'^\["(.*?)",(\d+),(\d+),"(\d{11})","([SCP]+)","([^"]*)",(\d+)\],?$', html, re.M):
        hand[int(m.group(2))] = m.groups()

    pairs = []
    rows, errs, skipped = [], [], {"missing": 0, "not-game": 0, "adult": 0, "vr": 0}
    for a in ids:
        spy, store = load(f"{CACHE}/spy/{a}.json"), load(f"{CACHE}/store/{a}.json")
        if not spy or not spy.get("name"):
            skipped["missing"] += 1; continue
        st = strengths(spy.get("tags"))
        top3 = sorted(st, key=lambda k: -st[k])[:3]
        if (store or {}).get("type") not in (None, "game") or NOT_GAMES & set(top3):
            skipped["not-game"] += 1; continue
        # Drop games that are mainly adult content; plenty of mainstream RPGs carry a Nudity tag.
        if a not in hand and (any(st.get(t, 0) > .2 for t in ("Hentai", "NSFW")) or top3[0] in ADULT
                              or (st.get("Sexual Content", 0) > .5 and max(st.get("Dating Sim", 0), st.get("Visual Novel", 0)) > .5)):
            skipped["adult"] += 1; continue
        if "VR" in top3 or "VR Only" in st:
            skipped["vr"] += 1; continue
        pos, neg = spy.get("positive", 0), spy.get("negative", 0)
        if pos + neg == 0:
            skipped["missing"] += 1; continue
        q = round(rating(pos, neg) * 100)
        year = year_of(store) or None
        raw = raw_traits(st, spy.get("median_forever"), year)

        tagset = []
        for gname, gtags in GENRE_ORDER:
            if any(st.get(t, 0) > .3 for t in gtags):
                tagset.append(gname); break
        else:
            tagset.append("action")
        for theme, ttags in THEME_TAGS.items():
            if any(st.get(t, 0) > .3 for t in ttags) and theme not in tagset:
                tagset.append(theme)
        if st.get("Indie", 0) > .3: tagset.append("indie")
        if (store or {}).get("is_free") or st.get("Free to Play", 0) > .4: tagset.append("f2p")

        name = (store or {}).get("name") or spy["name"]
        md = modes(st, store)
        derived = None
        if a in hand:
            h = hand[a]
            pairs.append((raw, h[3]))
            name, year, derived, md, tagset = h[0], int(h[2]), h[3], h[4], h[5].split(",")
        if not year:
            continue
        img = (store or {}).get("header_image") or ""
        m = re.search(r"/header(_[^.]*)?\.jpg(\?t=\d+)?", img)
        # store only the bit that differs from the default header URL (hashed paths on newer apps)
        art = "" if not img or re.search(rf"/apps/{a}/header\.jpg", img) else img.split("/apps/")[-1].split("?")[0]
        rows.append([name, a, year, derived, md, ",".join(tagset), q, round(math.log10(pos + neg), 2), art, raw])

    # Calibrate on the hand-tagged games, then score them with leave-one-out to report honest error.
    apply = calibrate(pairs)
    for i, (raw, h) in enumerate(pairs):
        pred = calibrate(pairs[:i] + pairs[i + 1:])(raw)
        errs.append(sum(abs(int(x) - int(y)) for x, y in zip(h, pred)) / 11)
    for r in rows:
        if r[3] is None:
            r[3] = apply(r[9])
        r.pop()
    rows.sort(key=lambda r: (-r[6], r[0]))
    out = ("/* Generated by scripts/build_games.py from SteamSpy + Steam store data. Do not edit by hand.\n"
           "   [name, steamAppId, year, traits, modes, tags, steamRating, log10(reviews), art] */\n"
           "window.GAMES_DB = " + json.dumps(rows, ensure_ascii=False, separators=(",", ":")).replace("],[", "],\n[") + ";\n")
    open(f"{ROOT}/games-data.js", "w").write(out)
    mae = sum(errs) / len(errs) if errs else 0
    print(f"wrote {len(rows)} games; skipped {skipped}; hand-vs-derived mean abs error {mae:.2f} steps (of 0-3, leave-one-out) over {len(errs)} games",
          file=sys.stderr)


if __name__ == "__main__":
    main()
