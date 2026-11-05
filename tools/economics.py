#!/usr/bin/env python3
"""BOM, budget levels and economic analysis. Prints markdown tables."""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "docs", "data")
R = json.load(open(os.path.join(DATA, "model_results.json")))

BOM = [
    ("Плосък колектор KPS11, 2,52 m², Solar Keymark", "бр.", 5, 480.0, "coll"),
    ("Монтажна шина с анкери (за 2 колектора)", "к-т", 3, 120.0, "coll"),
    ("Свързващ комплект между колекторите", "к-т", 4, 45.0, "coll"),
    ("Соларна помпена станция S2 SRS3 с регулатор", "бр.", 1, 480.0, "solar"),
    ("Пластинчат топлообменник + помпен комплект", "к-т", 1, 550.0, "solar"),
    ("Буферен съд PS 800 N+ с изолация", "бр.", 1, 1250.0, "buf"),
    ("Бойлер R2BC 200 с две серпентини", "бр.", 1, 760.0, "dhw"),
    ("Контролер IR 12 THERM2 SOL + 8 датчика", "к-т", 1, 620.0, "ctrl"),
    ("Помпена група M3 MIX с трипътен смесител", "к-т", 1, 470.0, "heat"),
    ("Термостатичен смесител 55 °C за камината", "бр.", 1, 380.0, "fire"),
    ("Циркулационна помпа за каминения кръг", "бр.", 1, 210.0, "fire"),
    ("Разширителен съд 25 l, 6 bar (солар)", "бр.", 1, 110.0, "solar"),
    ("Разширителен съд 100 l (отопление + буфер)", "бр.", 1, 210.0, "heat"),
    ("Разширителен съд 8 l (БГВ)", "бр.", 1, 45.0, "dhw"),
    ("Предпазна група 6 bar / 3 bar", "бр.", 2, 95.0, "solar"),
    ("Възвратни клапани, кранове, филтри", "к-т", 1, 380.0, "misc"),
    ("Автоматичен обезвъздушител", "бр.", 4, 35.0, "misc"),
    ("Зонов вентил с електрозадвижка", "бр.", 3, 95.0, "heat"),
    ("Стаен термостат", "бр.", 3, 45.0, "heat"),
    ("Медни тръби 22/18/15 mm + фитинги", "к-т", 1, 880.0, "pipe"),
    ("Изолация на тръбите", "к-т", 1, 260.0, "pipe"),
    ("Кабели, табло, крепежи, дребни материали", "к-т", 1, 420.0, "ctrl"),
    ("Антифриз 25 l (40 % пропиленгликол)", "бр.", 1, 90.0, "solar"),
    ("Монтажни конструкции и анкери", "к-т", 1, 250.0, "coll"),
    ("Труд – монтаж", "усл.", 1, 2600.0, "labour"),
    ("Пускане в експлоатация, протоколи", "усл.", 1, 400.0, "labour"),
    ("Проект, съгласуване, надзор", "усл.", 1, 450.0, "labour"),
]

PELLET_EUR_KG = 0.33
PELLET_KWH_KG = 4.8
BOILER_ETA = 0.90
EL_EUR_KWH = 0.22
DISCOUNT = 0.04
LIFE = 20


def bom_total(factor=1.0, labour_factor=1.0):
    return sum(q * p * (labour_factor if k == "labour" else factor)
               for _, _, q, p, k in BOM)


def variant_capex(n_coll, factor=1.0, labour_factor=1.0):
    """Capex with a different number of collectors (5 in BOM)."""
    base = bom_total(factor, labour_factor)
    per = sum(q * p for _, _, q, p, k in BOM if k == "coll") / 5.0
    return base + (n_coll - 5) * per * factor


