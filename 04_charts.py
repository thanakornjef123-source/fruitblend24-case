"""Charts for the deck (PNG, 2x). Run after 03_analysis.py."""
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
import matplotlib.ticker as mt

OUT = Path(__file__).parent
CH = OUT / "charts"
CH.mkdir(exist_ok=True)
R = pd.read_pickle(OUT / "results.pkl")

for f in fm.findSystemFonts():
    if "Inter" in f:
        fm.fontManager.addfont(f)
BG = "#F7F5EF"
INK = "#1D2B2A"
INK2 = "#55605E"
GRID = "#DEDAD0"
BLUE = "#2a78d6"     # gains / actual / plan
ORANGE = "#eb6834"   # losses / problem
GRAY = "#A9A59B"
VIOLET = "#6250d6"
plt.rcParams.update({
    "font.family": "Inter", "font.size": 17, "axes.edgecolor": GRID, "axes.labelcolor": INK2,
    "xtick.color": INK2, "ytick.color": INK2, "text.color": INK, "axes.facecolor": BG, "figure.facecolor": BG,
    "axes.spines.top": False, "axes.spines.right": False, "axes.spines.left": False,
    "axes.grid": True, "axes.grid.axis": "y", "grid.color": GRID, "grid.linewidth": 1,
    "xtick.major.size": 0, "ytick.major.size": 0, "legend.frameon": False,
})
kfmt = mt.FuncFormatter(lambda v, p: f"{v/1000:,.0f}k" if abs(v) < 1e6 else f"{v/1e6:,.1f}M")
mlab = lambda idx: [d.strftime("%b\n%y") if d.month in (1, 9) else d.strftime("%b") for d in idx]


def save(fig, name):
    fig.savefig(CH / f"{name}.png", dpi=200, bbox_inches="tight", pad_inches=0.15)
    plt.close(fig)


# 1. Monthly GP vs budget (bars) — one axis, THB
pm = R["pnl_month"]
fig, ax = plt.subplots(figsize=(10.0, 5.6))
x = np.arange(len(pm))
cols = [BLUE if v >= 700000 else ORANGE for v in pm.gross_profit_thb]
ax.bar(x, pm.gross_profit_thb, color=cols, width=0.68, zorder=3)
ax.axhline(700000, color=INK, lw=2, ls=(0, (5, 4)), zorder=4)
ax.text(-0.45, 1040000, "- - -  Budget GP 700k / month (flat)", ha="left", va="center", fontsize=16, color=INK)
for i, v in enumerate(pm.gross_profit_thb):
    ax.text(i, v + 15000, f"{v/1000:,.0f}", ha="center", va="bottom", fontsize=14, color=INK2)
ax.set_xticks(x, mlab(pm.index))
ax.yaxis.set_major_formatter(kfmt)
ax.set_ylim(0, 1100000)
ax.set_ylabel("Gross profit (THB)")
save(fig, "c1_gp_vs_budget")

# 2. GP per cup by SKU per month (highlight PF + MB)
sm = R["pnl_sku_month"].gp_per_cup_thb.unstack()
fig, ax = plt.subplots(figsize=(10.0, 5.6))
for s, c, lw in [("Watermelon", GRAY, 2), ("Pineapple", GRAY, 2), ("Guava", GRAY, 2), ("PassionFruit", ORANGE, 3), ("MixedBerryPremium", VIOLET, 3)]:
    y = sm[s]
    ax.plot(range(len(y)), y.values, color=c, lw=lw, marker="o", ms=6 if c != GRAY else 0, zorder=3)
ax.axhline(0, color=INK, lw=1.2)
ax.text(11.2, sm["PassionFruit"].iloc[-1], "Passion Fruit  2.9", va="center", fontsize=15, color=ORANGE, fontweight="bold")
ax.text(11.2, sm["MixedBerryPremium"].iloc[-1], "Mixed Berry  −17.1", va="center", fontsize=15, color=VIOLET, fontweight="bold")
ax.text(11.2, sm[["Watermelon", "Pineapple", "Guava"]].iloc[-1].mean() + 0.6, "Watermelon, Pineapple,\nGuava  12–13", va="center", fontsize=15, color=INK2)
ax.set_xticks(range(len(sm)), mlab(sm.index))
ax.set_xlim(-0.4, 14.6)
ax.set_ylabel("Gross profit per cup (THB)")
save(fig, "c2_gp_per_cup")

# 3. Fruit cost per cup weekly — PF & MB
fc = R  # placeholder to keep names short
t = pd.read_pickle(OUT / "clean" / "tables.pkl")
fcw = t["fruit_cost_weekly"].pivot_table(index="week_start", columns="sku", values="fruit_cost_per_cup_thb")
fig, ax = plt.subplots(figsize=(7.6, 5.0))
ax.plot(fcw.index, fcw["MixedBerryPremium"], color=VIOLET, lw=2.5)
ax.plot(fcw.index, fcw["PassionFruit"], color=ORANGE, lw=2.5)
ax.plot(fcw.index, fcw[["Watermelon", "Pineapple", "Guava"]].mean(axis=1), color=GRAY, lw=2)
ax.text(fcw.index[-1], fcw["MixedBerryPremium"].dropna().iloc[-1] + 1.5, "Mixed Berry", ha="right", fontsize=15, color=VIOLET, fontweight="bold")
ax.text(fcw.index[-1], fcw["PassionFruit"].iloc[-1] + 1.5, "Passion Fruit", ha="right", fontsize=15, color=ORANGE, fontweight="bold")
ax.text(fcw.index[0], 12.5, "Other 3 (avg)", fontsize=15, color=INK2)
ax.set_ylabel("Fruit cost per cup (THB)")
ax.set_ylim(0, 60)
ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%b"))
save(fig, "c3_fruit_cost")

