"""
FruitBlend24 — Steps 2-5: P&L vs budget, demand & pricing, promotions, inventory & 3-month outlook.
Input : clean/tables.pkl (from 01_clean_data.py)
Output: results.pkl (all tables for charts / workbook / deck)
"""
from pathlib import Path
import numpy as np
import pandas as pd

OUT = Path(__file__).parent
t = pd.read_pickle(OUT / "clean" / "tables.pkl")
o, fc, w = t["orders_clean"].copy(), t["fruit_cost_weekly"], t["waste_clean"].copy()
cs = t["cost_sku"].set_index("sku")
ovh = t["kitchen_overhead"].set_index("kitchen")["fixed_monthly_overhead_thb"]
bud = t["monthly_budget"].set_index("month")
SKUS = ["Watermelon", "Pineapple", "Guava", "PassionFruit", "MixedBerryPremium"]
KITCH = ["Pattaya_Central", "Pattaya_Beach", "BKK_Sukhumvit", "BKK_Ladprao"]
PACK = cs.packaging_cost_per_cup_thb
LAB = cs.labor_cost_per_cup_thb
PRICE = cs.base_price_thb
R = {}

# =============================================================== 1. P&L (task 4)
# Gross profit definition (matches the budget's ~26% GP margin):
#   GP = gross revenue − platform commission − fruit − packaging − labor − waste (fruit+packaging of discarded cups)
# Operating profit = GP − fixed kitchen overhead
o = o.merge(fc[["week_start", "sku", "fruit_cost_per_cup_thb"]], on=["week_start", "sku"], how="left")
assert o.fruit_cost_per_cup_thb.notna().all()
o["discount_thb"] = (o.base_price_thb - o.price_thb) * o.units_sold
o["commission_thb"] = o.gross_revenue_thb * o.commission_rate
o["fruit_thb"] = o.units_sold * o.fruit_cost_per_cup_thb
o["packaging_thb"] = o.units_sold * o.sku.map(PACK)
o["labor_thb"] = o.units_sold * o.sku.map(LAB)
o["cm_thb"] = o.gross_revenue_thb - o.commission_thb - o.fruit_thb - o.packaging_thb - o.labor_thb
o["cm_fullprice_thb"] = o.units_sold * o.base_price_thb * (1 - o.commission_rate) - (o.fruit_thb + o.packaging_thb + o.labor_thb)
w["month"] = w.date.dt.to_period("M").dt.to_timestamp()

VAL = ["units_sold", "gross_revenue_thb", "discount_thb", "commission_thb", "fruit_thb", "packaging_thb", "labor_thb"]


def pnl(keys):
    a = o.groupby(keys)[VAL].sum()
    a["waste_units"] = w.groupby(keys).units_wasted.sum()
    a["waste_thb"] = w.groupby(keys).est_waste_cost_thb.sum()
    a["gross_profit_thb"] = a.gross_revenue_thb - a.commission_thb - a.fruit_thb - a.packaging_thb - a.labor_thb - a.waste_thb
    a["gp_margin"] = a.gross_profit_thb / a.gross_revenue_thb
    a["gp_per_cup_thb"] = a.gross_profit_thb / a.units_sold
    a["avg_price_thb"] = a.gross_revenue_thb / a.units_sold
    a["waste_rate"] = a.waste_units / (a.waste_units + a.units_sold)
    return a


pm = pnl(["month"])
pm["overhead_thb"] = ovh.sum()
pm["operating_profit_thb"] = pm.gross_profit_thb - pm.overhead_thb
pm["budget_revenue_thb"] = bud.budget_revenue_thb
pm["budget_gp_thb"] = bud.budget_gross_profit_thb
pm["rev_var_thb"] = pm.gross_revenue_thb - pm.budget_revenue_thb
pm["gp_var_thb"] = pm.gross_profit_thb - pm.budget_gp_thb
pm["rev_var_pct"] = pm.rev_var_thb / pm.budget_revenue_thb
pm["gp_var_pct"] = pm.gp_var_thb / pm.budget_gp_thb
R["pnl_month"] = pm

ps = pnl(["sku"]).reindex(SKUS)
R["pnl_sku"] = ps
pk = pnl(["kitchen"]).reindex(KITCH)
pk["overhead_thb"] = ovh * 12
pk["operating_profit_thb"] = pk.gross_profit_thb - pk.overhead_thb
pk["breakeven_gp_uplift"] = pk.overhead_thb / pk.gross_profit_thb - 1
R["pnl_kitchen"] = pk
pkm = pnl(["kitchen", "month"])
pkm["operating_profit_thb"] = pkm.gross_profit_thb - pkm.index.get_level_values(0).map(ovh).values
R["pnl_kitchen_month"] = pkm
R["pnl_sku_month"] = pnl(["month", "sku"])
R["pnl_kitchen_sku"] = pnl(["kitchen", "sku"])

