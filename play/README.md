# whatto.play

Tell it what you like, and it ranks 1,000+ Steam games by how well they fit. Static site, no build step, no sign-up; everything you enter stays in your browser.

## Files

- `index.html`: the app (UI, scoring, live prices).
- `games-data.js`: generated catalogue, `window.GAMES_DB`. Don't edit by hand.
- `hand-tags.js`: ~190 hand-tagged games, `window.HAND`. They override derived traits and calibrate the rest.
- `scripts/fetch_games.py`: pulls candidates and details from SteamSpy and the Steam store into a cache folder (resumable, ~40 min).
- `scripts/build_games.py`: turns the cache into `games-data.js`.

## How scoring works

Each game has 11 traits scored 0–3: story, reflexes, thinking, open world, challenge, chill, building, realism, graphics, length, short sessions. Derived games get them from Steam user-tag votes (weighted per trait) and median playtime, then quantile-mapped onto the hand-tag distribution. Leave-one-out error against the hand tags is about 0.5 steps.

Your settings become weights in −1..+1. Score = trait fit (weighted agreement) + similarity to loved games (cosine) + theme bonus + small adjustments + Steam rating. The list is picked greedily with a small penalty for repeated genres.

## Refresh the data

Needs network access to `steamspy.com` and `store.steampowered.com`.

```sh
python3 scripts/fetch_games.py /path/to/cache 4 1500   # pages of SteamSpy "all", max games
python3 scripts/build_games.py /path/to/cache
```

## Data

SteamSpy, the Steam store, and CheapShark (live prices, from the browser). Cover art © the respective publishers. Not affiliated with Valve.