# 4. Kitchen operating profit by month (lines) + annual
pkm = R["pnl_kitchen_month"].operating_profit_thb.unstack(0)
fig, ax = plt.subplots(figsize=(10.0, 5.6))
style = {"Pattaya_Central": (BLUE, "-"), "Pattaya_Beach": (BLUE, (0, (4, 3))), "BKK_Sukhumvit": (ORANGE, (0, (4, 3))), "BKK_Ladprao": (ORANGE, "-")}
for k, (c, ls) in style.items():
    ax.plot(range(12), pkm[k].values, color=c, ls=ls, lw=2.8, zorder=3, label=k.replace("_", " "))
ax.legend(loc="upper left", fontsize=15)
ax.axhline(0, color=INK, lw=1.2)
ax.set_xticks(range(12), mlab(pkm.index))
ax.yaxis.set_major_formatter(kfmt)
ax.set_xlim(-0.4, 11.4)
ax.set_ylabel("Operating profit after overhead (THB)")
save(fig, "c4_kitchen_op")

# 5. Promo: lift achieved vs break-even lift
pc = R["promo_code"]
fig, ax = plt.subplots(figsize=(8.4, 5.2))
labs = [f"{n}\n({c}, −{d:.0%})" for c, n, d in zip(pc.index, pc.promo_name, pc.discount_pct)]
y = np.arange(len(pc))
ax.barh(y + 0.19, pc.breakeven_lift, height=0.36, color=GRAY, zorder=3, label="Lift needed to break even")
ax.barh(y - 0.19, pc.lift, height=0.36, color=ORANGE, zorder=3, label="Lift achieved")
for i, (a, b) in enumerate(zip(pc.lift, pc.breakeven_lift)):
    ax.text(a + 0.02, i - 0.19, f"{a:+.0%}", va="center", fontsize=15, color=INK)
    ax.text(b + 0.02, i + 0.19, f"{b:+.0%}", va="center", fontsize=15, color=INK2)
ax.set_yticks(y, labs, fontsize=15)
ax.invert_yaxis()
ax.grid(axis="y", visible=False)
ax.grid(axis="x", visible=True)
ax.xaxis.set_major_formatter(mt.PercentFormatter(1.0, decimals=0))
ax.set_xlim(0, 1.45)
ax.legend(loc="lower right", fontsize=15, bbox_to_anchor=(1.0, -0.02))
save(fig, "c5_promo_lift")

# 6. Hourly demand profile
dh = R["demand_hour"]
fig, ax = plt.subplots(figsize=(10.0, 4.6))
ax.plot(dh.index, dh["Pattaya"], color=BLUE, lw=2.8, label="Pattaya kitchens")
ax.plot(dh.index, dh["BKK"], color=ORANGE, lw=2.8, ls=(0, (4, 3)), label="Bangkok kitchens")
ax.axvspan(10.5, 13.5, color="#E9E4D8", zorder=0)
ax.axvspan(20.5, 23.5, color="#E9E4D8", zorder=0)
ax.text(12, 0.097, "Lunch peak", ha="center", fontsize=15, color=INK2)
ax.text(22, 0.097, "Late-night peak", ha="center", fontsize=15, color=INK2)
ax.yaxis.set_major_formatter(mt.PercentFormatter(1.0, decimals=0))
ax.set_ylim(0, 0.105)
ax.set_xticks(range(0, 24, 3), [f"{h:02d}:00" for h in range(0, 24, 3)])
ax.set_ylabel("Share of daily cups")
ax.legend(loc="upper left", fontsize=15)
save(fig, "c6_hourly")

# 7. Monthly cups by SKU (stacked) — seasonality
dm = R["demand_month_sku"].fillna(0)
fig, ax = plt.subplots(figsize=(7.6, 4.6))
order = ["Watermelon", "Pineapple", "Guava", "PassionFruit", "MixedBerryPremium"]
colors = ["#2a78d6", "#7FAEE6", "#B9D1EF", ORANGE, VIOLET]
bottom = np.zeros(12)
for s, c in zip(order, colors):
    ax.bar(range(12), dm[s].values, bottom=bottom, color=c, width=0.7, zorder=3, edgecolor=BG, linewidth=1.5, label=s.replace("MixedBerryPremium", "Mixed Berry").replace("PassionFruit", "Passion Fruit"))
    bottom += dm[s].values