# GP variance bridge vs budget by season (where did the miss come from?)
pm_s = pm.copy()
pm_s["season"] = np.select([pm_s.index.month.isin([3, 4, 5]), pm_s.index.month.isin([6, 7, 8, 9, 10])],
                           ["Hot (Mar–May)", "Rainy (Jun–Oct)"], "Cool (Nov–Feb)")
R["season"] = pm_s.groupby("season")[["gross_revenue_thb", "budget_revenue_thb", "gross_profit_thb", "budget_gp_thb", "operating_profit_thb"]].sum()

# Fruit-cost shock: what Jun–Aug GP would have been at Mar–May fruit cost per cup
fcm = fc.assign(month=fc.week_start.dt.to_period("M").dt.to_timestamp())
pre = o[o.month.between("2026-03-01", "2026-05-01")].groupby("sku").apply(lambda g: g.fruit_thb.sum() / g.units_sold.sum())
ja = o[o.month >= "2026-06-01"]
shock = (ja.fruit_thb - ja.units_sold * ja.sku.map(pre)).groupby(ja.sku).sum()
R["fruit_shock_JunAug"] = pd.DataFrame({"fruit_cost_MarMay": pre,
                                        "fruit_cost_JunAug": ja.groupby("sku").apply(lambda g: g.fruit_thb.sum() / g.units_sold.sum()),
                                        "extra_cost_JunAug_thb": shock}).reindex(SKUS)

# =============================================================== 2. Demand (task 2)
days = o.groupby("day_of_week").date.nunique()
R["demand_dow"] = (o.groupby("day_of_week").units_sold.sum() / days).rename("cups_per_day")
R["demand_hour"] = o.pivot_table(index="hour", columns=o.kitchen.str.split("_").str[0], values="units_sold", aggfunc="sum")
R["demand_hour"] = R["demand_hour"] / R["demand_hour"].sum()
R["demand_month_sku"] = o.pivot_table(index="month", columns="sku", values="units_sold", aggfunc="sum")[SKUS]
R["platform_month"] = o.pivot_table(index="month", columns="platform_name", values="units_sold", aggfunc="sum")
R["platform_pnl"] = o.groupby("platform_name").agg(units=("units_sold", "sum"), revenue=("gross_revenue_thb", "sum"),
                                                   commission=("commission_thb", "sum"), cm=("cm_thb", "sum"))
R["platform_pnl"]["cm_per_cup"] = R["platform_pnl"].cm / R["platform_pnl"].units

# =============================================================== 3. Promotions (task 3)
d = o.groupby(["date", "kitchen", "sku"]).agg(u=("units_sold", "sum"), rev=("gross_revenue_thb", "sum"),
                                             cm=("cm_thb", "sum"), cmf=("cm_fullprice_thb", "sum"),
                                             code=("base_code", "max"), dow=("day_of_week", "first")).reset_index()
d["wkend"] = d.dow >= 5
rows = []
for (k, s), g in d.groupby(["kitchen", "sku"]):
    g = g.set_index("date").sort_index()
    base = g[g.code == "RC000"]
    for dt, r in g[g.code != "RC000"].iterrows():
        # baseline = same kitchen×SKU, non-promo days within ±28 days, same weekday/weekend type
        win = base[(abs((base.index - dt).days) <= 28) & (base.wkend == r.wkend)]
        bu = win.u.mean()
        rows.append(dict(date=dt, kitchen=k, sku=s, code=r.code, units=r.u, baseline_units=bu, cm=r.cm,
                         baseline_cm=bu * win.cmf.sum() / win.u.sum(), rev=r.rev,
                         baseline_rev=bu * win.rev.sum() / win.u.sum()))
pr = pd.DataFrame(rows)
DISC = t["rate_code_dim"].set_index("base_code").discount_pct
NAME = t["rate_code_dim"].set_index("base_code").rate_code_name


