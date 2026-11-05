#!/usr/bin/env python3
"""
Sunny days in Radomir by month and by year.

Input : docs/data/power_daily.json  (NASA POWER / MERRA-2, daily, 2005-2026)
Output: markdown tables for README.md ("Слънчеви дни в Радомир")

A day is classified by the clearness index Kt = H / H0, where H is the daily
global irradiation on the horizontal plane (NASA POWER) and H0 is the daily
extraterrestrial irradiation computed for the site latitude.

    ясен             Kt >= 0.65
    предимно слънчев 0.55 <= Kt < 0.65
    променлив        0.35 <= Kt < 0.55
    облачен          Kt < 0.35

"Слънчеви дни" = ясни + предимно слънчеви (Kt >= 0.55).
"""

import datetime
import json
import math
import os
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "docs", "data")

LAT = 42.545
GSC = 1367.0
SUNNY = 0.55
CLEAR = 0.65
CLOUDY = 0.35
NORM_FIRST, NORM_LAST = 2005, 2025     # climatic normal (full years)
LAST_FULL_YEAR = 2025
MON = ["Яну", "Фев", "Мар", "Апр", "Май", "Юни", "Юли", "Авг", "Сеп", "Окт", "Ное", "Дек"]
DAYS_IN_MONTH = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]


def toa_kwh(day, lat=LAT):
    """Daily extraterrestrial irradiation on a horizontal plane, kWh/m2."""
    y, m, d = int(day[:4]), int(day[4:6]), int(day[6:])
    doy = datetime.date(y, m, d).timetuple().tm_yday
    phi = math.radians(lat)
    dec = math.radians(23.45 * math.sin(math.radians(360.0 * (284 + doy) / 365.0)))
    e0 = 1.0 + 0.033 * math.cos(math.radians(360.0 * doy / 365.0))
    ws = math.acos(max(-1.0, min(1.0, -math.tan(phi) * math.tan(dec))))
    h0 = (24.0 / math.pi) * GSC * e0 * (
        math.cos(phi) * math.cos(dec) * math.sin(ws) + ws * math.sin(phi) * math.sin(dec))
    return h0 / 1000.0


def load():
    raw = json.load(open(os.path.join(DATA, "power_daily.json")))
    out = []
    for day, h in zip(raw["dates"], raw["allsky"]):
        kt = h / toa_kwh(day)
        out.append(dict(day=day, y=int(day[:4]), m=int(day[4:6]), h=h, kt=kt))
    return out


def kind(kt):
    if kt >= CLEAR:
        return "clear"
    if kt >= SUNNY:
        return "sunny"
    if kt >= CLOUDY:
        return "var"
    return "cloudy"


def complete_months(days):
    """Drop months with less than 90 % of the days present (e.g. 2026-11)."""
    cnt = defaultdict(int)
    for d in days:
        cnt[(d["y"], d["m"])] += 1
    ok = set()
    for (y, m), c in cnt.items():
        need = 29 if m == 2 else DAYS_IN_MONTH[m - 1]
        if c >= 0.9 * need:
            ok.add((y, m))
    return ok


def fmt(x, dec=1):
    s = f"{x:,.{dec}f}".replace(",", " ").replace(".", ",")
    return s


