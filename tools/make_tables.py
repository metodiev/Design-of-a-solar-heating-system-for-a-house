#!/usr/bin/env python3
"""Print markdown tables from docs/data/model_results.json (used in the report)."""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "docs", "data")
R = json.load(open(os.path.join(DATA, "model_results.json")))
MR = json.load(open(os.path.join(DATA, "pvgis_mr.json")))["outputs"]["monthly"]
V90 = json.load(open(os.path.join(DATA, "pv_90.json")))["outputs"]["monthly"]["fixed"]
S55 = json.load(open(os.path.join(DATA, "series55.json")))["outputs"]["hourly"]

MON = ["Яну", "Фев", "Мар", "Апр", "Май", "Юни", "Юли", "Авг", "Сеп", "Окт", "Ное", "Дек"]

ghi = {}
for r in MR:
    ghi.setdefault(r["month"], []).append(r["H(h)_m"])
ghi = [sum(ghi[m]) / len(ghi[m]) for m in range(1, 13)]

t55 = [0.0] * 12
for r in S55:
    t55[int(r["time"][4:6]) - 1] += (r["Gb(i)"] + r["Gd(i)"] + r["Gr(i)"]) / 3000.0  # 3 years
h90 = [x["H(i)_m"] for x in V90]


def pick(n, v, typ="flat"):
    for r in R:
        if r["n"] == n and r["v_buf"] == v and r["type"] == typ:
            return r
    raise KeyError((n, v, typ))


def main():
    print("### Месечна слънчева радиация\n")
    print("| Месец | GHI, kWh/m² | Наклон 55°, kWh/m² | Вертикал юг, kWh/m² |")
    print("|---|---|---|---|")
    for i in range(12):
        print(f"| {MON[i]} | {ghi[i]:.0f} | {t55[i]:.0f} | {h90[i]:.0f} |")
    print(f"| **Година** | **{sum(ghi):.0f}** | **{sum(t55):.0f}** | **{sum(h90):.0f}** |")

    r = pick(5, 800)
    print("\n### Енергиен баланс – 5 плоски колектора, буфер 800 l\n")
    print("| Месец | Отопление, kWh | БГВ, kWh | Слънце, kWh | Използвано, kWh | Излишък, kWh | Резерв, kWh | Сол. дял |")
    print("|---|---|---|---|---|---|---|---|")
    dhw_m = [3819.7 / 365 * d for d in (31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)]
    for i in range(12):
        load = r["demand_m"][i] + dhw_m[i]
        sf = r["used_m"][i] / load * 100 if load > 0 else 0
        print(f"| {MON[i]} | {r['demand_m'][i]:.0f} | {dhw_m[i]:.0f} | {r['yield_m'][i]:.0f} | "
              f"{r['used_m'][i]:.0f} | {r['excess_m'][i]:.0f} | {r['backup_m'][i]:.0f} | {sf:.0f}% |")
    load = sum(r["demand_m"]) + sum(dhw_m)
    print(f"| **Година** | **{sum(r['demand_m']):.0f}** | **{sum(dhw_m):.0f}** | **{r['yield_a']:.0f}** | "
          f"**{r['used_a']:.0f}** | **{r['excess_a']:.0f}** | **{r['backup_a']:.0f}** | "
          f"**{r['used_a']/load*100:.0f}%** |")

    print("\n### Варианти – плоски колектори (буфер 800 l)\n")
    print("| Показател | 4 бр. | 5 бр. | 6 бр. |")
    print("|---|---|---|---|")
    v = [pick(n, 800) for n in (4, 5, 6)]
    rows = [
        ("Брутна площ, m²", lambda x: f"{x['area_gross']:.1f}"),
        ("Апертурна площ, m²", lambda x: f"{x['area_ap']:.1f}"),
        ("Годишно производство, kWh", lambda x: f"{x['yield_a']:.0f}"),
        ("Специфично, kWh/m²(ап.)", lambda x: f"{x['specific_yield']:.0f}"),
        ("Реално използвано, kWh", lambda x: f"{x['used_a']:.0f}"),
        ("  – за БГВ, kWh", lambda x: f"{x['used_dhw']:.0f}"),
        ("  – за отопление, kWh", lambda x: f"{x['used_h']:.0f}"),
        ("Излишък (неизползваем), kWh", lambda x: f"{x['excess_a']:.0f}"),
        ("Остатък от пелети/камина, kWh", lambda x: f"{x['backup_a']:.0f}"),
        ("Слънчев дял от товара", lambda x: f"{x['used_a']/(x['heat_a']+x['dhw_load_a'])*100:.0f}%"),
        ("Часове работа на соларната помпа", lambda x: f"{x['run_hours']:.0f}"),
    ]
    for name, f in rows:
        print(f"| {name} | " + " | ".join(f(x) for x in v) + " |")

    print("\n### Варианти – вакуумно-тръбни колектори (буфер 800 l)\n")
    print("| Показател | 4 бр. | 5 бр. | 6 бр. |")
    print("|---|---|---|---|")
    v = [pick(n, 800, "tube") for n in (4, 5, 6)]
    for name, f in rows:
        print(f"| {name} | " + " | ".join(f(x) for x in v) + " |")

    print("\n### Влияние на обема на буфера (5 плоски колектора)\n")
    print("| Буфер | Производство, kWh | Използвано, kWh | Излишък, kWh | Резерв, kWh |")
    print("|---|---|---|---|---|")
    for vv in (500, 800, 1000):
        x = pick(5, vv)
        print(f"| {vv} l | {x['yield_a']:.0f} | {x['used_a']:.0f} | {x['excess_a']:.0f} | {x['backup_a']:.0f} |")

    print("\n### Средни температури в буфера (5 плоски, 800 l)\n")
    print("| | " + " | ".join(MON) + " |")
    print("|---|" + "---|" * 12)
    x = pick(5, 800)
    print("| Горна част, °C | " + " | ".join(f"{t:.0f}" for t in x["t_top"]) + " |")
    print("| Долна част, °C | " + " | ".join(f"{t:.0f}" for t in x["t_bot"]) + " |")


if __name__ == "__main__":
    main()