def promo_tbl(keys):
    a = pr.groupby(keys)[["units", "baseline_units", "rev", "baseline_rev", "cm", "baseline_cm"]].sum()
    a["promo_days"] = pr.groupby(keys).date.nunique()
    a["lift"] = a.units / a.baseline_units - 1
    c = a.index.get_level_values(0) if isinstance(a.index, pd.MultiIndex) else a.index
    a["discount_pct"] = c.map(DISC).values
    a["implied_elasticity"] = np.log(a.units / a.baseline_units) / np.log(1 - a.discount_pct)
    a["incremental_units"] = a.units - a.baseline_units
    a["incremental_rev_thb"] = a.rev - a.baseline_rev
    a["incremental_profit_thb"] = a.cm - a.baseline_cm
    a["profit_per_promo_day_thb"] = a.incremental_profit_thb / a.promo_days
    return a


pc = promo_tbl("code")
pc.insert(0, "promo_name", pc.index.map(NAME))
# break-even lift: lift needed so that promo-day margin equals baseline margin
avg_cm_cup = (pr.baseline_cm.sum() / pr.baseline_units.sum())
avg_price = (pr.baseline_rev.sum() / pr.baseline_units.sum())
pc["breakeven_lift"] = [avg_cm_cup / (avg_cm_cup - DISC[c] * avg_price * (1 - 0.273)) - 1 for c in pc.index]
R["promo_code"] = pc
R["promo_code_sku"] = promo_tbl(["code", "sku"])
R["promo_days"] = pr

# cannibalisation check: other SKUs on RC101 (single-SKU) days
out = []
for _, p in pr[pr.code == "RC101"][["date", "sku"]].drop_duplicates().iterrows():
    oth = d[(d.sku != p.sku)]
    for (k, s), g in oth.groupby(["kitchen", "sku"]):
        g = g.set_index("date")
        if p.date not in g.index or g.loc[p.date, "code"] != "RC000":
            continue
        rr = g.loc[p.date]
        b = g[(g.code == "RC000") & (abs((g.index - p.date).days) <= 28) & (g.wkend == rr.wkend) & (g.index != p.date)]
        out.append((rr.u, b.u.mean()))
c = np.array(out)
R["rc101_other_sku_change"] = c[:, 0].sum() / c[:, 1].sum() - 1

# RC102 break-even on future repeat purchases (new-user campaign)
rc102 = pc.loc["RC102"]
full_cm_cup = pr[pr.code == "RC102"].baseline_cm.sum() / pr[pr.code == "RC102"].baseline_units.sum()
R["rc102_repeat_cups_needed"] = -rc102.incremental_profit_thb / full_cm_cup
R["rc102_repeat_per_incr_cup"] = R["rc102_repeat_cups_needed"] / rc102.incremental_units

# =============================================================== 4. Pricing (task 2)
rec = o[o.date >= "2026-06-01"]  # recent 3 months (current cost regime)
comm_mix = (rec.commission_thb.groupby(rec.sku).sum() / rec.gross_revenue_thb.groupby(rec.sku).sum())
fruit_now = fc[fc.week_start >= "2026-07-06"].groupby("sku").fruit_cost_per_cup_thb.mean()  # last 8 weeks
w_rec = w[w.date >= "2026-06-01"]
waste_rate_now = w_rec.groupby("sku").units_wasted.sum() / rec.groupby("sku").units_sold.sum()
base_units_day = rec[rec.base_code == "RC000"].groupby("sku").units_sold.sum() / rec[rec.base_code == "RC000"].groupby("sku").date.nunique()
el_sku = R["promo_code_sku"].loc["RC101", "implied_elasticity"]
EL = {"Low (−0.8, from RC103)": -0.8, "Mid (SKU-specific, from RC101)": None, "High (−2.4, from RC102)": -2.4}

uc = pd.DataFrame({"price_thb": PRICE, "commission_rate": comm_mix, "fruit_cost_thb": fruit_now,
                   "packaging_thb": PACK, "labor_thb": LAB}).reindex(SKUS)
uc["net_price_after_comm"] = uc.price_thb * (1 - uc.commission_rate)
uc["waste_rate"] = waste_rate_now
uc["waste_cost_per_sold_cup"] = (uc.fruit_cost_thb + uc.packaging_thb) * uc.waste_rate / (1 - uc.waste_rate)
uc["margin_per_cup_thb"] = uc.net_price_after_comm - uc.fruit_cost_thb - uc.packaging_thb - uc.labor_thb - uc.waste_cost_per_sold_cup
uc["base_units_per_day"] = base_units_day
uc["elasticity_rc101"] = el_sku
var = uc.fruit_cost_thb + uc.packaging_thb + uc.labor_thb + uc.waste_cost_per_sold_cup
uc["breakeven_price_thb"] = var / (1 - uc.commission_rate)
R["unit_econ_now"] = uc

