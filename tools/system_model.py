#!/usr/bin/env python3
"""
Hourly energy model of the solar combisystem in Radomir (BG).

Weather : PVGIS-SARAH3 / ERA5, 2019 hourly, plane 55 deg, azimuth 0 (south)
Solar   : Hottel-Whillier-Bliss, quasi-steady, hourly
Buffer  : single well-mixed node + fixed stratification offset (8 K bottom / 8 K top)
DHW     : 1 node, solar priority, coil effectiveness 0.85
Heating : hourly profile proportional to (20 - Tout), scaled to the ISO 13790 monthly demand
Backup  : pellet stove / fireplace charges the buffer to the set-point when needed

Output: docs/data/model_results.json
"""

import json
import os
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "docs", "data")
YEARS = ("2018", "2019", "2020")
NYEARS = len(YEARS)

# ------------------------------------------------------------------ building --
A_USE = 80.0                       # m2 heated, total for the three floors
U_WALL, A_WALL = 0.45, 151.0
U_ROOF, A_ROOF = 0.30, 26.7
U_FLR, A_FLR = 0.40, 26.7
U_WIN, A_WIN = 1.30, 13.0
TB = 0.08
FG = 0.5
ACH = 0.5
VOLUME = 200.0

H_TR = (U_WALL * A_WALL + U_ROOF * A_ROOF + U_FLR * A_FLR * FG + U_WIN * A_WIN) * (1 + TB)
H_VE = 0.34 * ACH * VOLUME
H_TOT = H_TR + H_VE
T_SET = 20.0
T_DESIGN = -15.0
P_DESIGN = H_TOT * (T_SET - T_DESIGN) / 1000.0

Q_INT_W = 4.5 * A_USE
G_WIN, F_FRAME = 0.60, 0.75
A_WIN_S, A_WIN_O = 7.0, 6.0
HOURS = [744, 672, 744, 720, 744, 720, 744, 744, 720, 744, 720, 744]

FLAT = dict(a_gross=2.52, a_ap=2.30, eta0=0.80, a1=3.5, a2=0.015, flow=40.0, iam=0.95)
TUBE = dict(a_gross=1.66, a_ap=1.30, eta0=0.70, a1=1.6, a2=0.008, flow=50.0, iam=1.00)

DHW_DAY = 180.0                    # l/day at 60 C
DHW_SET = 52.0
BUF_SET = 58.0                     # backup charging set-point (buffer mean)
BUF_MAX = 93.0
T_STRAT = 8.0                      # half of the top-bottom stratification


# ------------------------------------------------------------------- weather --
def load_weather():
    hourly = json.load(open(os.path.join(DATA, "series55.json")))["outputs"]["hourly"]
    hourly = [r for r in hourly if r["time"][:4] in YEARS]
    mr = json.load(open(os.path.join(DATA, "pvgis_mr.json")))["outputs"]["monthly"]
    v90 = json.load(open(os.path.join(DATA, "pv_90.json")))["outputs"]["monthly"]["fixed"]

    ghi = defaultdict(list)
    for r in mr:
        ghi[r["month"]].append(r["H(h)_m"])
    ghi_m = [sum(ghi[m]) / len(ghi[m]) for m in range(1, 13)]

    tsum = defaultdict(list)
    for r in hourly:
        tsum[int(r["time"][4:6])].append(r["T2m"])
    t_m = [sum(tsum[m]) / len(tsum[m]) for m in range(1, 13)]

    days = defaultdict(list)
    for r in hourly:
        days[r["time"][:8]].append(r["T2m"])
    hdd = [0.0] * 12
    cnt = [0] * 12
    for d in sorted(days):
        m = int(d[4:6]) - 1
        hdd[m] += max(0.0, T_SET - sum(days[d]) / len(days[d]))
        cnt[m] += 1
    hdd_m = [hdd[m] / cnt[m] * 30.44 for m in range(12)]

    return hourly, ghi_m, t_m, hdd_m, [x["H(i)_m"] for x in v90]


def iso_demand(hdd, hours, hs, ho):
    q_loss = H_TOT * hdd * 24.0 / 1000.0
    q_int = Q_INT_W * hours / 1000.0
    q_sol = A_WIN_S * G_WIN * F_FRAME * hs + A_WIN_O * G_WIN * F_FRAME * ho
    gamma = (q_int + q_sol) / q_loss if q_loss > 0 else 0.0
    a = 4.0
    if q_loss <= 0:
        return 0.0
    if abs(gamma - 1.0) < 1e-6:
        eta = a / (a + 1.0)
    else:
        eta = (1 - gamma ** a) / (1 - gamma ** (a + 1))
    eta = max(0.0, min(1.0, eta))
    return max(0.0, q_loss - eta * (q_int + q_sol))


def monthly_demand():
    _, ghi_m, _, hdd_m, h90 = load_weather()
    return [iso_demand(hdd_m[i], HOURS[i], h90[i], ghi_m[i]) for i in range(12)]


