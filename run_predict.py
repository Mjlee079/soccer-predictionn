import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from api_client import search_teams, get_last_n, get_h2h, get_finished_matches
from predictor import predict, _fin, _result, _gf, _ga

# Find teams
print("Searching for AmaZulu...")
az_results = search_teams("AmaZulu")
for t in az_results[:5]:
    print(f"  [{t['id']}] {t['name']} ({t['country']})")

print("\nSearching for Mamelodi Sundowns...")
ms_results = search_teams("Mamelodi")
for t in ms_results[:5]:
    print(f"  [{t['id']}] {t['name']} ({t['country']})")

if not az_results or not ms_results:
    print("Could not find one or both teams!")
    sys.exit(1)

home = az_results[0]
away = ms_results[0]
print(f"\nHome: {home['name']} (ID {home['id']})")
print(f"Away: {away['name']} (ID {away['id']})")

# Fetch data
print(f"\nFetching {home['name']} matches...")
hm = get_last_n(home["id"], 15)
print(f"  {len(hm)} matches loaded")

print(f"Fetching {away['name']} matches...")
am = get_last_n(away["id"], 15)
print(f"  {len(am)} matches loaded")

print("Fetching H2H...")
h2h = get_h2h(home["id"], away["id"])
print(f"  {len(h2h)} H2H matches")

# Run prediction
r = predict(home["name"], away["name"], hm, am, h2h)

# Display
print("\n" + "=" * 62)
print(f"  PREDICTION:  {r['home']}  vs  {r['away']}")
print("=" * 62)

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

# Factor breakdown
f = r["factors"]
print(f"\n  Factor Breakdown:")
print("-" * 62)
print(f"  {'Factor':<20} {'Home':>8}  {'Away':>8}  {'Weight':>6}")
print("-" * 62)
for lbl, key, wt in [
    ("Recent Form",  "form",    "25%"),
    ("Head-to-Head", "h2h",     "20%"),
    ("Attack (GF)",  "attack",  "15%"),
    ("Defence (GA)", "defence", "15%"),
    ("Venue Split",  "venue",   "15%"),
    ("GD Momentum",  "gd",      "10%"),
]:
    h, a = f[key]
    print(f"  {lbl:<20} {h:>8}  {a:>8}  {wt:>6}")
print("-" * 62)
ch, ca = f["composite"]
print(f"  {'COMPOSITE':<20} {ch:>8}  {ca:>8}")

# Recent form
for team_data, matches in [(home, hm), (away, am)]:
    fin = _fin(matches)[:5]
    if fin:
        print(f"\n  {team_data['name']} - Recent Form:")
        for m in fin:
            res = _result(m, team_data["name"])
            tag = {"W": "WIN ", "D": "DRAW", "L": "LOSS"}[res]
            print(f"    [{tag}]  {m['home']} {m['home_goals']}-{m['away_goals']} {m['away']}  ({m['date']})")

if h2h:
    print(f"\n  Head-to-Head This Season:")
    for m in h2h:
        print(f"    {m['home']} {m['home_goals']}-{m['away_goals']} {m['away']}  ({m['date']})")