sim = []
for s in SKUS:
    for en, e in EL.items():
        e = el_sku[s] if e is None else e
        for dp in [-0.10, -0.05, 0, 0.05, 0.10, 0.15, 0.20]:
            p1 = uc.price_thb[s] * (1 + dp)
            q = uc.base_units_per_day[s] * (1 + dp) ** e
            m = p1 * (1 - uc.commission_rate[s]) - var[s]
            sim.append(dict(sku=s, elasticity_case=en, elasticity=e, price_change=dp, new_price=p1,
                            units_per_day=q, margin_per_cup=m, gp_per_month=q * m * 30.4))
sim = pd.DataFrame(sim)
b0 = sim[sim.price_change == 0].set_index(["sku", "elasticity_case"]).gp_per_month
sim["delta_gp_per_month"] = sim.gp_per_month - sim.set_index(["sku", "elasticity_case"]).index.map(b0).values
R["price_sim"] = sim

# =============================================================== 5. Forecast & inventory (task 5)
# Daily demand grid kitchen×SKU×date (0 when no rows)
grid = pd.MultiIndex.from_product([pd.date_range("2025-09-01", "2026-08-31"), KITCH, SKUS], names=["date", "kitchen", "sku"])
dd = d.set_index(["date", "kitchen", "sku"]).reindex(grid)
dd = dd[~((dd.index.get_level_values("sku") == "MixedBerryPremium") & (dd.index.get_level_values("date") < "2026-03-01"))]
dd["u"] = dd.u.fillna(0)
dd["code"] = dd.code.fillna("RC000")
dd = dd.reset_index()
# de-promoted demand: promo days replaced by their estimated baseline
dd = dd.merge(pr[["date", "kitchen", "sku", "baseline_units"]], how="left", on=["date", "kitchen", "sku"])
dd["u_base"] = np.where(dd.code != "RC000", dd.baseline_units, dd.u)

# (a) Operational weekly forecast = mean of same weekday over previous 4 weeks (de-promoted) — backtest Jun–Aug 2026
dd = dd.sort_values(["kitchen", "sku", "date"])
dd["dow"] = dd.date.dt.dayofweek
dd["fc_4wk"] = dd.groupby(["kitchen", "sku", "dow"]).u_base.transform(lambda s: s.shift(1).rolling(4, min_periods=4).mean())
bt = dd[(dd.date >= "2026-06-01") & dd.fc_4wk.notna()].copy()
bt["week"] = bt.date - pd.to_timedelta(bt.dow, unit="D")
wk = bt.groupby(["week", "kitchen", "sku"])[["u_base", "fc_4wk"]].sum()
R["backtest_wape_weekly"] = (wk.u_base - wk.fc_4wk).abs().groupby("sku").sum() / wk.u_base.groupby("sku").sum()
R["backtest_bias_weekly"] = (wk.fc_4wk - wk.u_base).groupby("sku").sum() / wk.u_base.groupby("sku").sum()
R["backtest_wape_daily"] = (bt.u_base - bt.fc_4wk).abs().groupby(bt.sku).sum() / bt.u_base.groupby(bt.sku).sum()
# daily error spread (for safety buffer): std of (actual/forecast − 1)
bt["err"] = bt.u_base / bt.fc_4wk - 1
R["daily_err_sd"] = bt.groupby("sku").err.std()