# ---------------------------------------------------------------- simulation --
def stagnation_dt(g, coll):
    """Absorber overtemperature at zero efficiency (dry stagnation), K."""
    a1, a2, eta0 = coll["a1"], coll["a2"], coll["eta0"]
    if a2 <= 0:
        return eta0 * g / a1
    return (-a1 + (a1 * a1 + 4.0 * a2 * eta0 * g) ** 0.5) / (2.0 * a2)


def simulate(n_coll, coll, v_buf, dhw_vol=200.0):
    hourly, _, _, _, _ = load_weather()
    q_heat_m = monthly_demand()

    a_ap = n_coll * coll["a_ap"]
    m_dot = coll["flow"] * a_ap / 3600.0                  # kg/s
    q_pump_max = m_dot * 4186.0 * 20.0                    # W

    c_buf = v_buf * 4186.0                                # J/K
    ua_buf = 2.0 if v_buf >= 800 else 1.7
    t_buf = 45.0

    c_dhw = dhw_vol * 4186.0
    t_dhw = 50.0
    ua_dhw = 1.2

    prof = [0.01, 0.01, 0.01, 0.01, 0.02, 0.05, 0.09, 0.09, 0.05, 0.03, 0.02, 0.02,
            0.03, 0.02, 0.01, 0.01, 0.02, 0.05, 0.08, 0.09, 0.07, 0.05, 0.03, 0.02]
    e_dhw_day = DHW_DAY * 4186.0 * (60.0 - 10.0) / 3.6e6  # kWh/day

    raw_m = [0.0] * 12
    for r in hourly:
        raw_m[int(r["time"][4:6]) - 1] += H_TOT * max(0.0, T_SET - r["T2m"]) / 1000.0
    target = [q * NYEARS for q in q_heat_m]
    scale = [target[i] / raw_m[i] if raw_m[i] > 0 else 0.0 for i in range(12)]

    yield_m = [0.0] * 12
    used_m = [0.0] * 12
    used_h_m = [0.0] * 12
    used_dhw_m = [0.0] * 12
    excess_m = [0.0] * 12
    backup_m = [0.0] * 12
    demand_m = [0.0] * 12
    unmet_m = [0.0] * 12
    t_top_m = [0.0] * 12
    t_bot_m = [0.0] * 12
    hcnt = [0] * 12
    run_hours = 0
    stag_hours = 0                      # buffer at max + strong sun -> stagnation window
    hot_hours = 0                       # buffer top above 90 C
    hot_days = 0
    hot_day = ""
    t_max = 0.0

    for r in hourly:
        mon = int(r["time"][4:6]) - 1
        g = (r["Gb(i)"] + r["Gd(i)"] + r["Gr(i)"]) * coll["iam"]
        ta = r["T2m"]

        # ---------------- solar loop ----------------------------------------
        t_bot = max(12.0, t_buf - T_STRAT)
        if g > 30.0 and t_bot < BUF_MAX - 1:
            t_in = t_bot + 2.0
            t_out = t_in + 5.0
            q = 0.0
            for _ in range(8):
                tm = t_in + (t_out - t_in) / 2.0
                dt = max(0.0, tm - ta)
                eta = coll["eta0"] - coll["a1"] * dt / g - coll["a2"] * dt * dt / g
                eta = max(0.0, min(coll["eta0"], eta))
                q = min(a_ap * eta * g, q_pump_max)
                t_out = t_in + q / (m_dot * 4186.0)
            if t_out > t_bot + 6.0:
                run_hours += 1
                q_left = q / 1000.0                                # kW
                yield_m[mon] += q_left

                # coil 1 of the DHW tank has priority
                q_dhw = 0.0
                if t_dhw < DHW_SET + 5.0:
                    q_dhw = min(q_left, 8.0)
                    t_new = min(60.0, t_dhw + q_dhw * 0.85 * 3.6e6 / c_dhw)
                    q_dhw = (t_new - t_dhw) * c_dhw / 3.6e6 / 0.85
                    t_dhw = t_new
                    q_left -= q_dhw
                    used_m[mon] += q_dhw
                    used_dhw_m[mon] += q_dhw

                # rest -> buffer (through the solar heat exchanger, eta 0.92)
                store_max = max(0.0, (BUF_MAX - t_buf) * c_buf / 3.6e6)
                q_store = min(q_left * 0.92, store_max)
                t_buf += q_store * 3.6e6 / c_buf
                used_m[mon] += q_store
                excess_m[mon] += max(0.0, q_left - q_store)
                # buffer at maximum, sun is strong -> no sink for the collector
                if g > 300.0 and store_max < 0.5:
                    stag_hours += 1
                    t_max = max(t_max, ta + stagnation_dt(g, coll))
        elif g > 30.0:
            excess_m[mon] += a_ap * coll["eta0"] * g / 1000.0

        # ---------------- DHW draw ------------------------------------------
        e = e_dhw_day * prof[int(r["time"][9:11])]
        e = min(e, max(0.0, (t_dhw - 10.0) * c_dhw / 3.6e6))
        t_dhw -= e * 3.6e6 / c_dhw
        t_dhw -= ua_dhw * (t_dhw - 22.0) * 3600.0 / c_dhw

        # ---------------- heating -------------------------------------------
        q_heat = H_TOT * max(0.0, T_SET - ta) / 1000.0 * scale[mon]
        demand_m[mon] += q_heat
        t_top = t_buf + T_STRAT
        if t_top > 45.0:
            q = min(q_heat, max(0.0, (t_top - 40.0) * c_buf / 3.6e6))
            t_buf -= q * 3.6e6 / c_buf
            q_heat -= q
        unmet_m[mon] += q_heat

        # ---------------- DHW coil 2 from the buffer -------------------------
        if t_dhw < 50.0 and t_buf + T_STRAT > 55.0:
            q = min(6.0, max(0.0, (50.0 - t_dhw) * c_dhw / 3.6e6),
                    max(0.0, (t_buf + T_STRAT - 55.0) * c_buf / 3.6e6))
            t_dhw += q * 0.85 * 3.6e6 / c_dhw
            t_buf -= q * 3.6e6 / c_buf

        # ---------------- backup heat source --------------------------------
        need_backup = (t_buf + T_STRAT < 45.0 and q_heat > 0.05) or (t_dhw < 45.0)
        if need_backup and t_buf < BUF_SET:
            q_b = min(15.0, (BUF_SET - t_buf) * c_buf / 3.6e6)
            t_buf += q_b * 3.6e6 / c_buf
            backup_m[mon] += q_b

        t_buf -= ua_buf * (t_buf - 22.0) * 3600.0 / c_buf
        t_buf = max(20.0, min(BUF_MAX, t_buf))
        t_top_m[mon] += t_buf + T_STRAT
        if t_buf + T_STRAT > 90.0:
            hot_hours += 1
            if r["time"][:8] != hot_day:
                hot_day = r["time"][:8]
                hot_days += 1
        t_bot_m[mon] += max(12.0, t_buf - T_STRAT)
        hcnt[mon] += 1

    ny = float(NYEARS)
    yield_m = [x / ny for x in yield_m]
    used_m = [x / ny for x in used_m]
    used_dhw_m = [x / ny for x in used_dhw_m]
    excess_m = [x / ny for x in excess_m]
    backup_m = [x / ny for x in backup_m]
    demand_m = [x / ny for x in demand_m]
    unmet_m = [x / ny for x in unmet_m]
    run_hours = run_hours / ny
    # energy actually delivered to the loads = load - backup (storage change ~ 0 over the year)
    used_m = [max(0.0, demand_m[i] + e_dhw_day * HOURS[i] / 24.0 - backup_m[i]) for i in range(12)]
    used_dhw_m = [min(u, e_dhw_day * HOURS[i] / 24.0) for i, u in enumerate(used_dhw_m)]

    return dict(
        n=n_coll, type="flat" if coll is FLAT else "tube", v_buf=v_buf,
        area_gross=n_coll * coll["a_gross"], area_ap=a_ap,
        yield_m=yield_m, used_m=used_m, used_h_m=used_h_m, used_dhw_m=used_dhw_m,
        excess_m=excess_m, backup_m=backup_m, demand_m=demand_m, unmet_m=unmet_m,
        yield_a=sum(yield_m), used_a=sum(used_m),
        used_dhw=sum(used_dhw_m), used_h=sum(used_m) - sum(used_dhw_m),
        excess_a=sum(excess_m),
        unrealised_a=sum(yield_m) - sum(used_m),
        backup_a=sum(backup_m), heat_a=sum(q_heat_m), unmet_a=sum(unmet_m),
        dhw_load_a=e_dhw_day * 365.0,
        t_top=[t_top_m[i] / hcnt[i] for i in range(12)],
        t_bot=[t_bot_m[i] / hcnt[i] for i in range(12)],
        run_hours=run_hours,
        stagnation_hours=stag_hours / ny,
        hot_hours=hot_hours / ny,
        hot_days=hot_days / ny,
        t_stag_max=t_max,
        specific_yield=sum(yield_m) / a_ap,
    )


