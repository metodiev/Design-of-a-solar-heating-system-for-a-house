#!/usr/bin/env python3
"""
Supplementary calculation for the vacuum-tube variant of the solar combisystem.

Reuses the hourly model in system_model.py (same weather, same building, same
buffer) and adds the economic and risk indicators that the flat-plate variant
does not need: stagnation window, dry-stagnation temperature, cost per used kWh.

Prints markdown tables -> docs/05-колектори.md, docs/10-икономически-анализ.md,
docs/11-експлоатация-и-безопасност.md.
"""

import importlib.util
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("system_model", os.path.join(HERE, "system_model.py"))
sm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sm)

PELLET_EUR_KG = 0.33
PELLET_KWH_KG = 4.8
BOILER_ETA = 0.90
DISCOUNT = 0.04
LIFE = 20

# solar part of the BOM that does not depend on the collector type
SOLAR_FIXED = 480.0 + 550.0 + 110.0 + 90.0 + 2 * 95.0      # station, HX, vessel, glycol, safety group
LABOUR_TOTAL = 2600.0 + 400.0 + 450.0
LABOUR_SOLAR_SHARE = 0.15

COLL = {
    "flat": dict(price=480.0, rail=120.0, rail_per=2, labour=1.00),
    "tube": dict(price=700.0, rail=150.0, rail_per=2, labour=1.10),
}


def solar_capex(n, kind):
    """Solar part of the investment, EUR without VAT (same structure as economics.py)."""
    c = COLL[kind]
    coll = n * c["price"] + math.ceil(n / c["rail_per"]) * c["rail"] + (n - 1) * 45.0 + 250.0
    return coll + SOLAR_FIXED + LABOUR_TOTAL * LABOUR_SOLAR_SHARE * c["labour"]


def annuity_factor(rate, years):
    return (1.0 - (1.0 + rate) ** -years) / rate


def savings_eur(used_kwh):
    return used_kwh / (PELLET_KWH_KG * BOILER_ETA) * PELLET_EUR_KG


def lcoe(capex, used_kwh):
    return (capex / LIFE + 0.01 * capex) / used_kwh


def num(x, dec=0):
    """Bulgarian number format: space thousands separator, decimal comma."""
    s = f"{x:,.{dec}f}".replace(",", " ")
    return s.replace(".", ",") if dec else s


def row(label, n, kind, r, fmt="{:.0f}", base=None):
    cap = solar_capex(n, kind) * 1.2
    save = savings_eur(r["used_a"])
    val = dict(
        area=r["area_gross"], ap=r["area_ap"], yield_=r["yield_a"],
        spec=r["specific_yield"], used=r["used_a"], share=100.0 * r["used_a"] / (r["heat_a"] + r["dhw_load_a"]),
        excess=r["excess_a"], stag=r["stagnation_hours"], tstag=r["t_stag_max"],
        capex=cap, save=save, payback=cap / save, npv=save * annuity_factor(DISCOUNT, LIFE) - cap,
        lcoe=lcoe(cap, r["used_a"]),
    )
    return label, val