# (b) 3-month outlook (Sep–Nov 2026): seasonal naive on de-promoted demand, aligned by weekday (t − 364 days)
#     growth factor g = 1.00 (Aug-26 run-rate ≈ Sep-25 run-rate; only 12 months of history, so no trend is assumed)
aug26 = dd[(dd.date.dt.month == 8) & (dd.sku != "MixedBerryPremium")].u_base.sum() / 31
sep25 = dd[(dd.date < "2025-10-01") & (dd.sku != "MixedBerryPremium")].u_base.sum() / 30
R["growth_check"] = dict(aug26_per_day=aug26, sep25_per_day=sep25, ratio=aug26 / sep25)
G = 1.0
fdates = pd.date_range("2026-09-01", "2026-11-30")
hist = dd.set_index(["date", "kitchen", "sku"])
f = pd.MultiIndex.from_product([fdates, KITCH, SKUS], names=["date", "kitchen", "sku"]).to_frame(index=False)
f["ly_date"] = f.date - pd.Timedelta(days=364)
core = f.sku != "MixedBerryPremium"
f.loc[core, "base_units"] = hist.u_base.reindex(pd.MultiIndex.from_frame(f.loc[core, ["ly_date", "kitchen", "sku"]])).values * G
f.loc[core, "ly_units_actual"] = hist.u.reindex(pd.MultiIndex.from_frame(f.loc[core, ["ly_date", "kitchen", "sku"]])).values * G
f.loc[core, "ly_code"] = hist.code.reindex(pd.MultiIndex.from_frame(f.loc[core, ["ly_date", "kitchen", "sku"]])).values
# Mixed Berry (no last year): Aug-26 weekday profile × monthly decay fitted on Jun–Aug 2026
mbm = dd[(dd.sku == "MixedBerryPremium") & (dd.date >= "2026-06-01")].groupby(dd.date.dt.month).u_base.sum() / np.array([30, 31, 31])
decay = np.exp(np.polyfit([0, 1, 2], np.log(mbm.values), 1)[0])
R["mb_monthly_decay"] = decay
mb_aug = dd[(dd.sku == "MixedBerryPremium") & (dd.date >= "2026-08-01")].groupby(["kitchen", "dow"]).u_base.mean()
mbi = ~core
mm = (f.loc[mbi, "date"].dt.month - 8)
f.loc[mbi, "base_units"] = mb_aug.reindex(pd.MultiIndex.from_arrays([f.loc[mbi, "kitchen"], f.loc[mbi, "date"].dt.dayofweek])).values * decay ** mm.values
f.loc[mbi, "ly_units_actual"] = f.loc[mbi, "base_units"]
f.loc[mbi, "ly_code"] = "RC000"
f["month"] = f.date.dt.to_period("M").dt.to_timestamp()

# Cost & mix assumptions for the outlook
comm_k = (rec.commission_thb.groupby([rec.kitchen, rec.sku]).sum() / rec.gross_revenue_thb.groupby([rec.kitchen, rec.sku]).sum())
wr_k = (w_rec.groupby(["kitchen", "sku"]).units_wasted.sum() / rec.groupby(["kitchen", "sku"]).units_sold.sum())
f["commission_rate"] = comm_k.reindex(pd.MultiIndex.from_frame(f[["kitchen", "sku"]])).values
f["fruit_cost"] = f.sku.map(fruit_now)
f["waste_ratio_now"] = wr_k.reindex(pd.MultiIndex.from_frame(f[["kitchen", "sku"]])).values  # wasted / sold

LIFT = pc.lift  # promo lifts measured above
PLAN_PRICE = {"Watermelon": 47, "Pineapple": 51, "Guava": 49, "PassionFruit": 75, "MixedBerryPremium": 89}
PLAN_WASTE_CAP = {"PassionFruit": 0.06}  # wasted/sold target via daypart batch prep
DOUBLE_DAYS = {pd.Timestamp("2026-09-09"), pd.Timestamp("2026-10-10"), pd.Timestamp("2026-11-11")}


def scenario(name, price, keep_codes, drop_mb, waste_cap, el_case, frame=None, double_days=DOUBLE_DAYS):
    x = (f if frame is None else frame).copy()
    if drop_mb:
        x = x[x.sku != "MixedBerryPremium"].copy()
    x["list_price"] = x.sku.map(price)
    # promo calendar: status quo repeats last year's calendar (by aligned weekday) + double days; plan keeps only RC102
    x["code"] = np.where(x.date.isin(double_days), "RC102", np.where(x.ly_code.isin(["RC101", "RC103"]), x.ly_code, "RC000"))
    x.loc[~x.code.isin(keep_codes + ["RC000"]), "code"] = "RC000"
    x["disc"] = x.code.map(DISC).fillna(0)
    x["lift"] = x.code.map(LIFT).fillna(0)
    e = x.sku.map(el_sku) if el_case == "mid" else (-0.8 if el_case == "low" else -2.4)
    x["price_effect"] = (x.list_price / x.sku.map(PRICE)) ** e
    x["units"] = x.base_units * x.price_effect * (1 + x.lift)
    x["price"] = x.list_price * (1 - x.disc)
    x["revenue"] = x.units * x.price
    x["commission"] = x.revenue * x.commission_rate
    x["fruit"] = x.units * x.fruit_cost
    x["packaging"] = x.units * x.sku.map(PACK)
    x["labor"] = x.units * x.sku.map(LAB)
    wr = x.waste_ratio_now.copy()
    for s_, cap in waste_cap.items():
        wr = np.where(x.sku == s_, np.minimum(wr, cap), wr)
    x["waste_ratio"] = wr
    x["waste_units"] = x.units * x.waste_ratio
    x["waste"] = x.waste_units * (x.fruit_cost + x.sku.map(PACK))
    x["prep_units"] = x.units + x.waste_units
    x["gp"] = x.revenue - x.commission - x.fruit - x.packaging - x.labor - x.waste
    x["scenario"] = name
    return x


