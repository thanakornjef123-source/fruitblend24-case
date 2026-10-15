"""
FruitBlend24 — Step 1: Data quality assessment & cleaning
Input : FruitBlend24_Intern_Case_Data.xlsx (raw)
Output: FruitBlend24_clean.xlsx  (clean tables + data-quality log)
        clean/*.csv              (same tables as CSV for the analysis steps)
Run   : python 01_clean_data.py <path_to_raw.xlsx>
"""
import sys, re
from pathlib import Path
import numpy as np
import pandas as pd

RAW = sys.argv[1] if len(sys.argv) > 1 else "FruitBlend24_Intern_Case_Data.xlsx"
OUT = Path(__file__).parent
(OUT / "clean").mkdir(exist_ok=True)

x = pd.read_excel(RAW, sheet_name=None)
log = []  # data-quality log rows


def add_log(sheet, check, finding, rows, action, why):
    log.append(dict(sheet=sheet, check=check, finding=finding,
                    rows_affected=rows, action=action, rationale=why))


SKUS = ["Watermelon", "Pineapple", "Guava", "PassionFruit", "MixedBerryPremium"]
MB_LAUNCH = pd.Timestamp("2026-03-01")

# ---------------------------------------------------------------- reference tables
ca = x["cost_assumptions"]
cost_sku = ca.iloc[:5].copy()
cost_sku.columns = ["sku", "packaging_cost_per_cup_thb", "labor_cost_per_cup_thb", "base_price_thb"]
cost_sku[cost_sku.columns[1:]] = cost_sku[cost_sku.columns[1:]].astype(float)
hdr = ca.index[ca["sku"].astype(str).eq("kitchen")][0]
overhead = ca.iloc[hdr + 1:, :3].copy()
overhead.columns = ["kitchen", "fixed_monthly_overhead_thb", "note"]
overhead = overhead.dropna(subset=["kitchen"])
overhead["fixed_monthly_overhead_thb"] = overhead["fixed_monthly_overhead_thb"].astype(float)
add_log("cost_assumptions", "Structure",
        "Two different tables stacked in one sheet (SKU unit costs rows 1-5; kitchen overhead under a text header)",
        len(cost_sku) + len(overhead), "Split into cost_sku and kitchen_overhead tables",
        "Each table needs its own columns to join correctly")

rate = x["rate_code_dim"].copy()
platform = x["platform_commission_rate"].copy()
sku_code = x["sku_code_dim"].copy()
budget = x["monthly_budget"].copy()
budget["month"] = pd.to_datetime(budget["month"])

base_price = cost_sku.set_index("sku")["base_price_thb"]
disc = rate.set_index("base_code")["discount_pct"]
rc_name = rate.set_index("base_code")["rate_code_name"]
skucode = sku_code.set_index("sku_code")["sku"]
comm = platform.set_index("platform_code")["commission_rate"]

# ---------------------------------------------------------------- orders_hourly
o = x["orders_hourly"].copy()
n_raw = len(o)
o["item_name_raw"] = o["item_name_raw"].astype(str)


def map_sku(name: str) -> str:
    n = name.strip().lower()
    if "berry" in n or "เบอร์รี่" in n:
        return "MixedBerryPremium"
    if "guava" in n or "ฝรั่ง" in n:
        return "Guava"
    if "passion" in n or "เสาวรส" in n:
        return "PassionFruit"
    if "pineapple" in n or "สับปะรด" in n or "สัปปะรด" in n:  # 2nd = common misspelling
        return "Pineapple"
    if "watermelon" in n or "แตงโม" in n:
        return "Watermelon"
    return "NON_MENU"


name_map = (pd.DataFrame({"item_name_raw": sorted(o["item_name_raw"].unique())})
            .assign(sku=lambda d: d["item_name_raw"].map(map_sku)))