def main():
    flat5 = sm.simulate(5, sm.FLAT, 800)
    tubes = {n: sm.simulate(n, sm.TUBE, 800) for n in (4, 5, 6, 7, 8)}

    print("### Допълнително изчисление – вариант с вакуумно-тръбни колектори\n")
    print("Същата сграда, същият буфер 800 l, същите метеоданни (PVGIS 2018–2020).\n")
    print("| Показател | Плоски 5 бр. | Тръбни 4 | Тръбни 5 | Тръбни 6 | Тръбни 7 | Тръбни 8 |")
    print("|---|---|---|---|---|---|---|")
    cols = [row("Плоски 5", 5, "flat", flat5)] + [row(f"Тръбни {n}", n, "tube", r) for n, r in tubes.items()]

    def line(name, key, dec=0, suffix=""):
        print(f"| {name} | " + " | ".join(num(c[1][key], dec) + suffix for c in cols) + " |")

    line("Брутна площ, m²", "area", 1)
    line("Апертурна площ, m²", "ap", 1)
    line("Годишно производство, kWh", "yield_")
    line("Специфично, kWh/m²(ап.)", "spec")
    line("Реално използвано, kWh", "used")
    line("Слънчев дял от товара", "share", 0, " %")
    line("Излишък, kWh", "excess")
    line("Часове в стагнационен прозорец, h/a", "stag")
    line("Макс. температура на абсорбера при стагнация, °C", "tstag")
    line("Соларна инвестиция с ДДС, €", "capex")
    line("Спестени разходи, €/a", "save")
    line("Изплащане на соларната част, г.", "payback")
    line("NPV 20 г. при 4 %, €", "npv")
    line("LCOE, €/kWh", "lcoe", 3)

    # ---- equal-energy point ------------------------------------------------
    print("\n### Колко тръбни колектора дават същата енергия като 5 плоски\n")
    tgt = flat5["used_a"]
    print("| Брой тръбни | Използвано, kWh | Разлика към 5 плоски | Инвестиция с ДДС, € | "
          "Изплащане, г. |")
    print("|---|---|---|---|---|")
    for n, r in tubes.items():
        cap = solar_capex(n, "tube") * 1.2
        diff = num(r['used_a'] - tgt) if r['used_a'] >= tgt else "-" + num(tgt - r['used_a'])
        print(f"| {n} | {num(r['used_a'])} | {'+' if r['used_a'] >= tgt else '−'}{num(abs(r['used_a']-tgt))} | "
              f"{num(cap)} | {cap/savings_eur(r['used_a']):.0f} |")
    cross = None
    for n in range(6, 12):
        if n not in tubes:
            tubes[n] = sm.simulate(n, sm.TUBE, 800)
        if tubes[n]["used_a"] >= tgt:
            cross = n
            break
    print(f"\n> Еквивалентът на 5 плоски колектора ({num(tgt)} kWh/год.) се достига при "
          f"**{cross} тръбни** ({num(tubes[cross]['area_gross'], 1)} m² бруто), "
          f"инвестиция {num(solar_capex(cross, 'tube')*1.2)} € с ДДС – "
          f"с +{num((solar_capex(cross, 'tube')/solar_capex(5, 'flat')-1)*100)} % спрямо плоските.")

    # ---- marginal cost -----------------------------------------------------
    print("\n### Маргинална цена на всеки следващ тръбен колектор\n")
    print("| Стъпка | Доп. инвестиция с ДДС, € | Доп. използвана енергия, kWh/a | "
          "Доп. спестяване, €/a | Изплащане, г. |")
    print("|---|---|---|---|---|")
    for n in range(5, 9):
        d_used = tubes[n]["used_a"] - tubes[n-1]["used_a"]
        d_cap = (solar_capex(n, "tube") - solar_capex(n-1, "tube")) * 1.2
        d_sav = savings_eur(tubes[n]["used_a"]) - savings_eur(tubes[n-1]["used_a"])
        print(f"| {n-1} → {n} | {num(d_cap)} | {num(d_used)} | {num(d_sav)} | "
              f"{d_cap/d_sav if d_sav > 0 else float('inf'):.0f} |")

    # ---- comparison per m2 ------------------------------------------------
    print("\n### Цена на спестената топлина (соларна част, 20 г., 4 %)\n")
    print("| Вариант | Спестена енергия, kWh/a | Инвестиция с ДДС, € | €/kWh(спестен) | "
          "Спрямо 5 плоски |")
    print("|---|---|---|---|---|")
    base = lcoe(solar_capex(5, "flat") * 1.2, flat5["used_a"])
    for label, n, kind, r in [("Плоски 5", 5, "flat", flat5)] + \
                              [(f"Тръбни {n}", n, "tube", r) for n, r in tubes.items() if n <= 8]:
        lc = lcoe(solar_capex(n, kind) * 1.2, r["used_a"])
        print(f"| {label} | {num(r['used_a'])} | {num(solar_capex(n, kind)*1.2)} | "
              f"{num(lc, 3)} | {num(lc/base, 2)}× |")

    # ---- sensitivity on the tube price ------------------------------------
    print("\n### Чувствителност – цена на един тръбен колектор\n")
    print("| Цена, €/бр. | 5 тръбни: инвестиция, € | 5 тръбни: изплащане, г. | "
          "8 тръбни: инвестиция, € | 8 тръбни: изплащане, г. |")
    print("|---|---|---|---|---|")
    for price in (350.0, 450.0, 550.0, 700.0):
        COLL["tube"]["price"] = price
        c5 = solar_capex(5, "tube") * 1.2
        c8 = solar_capex(8, "tube") * 1.2
        print(f"| {num(price)} | {num(c5)} | {c5/savings_eur(tubes[5]['used_a']):.0f} | "
              f"{num(c8)} | {c8/savings_eur(tubes[8]['used_a']):.0f} |")
    COLL["tube"]["price"] = 700.0
    print(f"\n> За сравнение: 5 плоски – {num(solar_capex(5, 'flat')*1.2)} € с ДДС, "
          f"изплащане {solar_capex(5, 'flat')*1.2/savings_eur(flat5['used_a']):.0f} г.")

    # ---- stagnation risk --------------------------------------------------
    print("\n### Стагнация – количествена оценка\n")
    print("| Показател | Плоски 5 | Тръбни 5 | Тръбни 8 |")
    print("|---|---|---|---|")
    for label, key in (("Часове с буфер над 90 °C, h/a", "hot_hours"),
                       ("Дни с буфер над 90 °C, d/a", "hot_days"),
                       ("Часове без топлинен приемник, h/a", "stagnation_hours"),
                       ("Суха стагнация, изчислена, °C", "t_stag_max"),
                       ("Излишък за разсейване, kWh/a", "excess_a"),
                       ("Часове работа на помпата, h/a", "run_hours")):
        print(f"| {label} | {num(flat5[key])} | {num(tubes[5][key])} | {num(tubes[8][key])} |")


if __name__ == "__main__":
    main()