sq = scenario("Status quo", dict(PRICE), ["RC101", "RC102", "RC103"], False, {}, "mid")
plan = scenario("Recommended plan", PLAN_PRICE, ["RC102"], True, PLAN_WASTE_CAP, "mid")
plan_lo = scenario("Plan (low elasticity)", PLAN_PRICE, ["RC102"], True, PLAN_WASTE_CAP, "low")
plan_hi = scenario("Plan (high elasticity)", PLAN_PRICE, ["RC102"], True, PLAN_WASTE_CAP, "high")


def summ(x):
    a = x.groupby("month")[["units", "revenue", "commission", "fruit", "packaging", "labor", "waste", "gp", "prep_units", "waste_units"]].sum()
    a["overhead"] = ovh.sum()
    a["operating_profit"] = a.gp - a.overhead
    a["budget_revenue"] = 2_700_000
    a["budget_gp"] = 700_000
    a["gp_vs_budget"] = a.gp - a.budget_gp
    return a


R["outlook"] = {n: summ(x) for n, x in [("Status quo", sq), ("Recommended plan", plan),
                                         ("Plan (low elasticity)", plan_lo), ("Plan (high elasticity)", plan_hi)]}
# Bridge status quo → plan (Sep–Nov total GP), one lever at a time
steps = [("Status quo", dict(PRICE), ["RC101", "RC102", "RC103"], False, {}),
         ("Delist Mixed Berry", dict(PRICE), ["RC101", "RC102", "RC103"], True, {}),
         ("Stop RC101 & RC103", dict(PRICE), ["RC102"], True, {}),
         ("Reprice PF/WM/PA", PLAN_PRICE, ["RC102"], True, {}),
         ("Cut PF waste to 6%", PLAN_PRICE, ["RC102"], True, PLAN_WASTE_CAP)]
gp_steps = [scenario(n, p, k, m, wc, "mid").gp.sum() for n, p, k, m, wc in steps]
R["bridge"] = pd.DataFrame({"step": [s[0] for s in steps], "gp_sep_nov": gp_steps,
                            "delta": np.r_[np.nan, np.diff(gp_steps)]})

# Back-cast: run the same model over the last 12 months (validates the model vs actual P&L and sizes the
# full-year value of the plan). Inputs are the actual weekly fruit cost, actual platform mix and waste ratio by
# kitchen×SKU×month, de-promoted demand, and the actual promo calendar.
h = dd[["date", "kitchen", "sku", "u_base", "code"]].rename(columns={"u_base": "base_units", "code": "ly_code"}).copy()
h["month"] = h.date.dt.to_period("M").dt.to_timestamp()
h["week_start"] = h.date - pd.to_timedelta(h.date.dt.dayofweek, unit="D")
h = h.merge(fc[["week_start", "sku", "fruit_cost_per_cup_thb"]], how="left", on=["week_start", "sku"]).rename(columns={"fruit_cost_per_cup_thb": "fruit_cost"})
cmk = (o.groupby(["month", "kitchen", "sku"]).commission_thb.sum() / o.groupby(["month", "kitchen", "sku"]).gross_revenue_thb.sum())
wrk = (w.groupby(["month", "kitchen", "sku"]).units_wasted.sum() / o.groupby(["month", "kitchen", "sku"]).units_sold.sum())
idx = pd.MultiIndex.from_frame(h[["month", "kitchen", "sku"]])
h["commission_rate"] = cmk.reindex(idx).values
h["waste_ratio_now"] = wrk.reindex(idx).values
rc102_days = set(o.loc[o.base_code == "RC102", "date"].unique())
h_sq = scenario("Back-cast status quo", dict(PRICE), ["RC101", "RC102", "RC103"], False, {}, "mid", h, rc102_days)
h_pl = scenario("Back-cast plan", PLAN_PRICE, ["RC102"], True, PLAN_WASTE_CAP, "mid", h, rc102_days)
bc = pd.DataFrame({"actual_gp": pm.gross_profit_thb, "model_status_quo_gp": h_sq.groupby("month").gp.sum(),
                   "model_plan_gp": h_pl.groupby("month").gp.sum(), "actual_revenue": pm.gross_revenue_thb,
                   "model_status_quo_rev": h_sq.groupby("month").revenue.sum(), "model_plan_rev": h_pl.groupby("month").revenue.sum()})