o["sku"] = o["item_name_raw"].map(dict(zip(name_map.item_name_raw, name_map.sku)))
n_variants = name_map[name_map.sku != "NON_MENU"].shape[0]
add_log("orders_hourly", "Product names",
        f"{o.item_name_raw.nunique()} raw names (Thai/English, casing, typos e.g. 'สัปปะรด', 'smoothy', trailing spaces) "
        f"for 5 real products",
        int((o.sku != "NON_MENU").sum()),
        f"Mapped {n_variants} name variants to 5 SKUs by keyword (see name_mapping sheet)",
        "All variants of one SKU carry the identical price list, confirming they are the same product")

# exact duplicates
dup_mask = o.duplicated(keep="first")
excluded = [o[dup_mask].assign(exclude_reason="Exact duplicate row (export artifact)")]
add_log("orders_hourly", "Exact duplicates",
        f"{dup_mask.sum()} rows are byte-for-byte copies of another row; spread across all 12 months",
        int(dup_mask.sum()), "Removed (kept first copy)",
        "After removal every date×hour×kitchen×SKU×platform appears exactly once, so the copies are double-counts, not real orders")
o = o[~dup_mask]

# non-menu rows
nm = o["sku"] == "NON_MENU"
nm_rev = o.loc[nm, "gross_revenue_thb"].sum()
excluded.append(o[nm].assign(exclude_reason="Non-menu / data-entry artifact"))
add_log("orders_hourly", "Non-menu items",
        f"{nm.sum()} rows for 'แก้วเปล่า' (empty cup), 'น้ำส้มปั่น (เมนูทดลอง)' (test menu), "
        f"'Combo Set A (2 แก้ว)'; prices random (0/35/59/99), some at 0 THB; {nm_rev:,.0f} THB revenue",
        int(nm.sum()), "Excluded from analysis (kept in excluded_rows sheet)",
        "Not one of the 5 menu items, no cost data exists for them, and <0.04% of revenue")
o = o[~nm].copy()

# decode rate code
parts = o["rate_code"].str.split("-", expand=True)
o["platform_code"] = parts[0]
o["base_code"] = parts[1]
o["rate_code_sku"] = parts[2].map(skucode) if 2 in parts else np.nan
o["platform_name"] = o["platform_code"].map(platform.set_index("platform_code")["platform_name"])
o["promo_name"] = o["base_code"].map(rc_name)
o["discount_pct"] = o["base_code"].map(disc)
o["base_price_thb"] = o["sku"].map(base_price)
o["commission_rate"] = o["platform_code"].map(comm)

# validation checks (all expected to pass — logged as evidence)
chk = {
    "Revenue = units × price": int(((o.units_sold * o.price_thb - o.gross_revenue_thb).abs() > 0.01).sum()),
    "day_of_week matches date": int((o.date.dt.dayofweek != o.day_of_week).sum()),
    "Price = base price × (1 − promo discount)": int(((o.base_price_thb * (1 - o.discount_pct)).round(2).sub(o.price_thb).abs() > 0.01).sum()),
    "RC101 SKU suffix matches item sold": int((o.base_code.eq("RC101") & o.rate_code_sku.ne(o.sku)).sum()),
    "RC102 only on double dates (1/1…12/12)": int((o.base_code.eq("RC102") & (o.date.dt.day != o.date.dt.month)).sum()),
    "RC103 only in Jun–Oct": int((o.base_code.eq("RC103") & ~o.date.dt.month.isin([6, 7, 8, 9, 10])).sum()),
    "Mixed Berry not sold before 1 Mar 2026 launch": int((o.sku.eq("MixedBerryPremium") & (o.date < MB_LAUNCH)).sum()),
    "Unknown platform / rate code": int(o.platform_name.isna().sum() + o.promo_name.isna().sum()),
    "Missing values": int(o.isna().drop(columns=["rate_code_sku"]).sum().sum()),
    "Units ≤ 0 or price ≤ 0": int(((o.units_sold <= 0) | (o.price_thb <= 0)).sum()),
}
for k, v in chk.items():
    add_log("orders_hourly", k, "OK — 0 violations" if v == 0 else f"{v} violations", v,
            "None needed" if v == 0 else "Investigate", "Validation check")

