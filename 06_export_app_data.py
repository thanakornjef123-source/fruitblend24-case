"""Exports portable CSV/JSON data for the Streamlit app (app/data/). Run after 03_analysis.py."""
import json
from pathlib import Path
import pandas as pd

OUT = Path(__file__).parent
D = OUT / "app" / "data"
D.mkdir(parents=True, exist_ok=True)
R = pd.read_pickle(OUT / "results.pkl")
t = pd.read_pickle(OUT / "clean" / "tables.pkl")
o, fc, w = t["orders_clean"], t["fruit_cost_weekly"], t["waste_clean"]
cs = t["cost_sku"].set_index("sku")

# daily P&L fact: date × kitchen × SKU × platform
o = o.merge(fc[["week_start", "sku", "fruit_cost_per_cup_thb"]], on=["week_start", "sku"], how="left")
o["discount_thb"] = (o.base_price_thb - o.price_thb) * o.units_sold
o["commission_thb"] = o.gross_revenue_thb * o.commission_rate
o["fruit_thb"] = o.units_sold * o.fruit_cost_per_cup_thb
o["packaging_thb"] = o.units_sold * o.sku.map(cs.packaging_cost_per_cup_thb)
o["labor_thb"] = o.units_sold * o.sku.map(cs.labor_cost_per_cup_thb)
daily = o.groupby(["date", "kitchen", "sku", "platform_name"], as_index=False)[
    ["units_sold", "gross_revenue_thb", "discount_thb", "commission_thb", "fruit_thb", "packaging_thb", "labor_thb"]].sum()
daily.to_csv(D / "daily_sales.csv", index=False)
w[["date", "kitchen", "sku", "units_wasted", "est_waste_cost_thb", "is_imputed"]].to_csv(D / "daily_waste.csv", index=False)
o.groupby(["hour", "day_of_week", "kitchen", "sku"], as_index=False).units_sold.sum().to_csv(D / "hourly.csv", index=False)
fc.drop(columns=["is_imputed"]).to_csv(D / "fruit_cost_weekly.csv", index=False)
t["monthly_budget"][["month", "budget_revenue_thb", "budget_gross_profit_thb"]].to_csv(D / "budget.csv", index=False)
t["dq_log"].to_csv(D / "dq_log.csv", index=False)
t["reconciliation"].to_csv(D / "reconciliation.csv", index=False)
t["name_mapping"].to_csv(D / "name_mapping.csv", index=False)
t["rate_code_dim"].to_csv(D / "rate_codes.csv", index=False)

R["promo_days"].to_csv(D / "promo_days.csv", index=False)
R["unit_econ_now"].rename_axis("sku").reset_index().to_csv(D / "unit_economics.csv", index=False)
pd.DataFrame({"weekly_wape": R["backtest_wape_weekly"], "weekly_bias": R["backtest_bias_weekly"],
              "daily_wape": R["backtest_wape_daily"], "daily_error_sd": R["daily_err_sd"]}).rename_axis("sku").reset_index().to_csv(D / "backtest.csv", index=False)
R["forecast_frame"].to_csv(D / "forecast_frame.csv", index=False)
R["history_frame"].to_csv(D / "history_frame.csv", index=False)
R["assumptions"].to_csv(D / "assumptions.csv", index=False)
p = dict(R["params"])
p["rc101_other_sku_change"] = float(R["rc101_other_sku_change"])
p["rc102_repeat_cups_needed"] = float(R["rc102_repeat_cups_needed"])
p["rc102_repeat_per_incr_cup"] = float(R["rc102_repeat_per_incr_cup"])
p["growth_check"] = {k: float(v) for k, v in R["growth_check"].items()}
(D / "params.json").write_text(json.dumps(p, indent=2))
print(sorted(x.name for x in D.iterdir()))
print(sum(x.stat().st_size for x in D.iterdir()) / 1e6, "MB")