if __name__ == "__main__":
    print(f"H_tr={H_TR:.1f} W/K  H_ve={H_VE:.1f} W/K  H_tot={H_TOT:.1f} W/K")
    print(f"P_design={P_DESIGN:.2f} kW ({P_DESIGN*1000/A_USE:.1f} W/m2)")
    qm = monthly_demand()
    print("heating demand kWh/month:", [round(x) for x in qm], "annual", round(sum(qm)))
    print("DHW demand kWh/a:", round(DHW_DAY * 4186 * 50 / 3.6e6 * 365))

    out = []
    for coll, name in ((FLAT, "flat"), (TUBE, "tube")):
        for n in (4, 5, 6):
            for v in (500, 800, 1000):
                r = simulate(n, coll, v)
                r["type"] = name
                out.append(r)
                print(f"{name:5s} n={n} {r['area_gross']:.1f} m2 V={v:4d} | "
                      f"yield {r['yield_a']:5.0f} ({r['specific_yield']:3.0f} kWh/m2ap) "
                      f"used {r['used_a']:5.0f} excess {r['excess_a']:5.0f} "
                      f"backup {r['backup_a']:5.0f} unmet {r['unmet_a']:.0f}")
    json.dump(out, open(os.path.join(DATA, "model_results.json"), "w"), indent=1)