bc["plan_uplift_gp"] = bc.model_plan_gp - bc.model_status_quo_gp
bc["plan_op"] = bc.actual_gp + bc.plan_uplift_gp - ovh.sum()
bc["plan_op_excl_ladprao"] = bc.plan_op - (h_pl[h_pl.kitchen == "BKK_Ladprao"].groupby("month").gp.sum() - ovh["BKK_Ladprao"])
R["backcast"] = bc

# Inventory needs: weekly prep cups and fruit spend per kitchen×SKU (plan) + safety buffer guidance
plan["week"] = plan.date - pd.to_timedelta(plan.date.dt.dayofweek, unit="D")
inv = plan.groupby(["week", "kitchen", "sku"]).agg(forecast_cups=("units", "sum"), prep_cups=("prep_units", "sum"),
                                                   fruit_cost_per_cup=("fruit_cost", "first")).reset_index()
sd = R["daily_err_sd"]
inv["safety_cups_per_day"] = (inv.forecast_cups / 7) * inv.sku.map(sd) * 0.0  # placeholder, filled below
# Newsvendor critical ratio with plan prices: CR = underage / (underage + overage)
cu = (pd.Series(PLAN_PRICE) * (1 - comm_mix) - (fruit_now + PACK + LAB)).reindex(SKUS[:4])
co = (fruit_now + PACK).reindex(SKUS[:4])
cr = (cu / (cu + co)).clip(0.05, 0.95)
from scipy.stats import norm
z = cr.map(norm.ppf)
nv = pd.DataFrame({"underage_cost_lost_margin": cu, "overage_cost_waste": co, "critical_ratio": cr, "z": z,
                   "daily_forecast_error_sd": sd.reindex(SKUS[:4]), "weekly_wape": R["backtest_wape_weekly"].reindex(SKUS[:4])})
nv["buffer_pct_of_forecast"] = (nv.z * nv.daily_forecast_error_sd).clip(lower=0)
R["newsvendor"] = nv
inv["safety_cups_per_day"] = (inv.forecast_cups / 7) * inv.sku.map(nv.buffer_pct_of_forecast)
inv["fruit_spend_thb"] = inv.prep_cups * inv.fruit_cost_per_cup
R["inventory_weekly"] = inv
plan["fruit_purchase"] = plan.prep_units * plan.fruit_cost  # fruit bought = cups prepared (sold + wasted) × cost
R["inventory_month"] = plan.groupby(["month", "sku"]).agg(forecast_cups=("units", "sum"), prep_cups=("prep_units", "sum"),
                                                          waste_cups=("waste_units", "sum"), fruit_purchase_thb=("fruit_purchase", "sum")).reset_index()
R["forecast_daily_plan"] = plan[["date", "kitchen", "sku", "base_units", "code", "list_price", "units", "prep_units", "waste_units", "revenue", "gp"]]
R["forecast_daily_sq"] = sq[["date", "kitchen", "sku", "base_units", "code", "list_price", "units", "prep_units", "waste_units", "revenue", "gp"]]

# Kitchen view in plan + Ladprao option
pk_plan = plan.groupby("kitchen").gp.sum().reindex(KITCH).to_frame("gp_sep_nov")
pk_plan["overhead_sep_nov"] = ovh * 3
pk_plan["op_sep_nov"] = pk_plan.gp_sep_nov - pk_plan.overhead_sep_nov
R["kitchen_plan"] = pk_plan