def main():
    print("### Количествена сметка (среден клас)\n")
    print("| № | Позиция | Мярка | Кол. | Ед. цена, € | Сума, € |")
    print("|---|---|---|---|---|---|")
    tot = 0
    for i, (name, unit, q, p, _) in enumerate(BOM, 1):
        tot += q * p
        print(f"| {i} | {name} | {unit} | {q} | {p:,.0f} | {q*p:,.0f} |")
    print(f"| | **Общо без ДДС** | | | | **{tot:,.0f}** |")
    print(f"| | **С ДДС 20 %** | | | | **{tot*1.2:,.0f}** |")

    solar_net = sum(q * p for _, _, q, p, k in BOM if k in ("coll", "solar"))
    solar_net += 0.15 * sum(q * p for _, _, q, p, k in BOM if k == "labour")
    print(f"\n> Соларна част (колектори, станция, ТО, разширителен съд, гликол, конструкция, "
          f"съответния дял труд): **{solar_net:,.0f} € без ДДС / {solar_net*1.2:,.0f} € с ДДС**.")

    print("\n### Бюджетни нива\n")
    print("| Ниво | Оборудване и материали | Труд | Общо без ДДС | С ДДС |")
    print("|---|---|---|---|---|")
    for name, f, lf in (("Икономичен", 0.80, 0.90), ("Среден клас", 1.0, 1.0), ("Висок клас", 1.35, 1.15)):
        eq = sum(q * p * f for _, _, q, p, k in BOM if k != "labour")
        lb = sum(q * p * lf for _, _, q, p, k in BOM if k == "labour")
        print(f"| {name} | {eq:,.0f} | {lb:,.0f} | {eq+lb:,.0f} | {(eq+lb)*1.2:,.0f} |")

    print("\n### Варианти 4 / 5 / 6 колектора (буфер 800 l, плоски)\n")
    print("| Показател | 4 бр. | 5 бр. | 6 бр. |")
    print("|---|---|---|---|")
    vs = [next(x for x in R if x["n"] == n and x["v_buf"] == 800 and x["type"] == "flat") for n in (4, 5, 6)]
    print("| Инвестиция – соларна част с ДДС, € | " +
          " | ".join(f"{(solar_net + (v['n']-5)*360)*1.2:,.0f}" for v in vs) + " |")
    print("| Годишно производство, kWh | " + " | ".join(f"{v['yield_a']:,.0f}" for v in vs) + " |")
    print("| Реално използвано, kWh | " + " | ".join(f"{v['used_a']:,.0f}" for v in vs) + " |")
    print("| Спестени пелети, kg/a | " + " | ".join(f"{v['used_a']/(PELLET_KWH_KG*BOILER_ETA):,.0f}" for v in vs) + " |")
    print("| Спестени €/a (0,33 €/kg) | " +
          " | ".join(f"{v['used_a']/(PELLET_KWH_KG*BOILER_ETA)*PELLET_EUR_KG:,.0f}" for v in vs) + " |")
    print("| Изплащане на соларната част, г. | " +
          " | ".join(f"{((solar_net + (v['n']-5)*360)*1.2)/(v['used_a']/(PELLET_KWH_KG*BOILER_ETA)*PELLET_EUR_KG):.0f}"
                     for v in vs) + " |")

    print("\n### Икономика на цялата система (5 плоски, 800 l)\n")
    r = vs[1]
    kg = r["used_a"] / (PELLET_KWH_KG * BOILER_ETA)
    capex = tot * 1.2
    print("| Показател | Стойност |")
    print("|---|---|")
    print(f"| Обща инвестиция с ДДС | {capex:,.0f} € |")
    print(f"| Соларна част с ДДС | {solar_net*1.2:,.0f} € |")
    print(f"| Спестени пелети | {kg:,.0f} kg/a |")
    print(f"| Спестени разходи (пелети 0,33 €/kg) | {kg*PELLET_EUR_KG:,.0f} €/a |")
    print(f"| Изплащане на соларната част | {solar_net*1.2/(kg*PELLET_EUR_KG):.0f} г. |")
    print(f"| Изплащане на цялата система | {capex/(kg*PELLET_EUR_KG):.0f} г. |")
    npv = sum(kg * PELLET_EUR_KG / (1 + DISCOUNT) ** t for t in range(1, LIFE + 1)) - solar_net * 1.2
    print(f"| NPV 20 г. при 4 % (соларна част) | {npv:,.0f} € |")
    lcoe = (solar_net * 1.2 / LIFE + 0.01 * solar_net * 1.2) / r["used_a"]
    print(f"| LCOE на слънчевата топлина | {lcoe:.3f} €/kWh |")

    print("\n### Сценарий „електрическа БГВ преди инвестицията“\n")
    print("| Вариант | Спестени €/a | Изплащане на соларната част, г. |")
    print("|---|---|---|")
    for v in vs:
        save = (v["used_dhw"] * EL_EUR_KWH
                + v["used_h"] / (PELLET_KWH_KG * BOILER_ETA) * PELLET_EUR_KG)
        sc = (solar_net + (v["n"] - 5) * 360) * 1.2
        print(f"| Плоски, {v['n']} бр. | {save:,.0f} | {sc/save:.0f} |")

    print("\n### Чувствителност – цена на пелетите (5 плоски, 800 l)\n")
    print("| Цена, €/kg | €/kWh(топл.) | Спестени €/a | Изплащане на соларната част, г. |")
    print("|---|---|---|---|")
    for p_ in (0.22, 0.28, 0.33, 0.40, 0.50, 0.65):
        save = kg * p_
        print(f"| {p_:.2f} | {p_/(PELLET_KWH_KG*BOILER_ETA):.3f} | {save:,.0f} | {solar_net*1.2/save:.0f} |")

    print("\n### Маргинална ефективност на всеки следващ колектор\n")
    print("| Стъпка | Доп. инвестиция с ДДС, € | Доп. използвана енергия, kWh/a | Доп. спестяване, €/a | Изплащане, г. |")
    print("|---|---|---|---|---|")
    prev = None
    for v in vs:
        if prev:
            du = v["used_a"] - prev[0]
            dc = 360 * 1.2
            ds = du / (PELLET_KWH_KG * BOILER_ETA) * PELLET_EUR_KG
            print(f"| {prev[1]} → {v['n']} | {dc:,.0f} | {du:,.0f} | {ds:,.0f} | {dc/ds:.0f} |")
        prev = (v["used_a"], v["n"])


if __name__ == "__main__":
    main()
