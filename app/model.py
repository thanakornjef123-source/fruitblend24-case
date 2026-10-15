"""Data loading and the business logic behind the FruitBlend24 app.

Everything the app shows is computed here from the CSVs in data/, which 06_export_app_data.py
writes from the cleaned workbook. The scenario engine is the same one used in 03_analysis.py.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

DATA = Path(__file__).parent / "data"

SKUS = ["Watermelon", "Pineapple", "Guava", "PassionFruit", "MixedBerryPremium"]
SKU_LABEL = {"Watermelon": "Watermelon", "Pineapple": "Pineapple", "Guava": "Guava",
             "PassionFruit": "Passion Fruit", "MixedBerryPremium": "Mixed Berry"}
KITCHENS = ["Pattaya_Central", "Pattaya_Beach", "BKK_Sukhumvit", "BKK_Ladprao"]
KITCHEN_LABEL = {k: k.replace("_", " ") for k in KITCHENS}
CODES = {"RC101": "Bundle Deal", "RC102": "Double Day New User", "RC103": "Seasonal Push"}
ELASTICITY_CASES = {"Mid (per product)": "mid", "Low (−0.8)": "low", "High (−2.4)": "high"}
COST_COLS = ["commission_thb", "fruit_thb", "packaging_thb", "labor_thb", "waste_thb"]


# ------------------------------------------------------------------------------------------ loading
def load_all() -> dict:
    p = json.loads((DATA / "params.json").read_text())
    d = {"params": p}
    d["sales"] = pd.read_csv(DATA / "daily_sales.csv", parse_dates=["date"])
    d["waste"] = pd.read_csv(DATA / "daily_waste.csv", parse_dates=["date"])
    d["hourly"] = pd.read_csv(DATA / "hourly.csv")
    d["fruit"] = pd.read_csv(DATA / "fruit_cost_weekly.csv", parse_dates=["week_start"])
    d["budget"] = pd.read_csv(DATA / "budget.csv", parse_dates=["month"])
    d["dq_log"] = pd.read_csv(DATA / "dq_log.csv")
    d["recon"] = pd.read_csv(DATA / "reconciliation.csv")
    d["names"] = pd.read_csv(DATA / "name_mapping.csv")
    d["rate_codes"] = pd.read_csv(DATA / "rate_codes.csv")
    d["promo_days"] = pd.read_csv(DATA / "promo_days.csv", parse_dates=["date"])
    d["unit_econ"] = pd.read_csv(DATA / "unit_economics.csv").set_index("sku")
    d["backtest"] = pd.read_csv(DATA / "backtest.csv").set_index("sku")
    d["assumptions"] = pd.read_csv(DATA / "assumptions.csv")
    for k in ("forecast_frame", "history_frame"):
        d[k] = pd.read_csv(DATA / f"{k}.csv", parse_dates=["date", "month"])
    for k in ("sales", "waste"):
        d[k]["month"] = d[k]["date"].dt.to_period("M").dt.to_timestamp()
    return d


# ------------------------------------------------------------------------------------------ P&L
def pnl(d: dict, by: list[str], kitchens=None, skus=None, platforms=None) -> pd.DataFrame:
    """Gross profit = revenue − commission − fruit − packaging − labor − waste.
    Waste is recorded per kitchen×SKU×day, not per platform: with a platform filter it is
    allocated by that platform's share of cups."""
    s, w = d["sales"], d["waste"]
    if kitchens:
        s, w = s[s.kitchen.isin(kitchens)], w[w.kitchen.isin(kitchens)]
    if skus:
        s, w = s[s.sku.isin(skus)], w[w.sku.isin(skus)]
    key = ["date", "kitchen", "sku"]
    wd = w.groupby(key, as_index=False)[["units_wasted", "est_waste_cost_thb"]].sum()
    tot = s.groupby(key, as_index=False).units_sold.sum().rename(columns={"units_sold": "all_units"})
    if platforms:
        s = s[s.platform_name.isin(platforms)]
    sd = s.groupby(key + ["month"], as_index=False)[
        ["units_sold", "gross_revenue_thb", "discount_thb", "commission_thb", "fruit_thb", "packaging_thb", "labor_thb"]].sum()
    sd = sd.merge(tot, on=key, how="left").merge(wd, on=key, how="left")
    share = (sd.units_sold / sd.all_units).fillna(0)
    sd["waste_units"] = sd.units_wasted.fillna(0) * share
    sd["waste_thb"] = sd.est_waste_cost_thb.fillna(0) * share
    a = sd.groupby(by)[["units_sold", "gross_revenue_thb", "discount_thb", "commission_thb", "fruit_thb",
                        "packaging_thb", "labor_thb", "waste_units", "waste_thb"]].sum()
    a["gross_profit_thb"] = a.gross_revenue_thb - a[COST_COLS].sum(axis=1)
    a["gp_margin"] = a.gross_profit_thb / a.gross_revenue_thb
    a["gp_per_cup"] = a.gross_profit_thb / a.units_sold
    a["waste_rate"] = a.waste_units / (a.waste_units + a.units_sold)
    return a


