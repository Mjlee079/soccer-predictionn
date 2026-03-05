"""
Soccer Match Prediction Engine
==============================
Weighted multi-factor model using real match data.

Factors:
  1. Recent Form (last 10)      25%
  2. Head-to-Head Record        20%
  3. Goals Scored (attack)      15%
  4. Goals Conceded (defence)   15%
  5. Home / Away performance    15%
  6. Goal-Difference momentum   10%
"""

WEIGHTS = {
    "form":    0.25,
    "h2h":     0.20,
    "attack":  0.15,
    "defence": 0.15,
    "venue":   0.15,
    "gd":      0.10,
}


# ── helpers ──────────────────────────────────────────────────
def _fin(matches):
    return [m for m in matches if m["home_goals"] is not None and m["away_goals"] is not None]


def _result(m, team):
    hg, ag = m["home_goals"], m["away_goals"]
    is_home = m["home"] == team
    if hg == ag:
        return "D"
    if is_home:
        return "W" if hg > ag else "L"
    return "W" if ag > hg else "L"


def _gf(m, team):
    return m["home_goals"] if m["home"] == team else m["away_goals"]


def _ga(m, team):
    return m["away_goals"] if m["home"] == team else m["home_goals"]


# ── factor calculations ─────────────────────────────────────
def calc_form(matches, team):
    f = _fin(matches)
    if not f:
        return 0.5
    pts = {"W": 3, "D": 1, "L": 0}
    return sum(pts[_result(m, team)] for m in f) / (3 * len(f))


def calc_h2h(h2h_matches, team_a, team_b):
    f = _fin(h2h_matches)
    if not f:
        return 0.5, 0.5
    pts = {"W": 3, "D": 1, "L": 0}
    a = sum(pts[_result(m, team_a)] for m in f)
    b = sum(pts[_result(m, team_b)] for m in f)
    t = a + b
    return (a / t, b / t) if t else (0.5, 0.5)


def calc_attack(matches, team):
    f = _fin(matches)
    if not f:
        return 0.5
    avg = sum(_gf(m, team) for m in f) / len(f)
    return max(0, min(1, avg / 3))  # 0-3+ goals → 0-1


def calc_defence(matches, team):
    f = _fin(matches)
    if not f:
        return 0.5
    avg = sum(_ga(m, team) for m in f) / len(f)
    return max(0, min(1, 1 - avg / 3))  # fewer conceded = better


def calc_venue(matches, team, is_home):
    f = [m for m in _fin(matches) if (m["home"] == team) == is_home]
    if not f:
        return 0.5
    pts = {"W": 3, "D": 1, "L": 0}
    return sum(pts[_result(m, team)] for m in f) / (3 * len(f))


def calc_gd(matches, team):
    f = _fin(matches)
    if not f:
        return 0.5
    avg = sum(_gf(m, team) - _ga(m, team) for m in f) / len(f)
    return max(0, min(1, (avg + 3) / 6))


# ── main prediction ─────────────────────────────────────────
def predict(home_name, away_name, home_matches, away_matches, h2h_matches):
    """Predict match outcome using weighted factors."""
    hf = calc_form(home_matches, home_name)
    af = calc_form(away_matches, away_name)

    h2h_h, h2h_a = calc_h2h(h2h_matches, home_name, away_name)

    h_att = calc_attack(home_matches, home_name)
    a_att = calc_attack(away_matches, away_name)

    h_def = calc_defence(home_matches, home_name)
    a_def = calc_defence(away_matches, away_name)

    h_ven = calc_venue(home_matches, home_name, True)
    a_ven = calc_venue(away_matches, away_name, False)

    h_gd = calc_gd(home_matches, home_name)
    a_gd = calc_gd(away_matches, away_name)

    # weighted composite
    h_score = (
        WEIGHTS["form"]    * hf
        + WEIGHTS["h2h"]   * h2h_h
        + WEIGHTS["attack"] * h_att
        + WEIGHTS["defence"]* h_def
        + WEIGHTS["venue"]  * h_ven
        + WEIGHTS["gd"]    * h_gd
    )
    a_score = (
        WEIGHTS["form"]    * af
        + WEIGHTS["h2h"]   * h2h_a
        + WEIGHTS["attack"] * a_att
        + WEIGHTS["defence"]* a_def
        + WEIGHTS["venue"]  * a_ven
        + WEIGHTS["gd"]    * a_gd
    )

    total = h_score + a_score
    h_raw = h_score / total if total else 0.5
    a_raw = a_score / total if total else 0.5

    # W / D / L probabilities
    diff = abs(h_raw - a_raw)
    draw = max(0.05, 0.35 - diff * 0.8)
    rem = 1 - draw
    h_win = rem * h_raw
    a_win = rem * a_raw
    s = h_win + draw + a_win
    h_win /= s
    draw /= s
    a_win /= s

    # predicted score
    fin_h = _fin(home_matches)
    fin_a = _fin(away_matches)
    avg_hgf = sum(_gf(m, home_name) for m in fin_h) / len(fin_h) if fin_h else 1.2
    avg_agf = sum(_gf(m, away_name) for m in fin_a) / len(fin_a) if fin_a else 1.0
    avg_hga = sum(_ga(m, home_name) for m in fin_h) / len(fin_h) if fin_h else 1.0
    avg_aga = sum(_ga(m, away_name) for m in fin_a) / len(fin_a) if fin_a else 1.2

    p_hg = round((avg_hgf * 0.6 + avg_aga * 0.4) * h_raw * 2)
    p_ag = round((avg_agf * 0.6 + avg_hga * 0.4) * a_raw * 2)

    # confidence
    data_n = len(fin_h) + len(fin_a) + len(_fin(h2h_matches))
    conf = int((min(1, data_n / 30) * 0.6 + diff * 0.4) * 100)

    probs = {"home": h_win, "draw": draw, "away": a_win}
    best = max(probs, key=probs.get)
    verdict = {"home": f"{home_name} WIN", "draw": "DRAW", "away": f"{away_name} WIN"}[best]

    return {
        "home": home_name, "away": away_name,
        "home_win": round(h_win * 100, 1),
        "draw": round(draw * 100, 1),
        "away_win": round(a_win * 100, 1),
        "pred_hg": p_hg, "pred_ag": p_ag,
        "verdict": verdict, "confidence": conf,
        "factors": {
            "form":    (f"{hf:.2f}", f"{af:.2f}"),
            "h2h":     (f"{h2h_h:.2f}", f"{h2h_a:.2f}"),
            "attack":  (f"{h_att:.2f}", f"{a_att:.2f}"),
            "defence": (f"{h_def:.2f}", f"{a_def:.2f}"),
            "venue":   (f"{h_ven:.2f}", f"{a_ven:.2f}"),
            "gd":      (f"{h_gd:.2f}", f"{a_gd:.2f}"),
            "composite":(f"{h_score:.3f}", f"{a_score:.3f}"),
        },
        "data_used": {"home": len(fin_h), "away": len(fin_a), "h2h": len(_fin(h2h_matches))},
    }