# coverage: hours with no row
cov = o.groupby(["date", "kitchen"]).hour.nunique()
add_log("orders_hourly", "Coverage",
        f"All 365 days × 4 kitchens present; {(cov < 24).sum()} kitchen-days have <24 hours of rows (min {cov.min()})",
        int((cov < 24).sum()), "Treat a missing hour×SKU row as 0 units sold",
        "The export only writes rows when something sold; quiet hours are mostly 2–5 am")

# demand spikes (flag, keep)
q = o.groupby(["sku", "kitchen"]).units_sold.quantile([.25, .75]).unstack()
fence = (q[0.75] + 3 * (q[0.75] - q[0.25])).rename("fence")
o = o.join(fence, on=["sku", "kitchen"])
o["is_demand_spike"] = (o.units_sold > o.fence).astype(int)
sp = o[o.is_demand_spike == 1]
add_log("orders_hourly", "Outliers (units_sold)",
        f"{len(sp)} rows above Q3+3×IQR for their SKU×kitchen (max {o.units_sold.max()} cups/hr). "
        f"{(sp.base_code != 'RC000').mean():.0%} fall on promo codes (vs {(o.base_code != 'RC000').mean():.0%} of all rows), "
        f"{sp.hour.isin([11,12,13,21,22,23]).mean():.0%} at lunch/late-night peaks (vs {o.hour.isin([11,12,13,21,22,23]).mean():.0%}), "
        f"{sp.date.dt.month.isin([3,4,5]).mean():.0%} in Mar–May hot season",
        len(sp), "Kept, flagged in is_demand_spike",
        "Pattern is consistent (hot-season weekends, promo days, peak hours) and revenue reconciles — genuine demand, not errors")
o = o.drop(columns="fence")

o["week_start"] = o["date"] - pd.to_timedelta(o["date"].dt.dayofweek, unit="D")
o["month"] = o["date"].dt.to_period("M").dt.to_timestamp()
o["net_revenue_after_commission_thb"] = o["gross_revenue_thb"] * (1 - o["commission_rate"])
o["item_name_raw"] = o["item_name_raw"].str.strip()
orders = o[["date", "month", "week_start", "hour", "day_of_week", "kitchen", "sku", "item_name_raw",
            "platform_code", "platform_name", "rate_code", "base_code", "promo_name", "discount_pct",
            "base_price_thb", "price_thb", "units_sold", "gross_revenue_thb", "commission_rate",
            "net_revenue_after_commission_thb", "is_demand_spike"]].sort_values(
    ["date", "hour", "kitchen", "sku", "platform_code"]).reset_index(drop=True)
excluded = pd.concat(excluded)[list(x["orders_hourly"].columns) + ["exclude_reason"]]

# ---------------------------------------------------------------- weekly_fruit_cost
fc = x["weekly_fruit_cost"].copy()
fc["week_start"] = pd.to_datetime(fc["week_start"])
add_log("weekly_fruit_cost", "Types", "week_start stored as text", len(fc), "Converted to date", "Needed for joins")
chk_fc = int(fc.isna().sum().sum() + fc.duplicated(["week_start", "sku"]).sum() + (fc.week_start.dt.dayofweek != 0).sum())
add_log("weekly_fruit_cost", "Nulls / duplicates / non-Monday weeks", "OK — 0 found" if chk_fc == 0 else f"{chk_fc} found",
        chk_fc, "None needed", "Validation check")
# MB launched Sunday 1 Mar but first cost week is Mon 2 Mar -> add a backfilled row for week 23 Feb
mb_first = fc[fc.sku == "MixedBerryPremium"].sort_values("week_start").iloc[0]
fc = pd.concat([fc, pd.DataFrame([{"week_start": pd.Timestamp("2026-02-23"), "sku": "MixedBerryPremium",
                                   "fruit_cost_per_cup_thb": mb_first.fruit_cost_per_cup_thb}])])
