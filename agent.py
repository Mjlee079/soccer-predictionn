"""
Soccer Match Prediction Agent
==============================
Fetches REAL match data from football.api-sports.io
and predicts outcomes using a multi-factor algorithm.

Setup:
  $env:FOOTBALL_API_KEY = 'your_key'
  py agent.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from api_client import search_teams, get_last_n, get_h2h, get_upcoming, get_finished_matches
from predictor import predict, _fin, _result, _gf, _ga

BANNER = r"""
 ____                          ____               _ _      _
/ ___|  ___   ___ ___ ___ _ __|  _ \ _ __ ___  __| (_) ___| |_ ___  _ __
\___ \ / _ \ / __/ __/ _ \ '__| |_) | '__/ _ \/ _` | |/ __| __/ _ \| '__|
 ___) | (_) | (_| (_|  __/ |  |  __/| | |  __/ (_| | | (__| || (_) | |
|____/ \___/ \___\___\___|_|  |_|   |_|  \___|\__,_|_|\___|\__\___/|_|

       AI Soccer Match Predictor  -  Live Football API Data
"""

def div():  print("=" * 62)
def thin(): print("-" * 62)


def pick_team(label="Team"):
    q = input(f"\n  Search {label}: ").strip()
    if not q:
        return None
    print(f"  Searching '{q}'...")
    results = search_teams(q)
    if not results:
        print("  [!] No teams found.")
        return None
    # Filter to show top 10
    shown = results[:10]
    print()
    for i, t in enumerate(shown, 1):
        print(f"    {i:>2}. {t['name']}  ({t['country']})")
    try:
        c = int(input(f"\n  Pick [1-{len(shown)}]: "))
        if 1 <= c <= len(shown):
            team = shown[c - 1]
            print(f"  -> {team['name']}")
            return team
    except ValueError:
        pass
    print("  [!] Invalid.")
    return None


# ─────────────────────────────────────────────────────────
# 1. PREDICT
# ─────────────────────────────────────────────────────────
def do_predict():
    div()
    print("  MATCH PREDICTION")
    div()

    home = pick_team("Home Team")
    if not home: return
    away = pick_team("Away Team")
    if not away: return

    print(f"\n  Fetching data...")
    print(f"  - {home['name']} recent matches...")
    hm = get_last_n(home["id"], 15)
    print(f"    {len(hm)} matches loaded")

    print(f"  - {away['name']} recent matches...")
    am = get_last_n(away["id"], 15)
    print(f"    {len(am)} matches loaded")

    print(f"  - Head-to-head...")
    h2h = get_h2h(home["id"], away["id"])
    print(f"    {len(h2h)} H2H matches found")

    print("\n  Running prediction...\n")
    r = predict(home["name"], away["name"], hm, am, h2h)

    # ── Output ──
    div()
    print(f"  {r['home']}  vs  {r['away']}")
    div()

    print(f"\n  Predicted Score:  {r['home']} {r['pred_hg']} - {r['pred_ag']} {r['away']}")

    print(f"\n  Probabilities:")
    print(f"    {r['home']:<28} WIN : {r['home_win']:>5.1f}%")
    print(f"    {'DRAW':<28}     : {r['draw']:>5.1f}%")
    print(f"    {r['away']:<28} WIN : {r['away_win']:>5.1f}%")

    print(f"\n  >>> VERDICT: {r['verdict']} <<<")
    c = r["confidence"]
    print(f"  Confidence: [{'+'*(c//5)}{'-'*(20-c//5)}] {c}%")

    d = r["data_used"]
    print(f"\n  Data: {d['home']} home, {d['away']} away, {d['h2h']} H2H matches")

    # Factor table
    f = r["factors"]
    print(f"\n  Factor Breakdown:")
    thin()
    print(f"  {'Factor':<20} {'Home':>8}  {'Away':>8}  {'Weight':>6}")
    thin()
    labels = [
        ("Recent Form",  "form",    "25%"),
        ("Head-to-Head",  "h2h",    "20%"),
        ("Attack (GF)",   "attack", "15%"),
        ("Defence (GA)",  "defence","15%"),
        ("Venue Split",   "venue",  "15%"),
        ("GD Momentum",   "gd",     "10%"),
    ]
    for lbl, key, wt in labels:
        h, a = f[key]
        print(f"  {lbl:<20} {h:>8}  {a:>8}  {wt:>6}")
    thin()
    ch, ca = f["composite"]
    print(f"  {'COMPOSITE':<20} {ch:>8}  {ca:>8}")

    # Recent results
    for side, team in [("home", home), ("away", away)]:
        matches = hm if side == "home" else am
        fin = _fin(matches)[:5]
        if fin:
            print(f"\n  {team['name']} - Recent:")
            for m in fin:
                res = _result(m, team["name"])
                tag = {"W": "WIN ", "D": "DRAW", "L": "LOSS"}[res]
                print(f"    [{tag}]  {m['home']} {m['home_goals']}-{m['away_goals']} {m['away']}  ({m['date']})  {m['league']}")

    if h2h:
        print(f"\n  Head-to-Head:")
        for m in h2h[:5]:
            print(f"    {m['home']} {m['home_goals']}-{m['away_goals']} {m['away']}  ({m['date']})")
    print()


# ─────────────────────────────────────────────────────────
# 2. TEAM FORM
# ─────────────────────────────────────────────────────────
def do_form():
    div()
    print("  TEAM FORM")
    div()
    team = pick_team("Team")
    if not team: return

    print(f"\n  Loading {team['name']}...")
    matches = get_finished_matches(team["id"])
    if not matches:
        print("  [!] No match data found.")
        return

    matches.sort(key=lambda m: m["date"])
    w = sum(1 for m in matches if _result(m, team["name"]) == "W")
    d = sum(1 for m in matches if _result(m, team["name"]) == "D")
    l = len(matches) - w - d
    gf = sum(_gf(m, team["name"]) for m in matches)
    ga = sum(_ga(m, team["name"]) for m in matches)
    n = len(matches)

    home_m = [m for m in matches if m["home"] == team["name"]]
    away_m = [m for m in matches if m["away"] == team["name"]]
    hw = sum(1 for m in home_m if _result(m, team["name"]) == "W")
    aw = sum(1 for m in away_m if _result(m, team["name"]) == "W")

    print()
    div()
    print(f"  {team['name']}  ({team['country']})  -  {n} matches")
    div()
    print(f"  Record:     W {w}  D {d}  L {l}  ({w/n:.3f})")
    print(f"  Goals:      {gf} scored  {ga} conceded  (GD {gf-ga:+d})")
    print(f"  Per Game:   {gf/n:.1f} GF   {ga/n:.1f} GA   {(gf-ga)/n:+.1f} avg margin")
    print(f"  Home:       {hw}-{len(home_m)-hw} ({hw/len(home_m):.3f})" if home_m else "")
    print(f"  Away:       {aw}-{len(away_m)-aw} ({aw/len(away_m):.3f})" if away_m else "")

    last5 = matches[-5:]
    if last5:
        streak = "".join({"W":"W","D":"D","L":"L"}[_result(m, team["name"])] for m in last5)
        print(f"\n  Last 5: [{streak}]")
        for m in reversed(last5):
            res = _result(m, team["name"])
            tag = {"W": "WIN ", "D": "DRAW", "L": "LOSS"}[res]
            print(f"    [{tag}]  {m['home']} {m['home_goals']}-{m['away_goals']} {m['away']}  ({m['date']})  {m['league']}")
    print()


# ─────────────────────────────────────────────────────────
# 3. UPCOMING + QUICK PREDICT
# ─────────────────────────────────────────────────────────
def do_upcoming():
    div()
    print("  UPCOMING FIXTURES")
    div()
    team = pick_team("Team")
    if not team: return

    print(f"\n  Loading schedule for {team['name']}...")
    fixtures = get_upcoming(team["id"], 5)
    if not fixtures:
        print("  [!] No upcoming fixtures found.")
        return

    print()
    for i, f in enumerate(fixtures, 1):
        venue = "HOME" if f["home"] == team["name"] else "AWAY"
        opp = f["away"] if venue == "HOME" else f["home"]
        print(f"    {i}. {f['date']}  [{venue}]  vs {opp}  ({f['league']})")

    yn = input("\n  Predict one? (y/n): ").strip().lower()
    if yn != "y": return

    try:
        idx = int(input(f"  Which? [1-{len(fixtures)}]: ")) - 1
        fx = fixtures[idx]
        h_id, a_id = fx["home_id"], fx["away_id"]
        print(f"\n  Predicting {fx['home']} vs {fx['away']}...")
        hm = get_last_n(h_id, 15)
        am = get_last_n(a_id, 15)
        h2h = get_h2h(h_id, a_id)
        r = predict(fx["home"], fx["away"], hm, am, h2h)
        print()
        div()
        print(f"  {r['home']} {r['pred_hg']} - {r['pred_ag']} {r['away']}")
        print(f"  {r['home']}: {r['home_win']}%   Draw: {r['draw']}%   {r['away']}: {r['away_win']}%")
        print(f"  >>> {r['verdict']} <<<  (Confidence: {r['confidence']}%)")
        div()
    except (ValueError, IndexError):
        print("  [!] Invalid selection.")
    print()


# ─────────────────────────────────────────────────────────
# MENU
# ─────────────────────────────────────────────────────────
def menu():
    div()
    print("  MAIN MENU")
    div()
    print("  1. Predict a match")
    print("  2. Team form & stats")
    print("  3. Upcoming fixtures + predict")
    print("  4. Exit")
    div()


def main():
    print(BANNER)
    try:
        from api_client import _get_api_key
        _get_api_key()
        print("  [OK] API key loaded.\n")
    except RuntimeError as e:
        print(f"  [!] {e}\n")
        return

    while True:
        menu()
        c = input("  Choose [1-4]: ").strip()
        if   c == "1": do_predict()
        elif c == "2": do_form()
        elif c == "3": do_upcoming()
        elif c == "4": print("\n  Goodbye!\n"); break
        else: print("  [!] Invalid.\n")


if __name__ == "__main__":
    main()