def overhead(d: dict, kitchens=None) -> float:
    ov = d["params"]["overhead"]
    return sum(v for k, v in ov.items() if not kitchens or k in kitchens)


# ------------------------------------------------------------------------------------------ promotions
def promo_summary(d: dict, by: list[str], kitchens=None, skus=None) -> pd.DataFrame:
    pr = d["promo_days"]
    if kitchens:
        pr = pr[pr.kitchen.isin(kitchens)]
    if skus:
        pr = pr[pr.sku.isin(skus)]
    disc = d["params"]["discount"]
    a = pr.groupby(by)[["units", "baseline_units", "rev", "baseline_rev", "cm", "baseline_cm"]].sum()
    a["promo_days"] = pr.groupby(by).date.nunique()
    a["lift"] = a.units / a.baseline_units - 1
    code = a.index.get_level_values("code")
    a["discount"] = [disc[c] for c in code]
    a["elasticity"] = np.log(a.units / a.baseline_units) / np.log(1 - a.discount)
    a["incremental_units"] = a.units - a.baseline_units
    a["incremental_revenue"] = a.rev - a.baseline_rev
    a["profit_impact"] = a.cm - a.baseline_cm
    a["profit_per_day"] = a.profit_impact / a.promo_days
    # lift needed for the promo day to earn the same margin as a normal day
    m = pr.baseline_cm.sum() / pr.baseline_units.sum()
    p = pr.baseline_rev.sum() / pr.baseline_units.sum()
    c = d["sales"].commission_thb.sum() / d["sales"].gross_revenue_thb.sum()
    a["breakeven_lift"] = [m / (m - disc[x] * p * (1 - c)) - 1 for x in code]
    return a


# ------------------------------------------------------------------------------------------ pricing
def price_curve(d: dict, sku: str, elasticity: float, prices: np.ndarray) -> pd.DataFrame:
    u = d["unit_econ"].loc[sku]
    var = u.fruit_cost_thb + u.packaging_thb + u.labor_thb + u.waste_cost_per_sold_cup
    q = u.base_units_per_day * (prices / u.price_thb) ** elasticity
    m = prices * (1 - u.commission_rate) - var
    gp = q * m * 30.4
    base = u.base_units_per_day * (u.price_thb * (1 - u.commission_rate) - var) * 30.4
    return pd.DataFrame({"price": prices, "units_per_day": q, "margin_per_cup": m, "gp_per_month": gp, "delta_gp": gp - base})


def elasticity_for(d: dict, sku: str, case: str) -> float:
    return {"mid": d["params"]["elasticity_sku"][sku], "low": -0.8, "high": -2.4}[case]