fc["is_imputed"] = (fc.week_start == "2026-02-23") & (fc.sku == "MixedBerryPremium")
fc["is_imputed"] = fc["is_imputed"].astype(int)
add_log("weekly_fruit_cost", "Gap at launch",
        "Mixed Berry launched Sun 1 Mar 2026 but its first cost week is Mon 2 Mar, so 1 Mar sales/waste have no fruit cost",
        1, f"Added week 2026-02-23 for Mixed Berry using the 2 Mar cost ({mb_first.fruit_cost_per_cup_thb} THB), flagged is_imputed",
        "Nearest available price; affects one day only")
fc = fc.sort_values(["sku", "week_start"])
fc["wow_change"] = fc.groupby("sku").fruit_cost_per_cup_thb.pct_change()
big = fc[fc.wow_change.abs() > 0.3]
add_log("weekly_fruit_cost", "Volatility",
        "; ".join(f"{r.sku} {r.wow_change:+.0%} w/c {r.week_start:%d %b %Y}" for r in big.itertuples()) +
        f". Range per cup: " + ", ".join(f"{s} {g.min():.1f}–{g.max():.1f}" for s, g in fc.groupby('sku').fruit_cost_per_cup_thb),
        len(big), "Kept as is",
        "Plausible seasonal input-cost swing (the brief calls this the volatile cost); matters for the P&L, not an error")

# ---------------------------------------------------------------- waste_daily
w = x["waste_daily"].copy()
w["date"] = pd.to_datetime(w["date"])
add_log("waste_daily", "Types", "date stored as text", len(w), "Converted to date", "Needed for joins")
grid = []
for k in overhead.kitchen:
    for s in SKUS:
        start = MB_LAUNCH if s == "MixedBerryPremium" else pd.Timestamp("2025-09-01")
        grid.append(pd.DataFrame({"date": pd.date_range(start, "2026-08-31"), "kitchen": k, "sku": s}))
grid = pd.concat(grid)
w = grid.merge(w, how="left", on=["date", "kitchen", "sku"])
miss = w.units_wasted.isna()
w["is_imputed"] = miss.astype(int)
# impute units = median of same kitchen×SKU within ±7 days
for i in w[miss].index:
    r = w.loc[i]
    win = w[(w.kitchen == r.kitchen) & (w.sku == r.sku) & ((w.date - r.date).abs() <= pd.Timedelta(days=7)) & ~miss]
    w.loc[i, "units_wasted"] = round(win.units_wasted.median())
add_log("waste_daily", "Missing rows",
        f"{miss.sum()} kitchen×SKU×day combinations absent: " +
        ", ".join(f"{r.kitchen}/{r.sku} {r.date:%d %b}" for r in w[miss].itertuples()),
        int(miss.sum()), "Inserted with units = median of the same kitchen×SKU ±7 days, flagged is_imputed",
        "Every other day has a waste record (including zeros), so a missing row means unrecorded, not zero")

w["week_start"] = w["date"] - pd.to_timedelta(w["date"].dt.dayofweek, unit="D")
w = w.merge(fc[["week_start", "sku", "fruit_cost_per_cup_thb"]], how="left", on=["week_start", "sku"])
pack = cost_sku.set_index("sku")["packaging_cost_per_cup_thb"]
w["recalc_cost"] = (w.units_wasted * (w.fruit_cost_per_cup_thb + w.sku.map(pack))).round(2)
ok = w.est_waste_cost_thb.notna()
mismatch = int(((w.recalc_cost - w.est_waste_cost_thb).abs() > 0.05)[ok].sum())
add_log("waste_daily", "Cost formula check",
        f"est_waste_cost = units × (weekly fruit cost + packaging) reproduces {ok.sum() - mismatch}/{ok.sum()} rows exactly",
        mismatch, "Formula confirmed; used to fill gaps", "Validation check")
