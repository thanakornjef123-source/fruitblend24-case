"""Writes clean/tables.pkl (from 01_clean_data.py) into a formatted Excel workbook."""
from pathlib import Path
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

OUT = Path(__file__).parent
t = pd.read_pickle(OUT / "clean" / "tables.pkl")

order = ["README", "dq_log", "reconciliation", "name_mapping", "orders_clean", "excluded_rows",
         "fruit_cost_weekly", "waste_clean", "cost_sku", "kitchen_overhead", "rate_code_dim",
         "platform_commission", "monthly_budget"]
F = "Arial"
HDR = PatternFill("solid", fgColor="1F4E78")
OKF = PatternFill("solid", fgColor="E2EFDA")
FIX = PatternFill("solid", fgColor="FFF2CC")
thin = Side(style="thin", color="BFBFBF")

wb = Workbook()
wb.remove(wb.active)

readme = [
    ["FruitBlend24 — Clean dataset (Step 1: data quality)"],
    [""],
    ["Built by 01_clean_data.py from the raw FruitBlend24_Intern_Case_Data.xlsx. Every change is listed in dq_log."],
    [""],
    ["Sheet", "What it holds"],
    ["dq_log", "Every check run on every sheet, what was found, what was done and why (green = passed, yellow = fixed)"],
    ["reconciliation", "Raw → clean row / revenue / unit bridge for orders_hourly"],
    ["name_mapping", "Each raw item_name_raw value and the SKU it was mapped to"],
    ["orders_clean", "123,655 hourly rows, 5 SKUs, rate code decoded into platform / promo / discount, commission added"],
    ["excluded_rows", "Rows removed from orders (duplicates and non-menu items) with the reason"],
    ["fruit_cost_weekly", "Weekly fruit cost per cup; 1 imputed row flagged"],
    ["waste_clean", "Complete daily waste grid (kitchen × SKU × day); imputed rows flagged"],
    ["cost_sku / kitchen_overhead", "The two tables that were stacked in raw cost_assumptions, now split"],
    ["rate_code_dim / platform_commission / monthly_budget", "Reference tables, unchanged"],
    [""],
    ["New columns in orders_clean", ""],
    ["sku", "One of Watermelon, Pineapple, Guava, PassionFruit, MixedBerryPremium"],
    ["platform_code / platform_name", "LM = LINE MAN, GB = Grab (first segment of rate_code)"],
    ["base_code / promo_name / discount_pct", "RC000 Standard, RC101 Bundle Deal 15%, RC102 Double Day 20%, RC103 Seasonal Push 12%"],
    ["base_price_thb", "Menu price before discount (cost_sku)"],
    ["commission_rate / net_revenue_after_commission_thb", "LINE MAN 30%, Grab 24% of gross revenue"],
    ["is_demand_spike", "1 = units_sold above Q3 + 3×IQR for that SKU×kitchen; kept in data (genuine peaks)"],
    ["month / week_start", "Keys for joining to monthly_budget and fruit_cost_weekly"],
]
ws = wb.create_sheet("README")
for r in readme:
    ws.append(r)
ws["A1"].font = Font(name=F, bold=True, size=14)
for row in ws.iter_rows():
    for c in row:
        if c.row != 1:
            c.font = Font(name=F, bold=c.row in (5, 16))
ws.column_dimensions["A"].width = 48
ws.column_dimensions["B"].width = 110

fmt = {"thb": '#,##0.00;(#,##0.00);"-"', "pct": "0.0%", "int": "#,##0", "date": "yyyy-mm-dd"}


def colfmt(name, s):
    if pd.api.types.is_datetime64_any_dtype(s):
        return fmt["date"]
    if "rate" in name or "pct" in name or name == "wow_change":
        return fmt["pct"]
    if "thb" in name:
        return fmt["thb"]
    if pd.api.types.is_integer_dtype(s):
        return "0" if name in ("hour", "day_of_week", "is_demand_spike", "is_imputed", "#") else fmt["int"]
    return None


for name in order[1:]:
    df = t[name].copy()
    ws = wb.create_sheet(name)
    ws.append(list(df.columns))
    for row in df.itertuples(index=False):
        ws.append([None if (isinstance(v, float) and pd.isna(v)) else (v.to_pydatetime() if isinstance(v, pd.Timestamp) else v) for v in row])
    n = len(df)
    for j, col in enumerate(df.columns, 1):
        h = ws.cell(1, j)
        h.font = Font(name=F, bold=True, color="FFFFFF")
        h.fill = HDR
        h.alignment = Alignment(wrap_text=True, vertical="center")
        f = colfmt(col, df[col])
        width = max(len(str(col)), int(df[col].astype(str).str.len().quantile(.95)) if n else 0) + 2
        ws.column_dimensions[get_column_letter(j)].width = min(width, 70)
        if n <= 20000:
            for i in range(2, n + 2):
                c = ws.cell(i, j)
                c.font = Font(name=F)
                if f:
                    c.number_format = f
        elif f:  # large sheets: number format only (font via column style keeps file small)
            for i in range(2, n + 2):
                ws.cell(i, j).number_format = f
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions

# dq_log styling
ws = wb["dq_log"]
for col, wdt in zip("ABCDEFG", [5, 18, 32, 70, 10, 55, 60]):
    ws.column_dimensions[col].width = wdt
for i in range(2, ws.max_row + 1):
    passed = str(ws.cell(i, 4).value).startswith("OK")
    for j in range(1, 8):
        c = ws.cell(i, j)
        c.alignment = Alignment(wrap_text=True, vertical="top")
        c.border = Border(bottom=thin)
        c.fill = OKF if passed else FIX

# reconciliation: total row as formulas
ws = wb["reconciliation"]
for j, L in [(2, "B"), (3, "C"), (4, "D")]:
    ws.cell(5, j).value = f"=SUM({L}2:{L}4)"
    ws.cell(5, j).font = Font(name=F, bold=True)
    ws.cell(5, j).number_format = fmt["thb"] if j == 3 else fmt["int"]
ws.cell(5, 1).value = "Clean rows (total)"  # a leading "=" would be read as a formula
ws.cell(5, 1).font = Font(name=F, bold=True)
ws.column_dimensions["A"].width = 22
for L in "BCD":
    ws.column_dimensions[L].width = 18
ws["F1"] = "Check: clean rows in orders_clean"
ws["F1"].font = Font(name=F, bold=True)
ws["G1"] = "=COUNTA(orders_clean!A:A)-1"
ws["F2"] = "Check: clean revenue in orders_clean"
ws["F2"].font = Font(name=F, bold=True)
ws["G2"] = "=SUM(orders_clean!R:R)"
ws["G2"].number_format = fmt["thb"]
ws["F3"] = "Difference vs bridge (should be 0)"
ws["G3"] = "=ROUND(G2-C5,2)"
ws.column_dimensions["F"].width = 36
ws.column_dimensions["G"].width = 18

wb.save(OUT / "FruitBlend24_clean.xlsx")
print("saved")