def main():
    days = load()
    ok = complete_months(days)
    norm = [d for d in days if NORM_FIRST <= d["y"] <= NORM_LAST and (d["y"], d["m"]) in ok]
    norm_months = {(d["y"], d["m"]) for d in norm}
    normal_years = len({y for y, _ in norm_months})

    # ---- table 1: monthly norm -------------------------------------------
    by_m = defaultdict(list)
    for d in norm:
        by_m[d["m"]].append(d)
    print("### 1. Климатична норма по месеци, Радомир (2005–2025)\n")
    print("| Месец | Слънчеви дни | Ясни (Kt ≥ 0,65) | Предимно слънчеви | "
          "Променливи | Облачни | Средна радиация, kWh/m²/ден |")
    print("|---|---|---|---|---|---|---|")
    tot = defaultdict(float)
    for m in range(1, 13):
        ds = by_m[m]
        k = [kind(d["kt"]) for d in ds]
        n = len(ds) / normal_years
        vals = [k.count("clear"), k.count("sunny"), k.count("var"), k.count("cloudy")]
        vals = [v / normal_years for v in vals]
        for name, v in zip(("sunny", "clear", "sunny2", "var", "cloudy"), [vals[0] + vals[1]] + vals):
            tot[name] += v
        print(f"| {MON[m-1]} | **{fmt(vals[0]+vals[1])}** | {fmt(vals[0])} | {fmt(vals[1])} | "
              f"{fmt(vals[2])} | {fmt(vals[3])} | {fmt(sum(d['h'] for d in ds)/len(ds))} |")
    print(f"| **Година** | **{fmt(tot['sunny'])}** | {fmt(tot['clear'])} | {fmt(tot['sunny2'])} | "
          f"{fmt(tot['var'])} | {fmt(tot['cloudy'])} | "
          f"{fmt(sum(d['h'] for d in norm)/len(norm))} |")

    # ---- table 2: share of day types --------------------------------------
    print("\n### 2. Разпределение на дните по тип, % от месеца\n")
    print("| Месец | Ясни | Предимно слънчеви | Променливи | Облачни |")
    print("|---|---|---|---|---|")
    for m in range(1, 13):
        ds = by_m[m]
        k = [kind(d["kt"]) for d in ds]
        n = len(ds)
        print(f"| {MON[m-1]} | {fmt(100*k.count('clear')/n)} % | {fmt(100*k.count('sunny')/n)} % | "
              f"{fmt(100*k.count('var')/n)} % | {fmt(100*k.count('cloudy')/n)} % |")

    # ---- table 3: year x month matrix ------------------------------------
    years = list(range(2015, 2027))
    cnt = defaultdict(int)
    for d in days:
        if (d["y"], d["m"]) in ok and d["kt"] >= SUNNY:
            cnt[(d["y"], d["m"])] += 1
    print("\n### 3. Брой слънчеви дни по години (Kt ≥ 0,55)\n")
    print("| Година | " + " | ".join(MON) + " | Година |")
    print("|---" * 14 + "|")
    for y in years:
        cells = []
        for m in range(1, 13):
            if (y, m) not in ok:
                cells.append("–")
            else:
                cells.append(str(cnt[(y, m)]))
        total = sum(int(c) for c in cells if c != "–")
        mark = "" if y <= LAST_FULL_YEAR else "*"
        print(f"| {y}{mark} | " + " | ".join(cells) + f" | **{total}** |")
    print(f"\n> \\* 2026 е непълна година (данни до 31.10.2026); за нея „Година“ е "
          f"сумата от януари до октомври. Нормата за {NORM_FIRST}–{NORM_LAST} е "
          f"**{fmt(tot['sunny'])}** слънчеви дни годишно.")

    # ---- table 4: annual series ------------------------------------------
    # reference for a partial year: the same months of the normal period
    def ref_sunny(months):
        ds = [d for d in norm if d["m"] in months]
        yrs = len({d["y"] for d in ds})
        return sum(1 for d in ds if d["kt"] >= SUNNY) / yrs

    print("\n### 4. Слънчеви дни по години – общо, спрямо нормата\n")
    print("| Година | Слънчеви дни | Спрямо нормата | Средна радиация, kWh/m²/ден | "
          "Най-слънчев месец | Най-облачен месец |")
    print("|---|---|---|---|---|---|")
    for y in range(NORM_FIRST, 2027):
        ds = [d for d in days if d["y"] == y and (y, d["m"]) in ok]
        if not ds:
            continue
        s = sum(1 for d in ds if d["kt"] >= SUNNY)
        months = defaultdict(list)
        for d in ds:
            months[d["m"]].append(d["kt"])
        best = max(months, key=lambda m: len([k for k in months[m] if k >= SUNNY]))
        worst = min(months, key=lambda m: len([k for k in months[m] if k >= SUNNY]))
        ref = ref_sunny(set(months)) if y > LAST_FULL_YEAR else tot["sunny"]
        dev = (s / ref - 1.0) * 100.0
        mark = "" if y <= LAST_FULL_YEAR else "*"
        n_best = len([k for k in months[best] if k >= SUNNY])
        n_worst = len([k for k in months[worst] if k >= SUNNY])
        dtxt = f"{dev:+.0f} %".replace("-", "−")
        print(f"| {y}{mark} | {s} | {dtxt} | {fmt(sum(d['h'] for d in ds)/len(ds), 2)} | "
              f"{MON[best-1]} ({n_best}) | {MON[worst-1]} ({n_worst}) |")

    print("\n> За 2026 „Спрямо нормата“ е спрямо същите месеци (януари–октомври) "
          "на 2005–2025, а средната радиация също е само за тези 10 месеца.")

    # ---- table 5: direct-sun hours from the PVGIS hourly series ----------
    s55 = json.load(open(os.path.join(DATA, "series55.json")))["outputs"]["hourly"]
    hours = defaultdict(float)
    seen = defaultdict(int)
    for r in s55:
        y, m = int(r["time"][:4]), int(r["time"][4:6])
        seen[(y, m)] += 1
        if r["Gb(i)"] >= 120.0:
            hours[(y, m)] += 1
    print("\n### 5. Часове с пряко слънце върху колекторната равнина (55°, юг)\n")
    print("| Месец | 2018 | 2019 | 2020 | Средно |")
    print("|---|---|---|---|---|")
    for m in range(1, 13):
        vals = [int(round(hours.get((y, m), 0))) for y in (2018, 2019, 2020)]
        print(f"| {MON[m-1]} | " + " | ".join(str(v) for v in vals) +
              f" | {fmt(sum(vals)/3, 0)} |")
    tot_h = [sum(int(round(hours.get((y, m), 0))) for m in range(1, 13)) for y in (2018, 2019, 2020)]
    print(f"| **Година** | " + " | ".join(f"**{v}**" for v in tot_h) +
          f" | **{fmt(sum(tot_h)/3, 0)}** |")
    print("\n> Часовете са от почасовата серия PVGIS (SARAH3) за равнина 55°/юг: "
          "час с Gb(i) ≥ 120 W/m². Това е практически „слънце грее върху панела“, "
          "по-строго от „денят е слънчев“.")


if __name__ == "__main__":
    main()