# ------------------------------------------------------------------------------------------ scenarios
def run_scenario(frame: pd.DataFrame, p: dict, prices: dict, keep_codes: list[str], drop_mb: bool,
                 waste_cap: dict, el_case: str, double_days: list[str], drop_kitchens=()) -> pd.DataFrame:
    """Same engine as 03_analysis.py: de-promoted base demand → price effect (elasticity) → promo lift
    → revenue, commission, fruit, packaging, labor, waste → gross profit."""
    x = frame.copy()
    if drop_mb:
        x = x[x.sku != "MixedBerryPremium"]
    if drop_kitchens:
        x = x[~x.kitchen.isin(drop_kitchens)]
    x = x.copy()
    x["list_price"] = x.sku.map(prices)
    dd = pd.to_datetime(pd.Series(double_days))
    code = np.where(x.date.isin(dd), "RC102", np.where(x.ly_code.isin(["RC101", "RC103"]), x.ly_code, "RC000"))
    code = np.where(pd.Series(code, index=x.index).isin(keep_codes + ["RC000"]), code, "RC000")
    x["code"] = code
    x["disc"] = x.code.map(p["discount"]).fillna(0)
    x["lift"] = x.code.map(p["lift"]).fillna(0)
    e = x.sku.map(p["elasticity_sku"]) if el_case == "mid" else (-0.8 if el_case == "low" else -2.4)
    x["units"] = x.base_units * (x.list_price / x.sku.map(p["price"])) ** e * (1 + x.lift)
    x["price"] = x.list_price * (1 - x.disc)
    x["revenue"] = x.units * x.price
    x["commission"] = x.revenue * x.commission_rate
    x["fruit"] = x.units * x.fruit_cost
    x["packaging"] = x.units * x.sku.map(p["packaging"])
    x["labor"] = x.units * x.sku.map(p["labor"])
    wr = x.waste_ratio_now.copy()
    for s, cap in waste_cap.items():
        wr = wr.where(x.sku != s, np.minimum(wr, cap))
    x["waste_ratio"] = wr
    x["waste_units"] = x.units * x.waste_ratio
    x["waste"] = x.waste_units * (x.fruit_cost + x.sku.map(p["packaging"]))
    x["prep_units"] = x.units + x.waste_units
    x["fruit_purchase"] = x.prep_units * x.fruit_cost
    x["gp"] = x.revenue - x.commission - x.fruit - x.packaging - x.labor - x.waste
    return x


def scenario_monthly(x: pd.DataFrame, p: dict, drop_kitchens=()) -> pd.DataFrame:
    a = x.groupby("month")[["units", "revenue", "commission", "fruit", "packaging", "labor", "waste", "gp",
                            "prep_units", "waste_units", "fruit_purchase"]].sum()
    a["overhead"] = sum(v for k, v in p["overhead"].items() if k not in drop_kitchens)
    a["operating_profit"] = a.gp - a.overhead
    return a


STATUS_QUO = dict(keep_codes=["RC101", "RC102", "RC103"], drop_mb=False, waste_cap={}, el_case="mid", drop_kitchens=())


def status_quo_prices(p):
    return dict(p["price"])


def newsvendor(d: dict, prices: dict) -> pd.DataFrame:
    """Critical ratio = margin lost on a missed sale ÷ (that + cost of a wasted cup)."""
    from statistics import NormalDist
    u = d["unit_econ"]
    rows = []
    for s in SKUS:
        cu = prices[s] * (1 - u.commission_rate[s]) - (u.fruit_cost_thb[s] + u.packaging_thb[s] + u.labor_thb[s])
        co = u.fruit_cost_thb[s] + u.packaging_thb[s]
        cr = min(max(cu / (cu + co), 0.02), 0.98) if cu > 0 else 0.02
        z = NormalDist().inv_cdf(cr)
        sd = d["backtest"].daily_error_sd[s]
        rows.append(dict(sku=s, lost_margin_per_missed_sale=cu, cost_per_wasted_cup=co, critical_ratio=cr,
                         prep_vs_forecast=z * sd))
    return pd.DataFrame(rows).set_index("sku")


# ------------------------------------------------------------------------------------------ formatting
def thb(v: float, dec: int = 2) -> str:
    if pd.isna(v):
        return "–"
    a = abs(v)
    sign = "−" if v < 0 else ""
    if a >= 1e6:
        return f"{sign}{a/1e6:,.{dec}f}M"
    if a >= 1e3:
        return f"{sign}{a/1e3:,.0f}k"
    return f"{sign}{a:,.0f}"


def signed(v: float, dec: int = 2) -> str:
    return ("+" if v >= 0 else "") + thb(v, dec) if v >= 0 else thb(v, dec)