# Waste savings history: if MB & PF had run at core-SKU waste rate
core_rate = ps.loc[["Watermelon", "Pineapple", "Guava"]].waste_units.sum() / ps.loc[["Watermelon", "Pineapple", "Guava"]].units_sold.sum()
R["core_waste_ratio"] = core_rate
R["assumptions"] = pd.DataFrame([
    ["Gross profit definition", "Revenue − platform commission − fruit − packaging − labor − waste cost; overhead below GP", "Matches budget GP margin (~26%)"],
    ["Commission", "LINE MAN 30%, Grab 24% of gross revenue; outlook uses Jun–Aug 2026 platform mix per kitchen×SKU", "platform_commission_rate"],
    ["Promo baseline", "Same kitchen×SKU, non-promo days within ±28 days, same weekday/weekend type", "Controls for season and weekend"],
    ["Elasticity", "Promo-day log-lift ÷ log(1−discount); RC101 SKU-specific used as mid case, −0.8 / −2.4 as bounds", "Promo response may overstate permanent-price response; test first"],
    ["Forecast", "Seasonal naive: same weekday last year (t−364), promo days replaced by baseline, growth = 1.00", f"Aug-26 vs Sep-25 core run-rate ratio = {aug26 / sep25:.3f}"],
    ["Mixed Berry forecast (status quo)", f"Aug-26 weekday profile × {decay:.3f} per month (Jun–Aug trend)", "No last-year history"],
    ["Fruit cost", "Average of last 8 weeks (6 Jul – 31 Aug 2026) held flat", "Conservative: Passion Fruit stays at ~28 THB"],
    ["Waste", "Jun–Aug 2026 wasted/sold ratio per kitchen×SKU; plan caps Passion Fruit at 6%", "Core SKUs already 3–6%"],
    ["Overhead", "670k THB/month (4 kitchens), unchanged", "cost_assumptions"],
    ["Mixed Berry delisting", "No demand transfer to other SKUs assumed", "Conservative; any transfer is upside"],
], columns=["item", "assumption", "basis / note"])

# frames + parameters the app needs to re-run scenarios live
R["forecast_frame"] = f[["date", "month", "kitchen", "sku", "base_units", "ly_code", "commission_rate", "fruit_cost", "waste_ratio_now"]]
R["history_frame"] = h[["date", "month", "kitchen", "sku", "base_units", "ly_code", "commission_rate", "fruit_cost", "waste_ratio_now"]]
R["params"] = {
    "price": {k: float(v) for k, v in PRICE.items()}, "packaging": {k: float(v) for k, v in PACK.items()},
    "labor": {k: float(v) for k, v in LAB.items()}, "discount": {k: float(v) for k, v in DISC.items()},
    "lift": {k: float(v) for k, v in LIFT.items()}, "elasticity_sku": {k: float(v) for k, v in el_sku.items()},
    "overhead": {k: float(v) for k, v in ovh.items()}, "plan_price": PLAN_PRICE, "plan_waste_cap": PLAN_WASTE_CAP,
    "double_days_outlook": sorted(d.strftime("%Y-%m-%d") for d in DOUBLE_DAYS),
    "double_days_history": sorted(pd.Timestamp(d).strftime("%Y-%m-%d") for d in rc102_days),
    "mb_monthly_decay": float(decay), "growth": G, "core_waste_ratio": float(core_rate),
}
pd.to_pickle(R, OUT / "results.pkl")

# ------------------------------------------------------------------ console summary
fmt = lambda v: f"{v/1e6:,.2f}M"
print("FY P&L: rev", fmt(pm.gross_revenue_thb.sum()), "GP", fmt(pm.gross_profit_thb.sum()), "budget GP", fmt(pm.budget_gp_thb.sum()),
      "OP", fmt(pm.operating_profit_thb.sum()), "months OP<0:", (pm.operating_profit_thb < 0).sum())
print(R["season"].round(-3))
print(ps[["units_sold", "gross_profit_thb", "gp_margin", "gp_per_cup_thb", "waste_rate"]].round(3))
print(pk[["gross_profit_thb", "overhead_thb", "operating_profit_thb", "waste_rate", "breakeven_gp_uplift"]].round(3))
print(R["fruit_shock_JunAug"].round(1))
print(pc[["promo_days", "lift", "breakeven_lift", "implied_elasticity", "incremental_units", "incremental_profit_thb", "profit_per_promo_day_thb"]].round(2))
print("RC101 other-SKU change", round(R["rc101_other_sku_change"], 3), "RC102 repeat cups needed", round(R["rc102_repeat_cups_needed"]), "per incr cup", round(R["rc102_repeat_per_incr_cup"], 2))
print(uc.round(2).to_string())
print("WAPE weekly", R["backtest_wape_weekly"].round(3).to_dict(), "bias", R["backtest_bias_weekly"].round(3).to_dict())
print("WAPE daily", R["backtest_wape_daily"].round(3).to_dict(), "err sd", R["daily_err_sd"].round(3).to_dict())
print("growth", R["growth_check"], "MB decay", round(decay, 3))
for n, a in R["outlook"].items():
    print(n); print((a[["units", "revenue", "gp", "operating_profit", "gp_vs_budget"]] / 1).round(0).to_string())
print(R["bridge"].round(0))
print(nv.round(3))
print(R["kitchen_plan"].round(0))
print(R["inventory_month"].round(0))