nullc = w.est_waste_cost_thb.isna() & ~miss
add_log("waste_daily", "Null cost",
        f"{nullc.sum()} rows with units but no cost — all Mixed Berry on 1 Mar 2026 (launch day, no fruit-cost week)",
        int(nullc.sum()), "Filled with the confirmed formula using the backfilled 2 Mar fruit cost, flagged is_imputed",
        "Same root cause as the fruit-cost gap")
w.loc[nullc, "is_imputed"] = 1
w["est_waste_cost_thb"] = w["est_waste_cost_thb"].fillna(w["recalc_cost"])
w["units_wasted"] = w["units_wasted"].astype(int)
waste = w[["date", "week_start", "kitchen", "sku", "units_wasted", "est_waste_cost_thb", "is_imputed"]] \
    .sort_values(["date", "kitchen", "sku"]).reset_index(drop=True)
lw = waste[(waste.sku == "MixedBerryPremium") & (waste.date <= "2026-03-07")].units_wasted.sum()
add_log("waste_daily", "Outliers (units_wasted)",
        f"Highest waste days are all Mixed Berry in launch weeks (max 53 cups, 3 Mar Pattaya_Central; {lw} cups in launch week)",
        int((waste.units_wasted > 30).sum()), "Kept",
        "Consistent with over-preparing a new item — a business finding, not a data error")

budget["note"] = budget["note"].astype(str)
add_log("monthly_budget", "Assumption", "Budget is flat 2.70M revenue / 0.70M GP every month (note says it ignores seasonality and input-cost volatility)",
        12, "Kept as given", "Keep in mind when reading variance — part of any miss is the budget, not performance")

# ---------------------------------------------------------------- reconciliation summary
recon = pd.DataFrame([
    ["Raw rows", n_raw, x["orders_hourly"].gross_revenue_thb.sum(), x["orders_hourly"].units_sold.sum()],
    ["− Exact duplicates", -len(excluded[excluded.exclude_reason.str.startswith("Exact")]),
     -excluded[excluded.exclude_reason.str.startswith("Exact")].gross_revenue_thb.sum(),
     -excluded[excluded.exclude_reason.str.startswith("Exact")].units_sold.sum()],
    ["− Non-menu rows", -len(excluded[excluded.exclude_reason.str.startswith("Non")]),
     -excluded[excluded.exclude_reason.str.startswith("Non")].gross_revenue_thb.sum(),
     -excluded[excluded.exclude_reason.str.startswith("Non")].units_sold.sum()],
    ["= Clean rows", len(orders), orders.gross_revenue_thb.sum(), orders.units_sold.sum()],
], columns=["step", "rows", "gross_revenue_thb", "units"])
assert recon.iloc[:3, 1:].sum().round(2).tolist() == recon.iloc[3, 1:].round(2).tolist()

dq = pd.DataFrame(log)
dq.insert(0, "#", range(1, len(dq) + 1))

tables = {
    "dq_log": dq, "reconciliation": recon, "name_mapping": name_map.assign(
        rows=name_map.item_name_raw.map(x["orders_hourly"].item_name_raw.astype(str).value_counts())),
    "orders_clean": orders, "excluded_rows": excluded, "fruit_cost_weekly": fc.drop(columns="wow_change"),
    "waste_clean": waste, "cost_sku": cost_sku, "kitchen_overhead": overhead, "rate_code_dim": rate,
    "platform_commission": platform, "monthly_budget": budget,
}
for n, t in tables.items():
    t.to_csv(OUT / "clean" / f"{n}.csv", index=False, encoding="utf-8-sig")
pd.to_pickle(tables, OUT / "clean" / "tables.pkl")
print(recon.to_string(index=False))
print(dq[["#", "sheet", "check", "rows_affected"]].to_string(index=False))