ax.set_xticks(range(12), [d.strftime("%b")[0] for d in dm.index])
ax.yaxis.set_major_formatter(kfmt)
ax.set_ylabel("Cups sold per month")
ax.legend(fontsize=13, ncol=2, loc="upper left")
ax.set_ylim(0, 100000)
save(fig, "c7_monthly_mix")

# 8. Outlook Sep–Nov GP: status quo vs plan vs budget
ol = R["outlook"]
fig, ax = plt.subplots(figsize=(8.4, 5.2))
x = np.arange(3)
sq, pl, lo, hi = ol["Status quo"].gp, ol["Recommended plan"].gp, ol["Plan (low elasticity)"].gp, ol["Plan (high elasticity)"].gp
ax.bar(x - 0.2, sq, width=0.38, color=GRAY, zorder=3, label="Status quo")
ax.bar(x + 0.2, pl, width=0.38, color=BLUE, zorder=3, label="Recommended plan")
ax.errorbar(x + 0.2, pl, yerr=[pl - hi, lo - pl], fmt="none", ecolor=INK, capsize=6, lw=1.5, zorder=4)
ax.axhline(700000, color=INK, lw=2, ls=(0, (5, 4)))
ax.text(2.6, 712000, "Budget 700k", ha="right", fontsize=15)
for i in range(3):
    ax.text(i - 0.2, sq.iloc[i] + 12000, f"{sq.iloc[i]/1000:,.0f}k", ha="center", fontsize=14, color=INK2)
    ax.text(i + 0.2, lo.iloc[i] + 12000, f"{pl.iloc[i]/1000:,.0f}k", ha="center", fontsize=14, color=INK, fontweight="bold")
ax.set_xticks(x, ["Sep 2026", "Oct 2026", "Nov 2026"])
ax.yaxis.set_major_formatter(kfmt)
ax.set_ylim(0, 800000)
ax.set_ylabel("Gross profit (THB)")
ax.legend(loc="upper left", fontsize=15, ncol=2)
save(fig, "c8_outlook")

# 9. Bridge (waterfall) status quo -> plan, Sep–Nov GP
br = R["bridge"]
fig, ax = plt.subplots(figsize=(8.4, 5.2))
vals = list(br.gp_sep_nov)
labels = ["Status\nquo", "Delist\nMixed Berry", "Stop RC101\n& RC103", "Reprice\nPF/WM/PA", "PF waste\nto 6%", "Plan"]
base = vals[0]
ax.bar(0, base, color=GRAY, width=0.6, zorder=3)
run = base
for i, dlt in enumerate(br.delta.iloc[1:], start=1):
    ax.bar(i, dlt, bottom=run, color=BLUE, width=0.6, zorder=3)
    ax.text(i, run + dlt + 15000, f"+{dlt/1000:,.0f}k", ha="center", fontsize=15, color=INK)
    run += dlt
ax.bar(5, run, color=BLUE, width=0.6, zorder=3)
ax.text(0, base + 15000, f"{base/1e6:,.2f}M", ha="center", fontsize=15, color=INK)
ax.text(5, run + 15000, f"{run/1e6:,.2f}M", ha="center", fontsize=15, color=INK, fontweight="bold")
ax.set_xticks(range(6), labels, fontsize=14)
ax.yaxis.set_major_formatter(kfmt)
ax.set_ylim(1_000_000, 1_750_000)
ax.set_ylabel("Gross profit Sep–Nov 2026 (THB)")
save(fig, "c9_bridge")

# 10. Price test: ΔGP/month at +10% across elasticity cases
ps = R["price_sim"]
p10 = ps[np.isclose(ps.price_change, 0.10)].pivot_table(index="sku", columns="elasticity_case", values="delta_gp_per_month")
p10 = p10.reindex(["PassionFruit", "MixedBerryPremium", "Pineapple", "Watermelon", "Guava"])
fig, ax = plt.subplots(figsize=(8.4, 5.0))
y = np.arange(len(p10))
lo_c, mid_c, hi_c = "Low (−0.8, from RC103)", "Mid (SKU-specific, from RC101)", "High (−2.4, from RC102)"
for i, s in enumerate(p10.index):
    a, b = p10.loc[s, [lo_c, hi_c]].min(), p10.loc[s, [lo_c, hi_c]].max()
    ax.plot([a, b], [i, i], color=GRAY, lw=6, solid_capstyle="round", zorder=2)
    m = p10.loc[s, mid_c]
    ax.plot(m, i, "o", color=BLUE if m > 0 else ORANGE, ms=13, zorder=3, markeredgecolor=BG, markeredgewidth=2)
    ax.text(b + 1500, i, f"{m/1000:+.1f}k", va="center", fontsize=15, color=INK)
ax.axvline(0, color=INK, lw=1.2)
ax.set_yticks(y, ["Passion Fruit", "Mixed Berry", "Pineapple", "Watermelon", "Guava"])
ax.invert_yaxis()
ax.grid(axis="y", visible=False)
ax.grid(axis="x", visible=True)
ax.xaxis.set_major_formatter(kfmt)
ax.set_xlabel("Change in gross profit per month from a +10% price (THB)")
ax.set_xlim(-12000, 40000)
save(fig, "c10_price_test")
print(sorted(p.name for p in CH.glob("*.png")))
