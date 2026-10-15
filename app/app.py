"""FruitBlend24 — Revenue & inventory review (Streamlit).

Run locally:  streamlit run app.py
Data: data/*.csv, exported from the cleaned workbook by 06_export_app_data.py.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import model as M

st.set_page_config(page_title="FruitBlend24 review", layout="wide")

INK, INK2, GRID = "#15322A", "#5A6B64", "#D9E1D8"
GAIN, LOSS, NEUTRAL = "#1F6FB2", "#D9542B", "#A8B3AC"
SKU_COLOR = {"Watermelon": "#1F6FB2", "Pineapple": "#1BA37A", "Guava": "#E0A100",
             "PassionFruit": "#D9542B", "MixedBerryPremium": "#6A55D6"}
KIT_COLOR = {"Pattaya_Central": "#1F6FB2", "Pattaya_Beach": "#1BA37A", "BKK_Sukhumvit": "#E0A100", "BKK_Ladprao": "#D9542B"}
FONT = "Figtree, Helvetica, Arial, sans-serif"


@st.cache_data(show_spinner="Loading data…")
def data():
    return M.load_all()


D = data()
P = D["params"]


# ------------------------------------------------------------------------------------------ helpers
def style(fig, h=380, legend=True):
    fig.update_layout(height=h, margin=dict(l=8, r=8, t=40 if legend else 16, b=8),
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      font=dict(family=FONT, color=INK, size=14), hoverlabel=dict(font_family=FONT),
                      legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, title=None), showlegend=legend,
                      hovermode="x unified")
    fig.update_xaxes(showgrid=False, linecolor=GRID, ticks="")
    fig.update_yaxes(gridcolor=GRID, zerolinecolor=INK2, zerolinewidth=1, ticks="")
    return fig


def show(fig):
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})


def lede(text):
    st.markdown(f"<p style='font-size:1.15rem;color:{INK2};max-width:62rem;margin-top:-0.4rem'>{text}</p>",
                unsafe_allow_html=True)


NICE = {"units_sold": "Cups sold", "gross_revenue_thb": "Revenue", "discount_thb": "Discounts", "commission_thb": "Commission",
        "fruit_thb": "Fruit", "packaging_thb": "Packaging", "labor_thb": "Labor", "waste_thb": "Waste cost",
        "gross_profit_thb": "Gross profit", "gp_margin": "GP margin", "gp_per_cup": "GP per cup", "waste_rate": "Waste rate",
        "overhead_thb": "Overhead", "operating_profit_thb": "Operating profit", "budget_gp_thb": "Budget GP",
        "gp_vs_budget": "GP vs budget", "price_thb": "Price", "commission_rate": "Commission rate",
        "fruit_cost_thb": "Fruit / cup", "margin_per_cup_thb": "Margin / cup", "breakeven_price_thb": "Break-even price",
        "base_units_per_day": "Cups / day", "elasticity_rc101": "Elasticity", "lost_margin_per_missed_sale": "Lost margin / missed sale",
        "cost_per_wasted_cup": "Cost / wasted cup", "critical_ratio": "Critical ratio", "prep_vs_forecast": "Prep vs forecast",
        "weekly_wape": "Weekly error (WAPE)", "weekly_bias": "Weekly bias", "daily_wape": "Daily error (WAPE)",
        "daily_error_sd": "Daily error SD", "promo_days": "Promo days", "units": "Cups", "baseline_units": "Baseline cups",
        "lift": "Lift", "breakeven_lift": "Break-even lift", "elasticity": "Elasticity", "incremental_units": "Extra cups",
        "incremental_revenue": "Extra revenue", "profit_impact": "Profit impact", "profit_per_day": "Profit / promo day",
        "rows": "Rows", "step": "Step", "item_name_raw": "Raw name", "sku": "Product", "code": "Promotion", "kitchen": "Kitchen", "date": "Date",
        "rev": "Revenue", "baseline_rev": "Baseline revenue", "cm": "Margin", "baseline_cm": "Baseline margin",
        "item": "Item", "assumption": "Assumption", "basis / note": "Basis / note"}


def table(df, fmt=None, height=None, index=True):
    df = df.copy()
    fmt = {NICE.get(k, k): v for k, v in (fmt or {}).items()}
    df.columns = [NICE.get(c, c) for c in df.columns]
    if df.index.names and any(df.index.names):
        df.index.names = [NICE.get(n, n) for n in df.index.names]
    h = height or (min(len(df), 18) * 35 + 38)
    st.dataframe(df.style.format(fmt, na_rep="–"), width="stretch", height=h, hide_index=not index)


THB0 = lambda v: "–" if pd.isna(v) else f"{v:,.0f}"
THB1 = lambda v: "–" if pd.isna(v) else f"{v:,.1f}"
PCT1 = lambda v: "–" if pd.isna(v) else f"{v:.1%}"
PCT0 = lambda v: "–" if pd.isna(v) else f"{v:+.0%}"
lab = lambda s: M.SKU_LABEL.get(s, M.KITCHEN_LABEL.get(s, s))


# ------------------------------------------------------------------------------------------ pages
def page_overview():
    pm = M.pnl(D, ["month"])
    rev, gp = pm.gross_revenue_thb.sum(), pm.gross_profit_thb.sum()
    ovh = M.overhead(D) * 12
    op_m = pm.gross_profit_thb - M.overhead(D)
    brev, bgp = D["budget"].budget_revenue_thb.sum(), D["budget"].budget_gross_profit_thb.sum()

    st.title("FruitBlend24 lost 0.40M last year. Five changes would have made it profitable.")
    lede("12 months of delivery orders (Sep 2025 – Aug 2026) from 4 kitchens and 5 smoothies, rebuilt into a P&amp;L "
         "and compared with the budget. All figures in THB.")

    c = st.columns(4)
    c[0].metric("Revenue", M.thb(rev), f"{rev/brev-1:+.1%} vs budget", border=True)
    c[1].metric("Gross profit", M.thb(gp), f"{gp/bgp-1:+.1%} vs budget", border=True)
    c[2].metric("Operating profit", M.thb(gp - ovh), f"after {M.thb(ovh)} kitchen overhead", delta_color="off", delta_arrow="off", border=True)
    c[3].metric("Loss-making months", f"{(op_m < 0).sum()} of 12", "profit only Jan and Mar–May", delta_color="off", delta_arrow="off", border=True)

    left, right = st.columns([1.35, 1], gap="large")
    with left:
        st.subheader("Gross profit beat the flat budget only in the hot season")
        b = D["budget"].set_index("month").budget_gross_profit_thb
        fig = go.Figure()
        fig.add_bar(x=pm.index, y=pm.gross_profit_thb, name="Gross profit",
                    marker_color=[GAIN if v >= b.iloc[0] else LOSS for v in pm.gross_profit_thb],
                    hovertemplate="%{y:,.0f}<extra>Gross profit</extra>")
        fig.add_scatter(x=b.index, y=b.values, name="Budget", mode="lines", line=dict(color=INK, dash="dash", width=2),
                        hovertemplate="%{y:,.0f}<extra>Budget</extra>")
        fig.update_xaxes(dtick="M1", tickformat="%b<br>%y")
        show(style(fig, 360))
        st.caption("Blue = at or above the 700k monthly budget, orange = below.")
    with right:
        st.subheader("What the data says")
        findings = [
            ("Profit is seasonal; the flat budget hides it", "Hot season GP +29% vs budget, rainy season −33% (−0.99M operating)."),
            ("Two products lost their margin", "Passion Fruit fruit cost +51% from June; Mixed Berry loses 17 THB a cup with 21% waste."),
            ("Both Bangkok kitchens lose money", "Ladprao −0.62M and in the red every month; Sukhumvit −0.49M."),
            ("No promotion pays for its discount", "Three codes, 57 promo days, −155k of profit."),
            ("LINE MAN cups earn less", "12.4 THB margin per cup vs 15.4 on Grab; LINE MAN is 56% of cups."),
        ]
        for h, t in findings:
            st.markdown(f"**{h}.** {t}")

    st.subheader("Recommended actions")
    rec = pd.DataFrame([
        ["Pricing", "Passion Fruit 65 → 75, Watermelon 45 → 47, Pineapple 49 → 51; hold Guava", "+131k GP"],
        ["Portfolio", "Delist Mixed Berry; relaunch only with fruit ≤35 THB/cup and waste <8%", "+69k GP"],
        ["Promotions", "Stop Seasonal Push and Bundle Deal; keep Double Day as a tagged test on Grab", "+29k GP"],
        ["Inventory", "Prep to forecast in daypart batches, no pre-made buffer; Passion Fruit waste 10% → 6%", "+19k GP"],
        ["Kitchens", "Give BKK Ladprao 90 days to cut overhead to ≤88k/month, or close", "+187k operating profit if closed"],
    ], columns=["Area", "Action", "Impact Sep–Nov 2026"])
    table(rec, index=False)
    st.page_link(PAGES["outlook"], label="Try the levers in the scenario builder")


def page_dq():
    st.title("The raw export needed five fixes before any number could be trusted")
    lede("Every check that ran, what it found and what was done. The log below lists the checks that found something; "
         "switch on the toggle to also see the ones that passed with zero violations.")
    r = D["recon"]
    c = st.columns(3)
    c[0].metric("Rows kept", f"{int(r.rows.iloc[-1]):,}", f"{int(r.rows.iloc[1] + r.rows.iloc[2]):,} removed", delta_color="off", delta_arrow="off", border=True)
    c[1].metric("Clean revenue", M.thb(r.gross_revenue_thb.iloc[-1]), f"{M.thb(r.gross_revenue_thb.iloc[-1] - r.gross_revenue_thb.iloc[0])} vs raw", delta_color="off", delta_arrow="off", border=True)
    passed = D["dq_log"].finding.str.startswith("OK")
    c[2].metric("Checks run", f"{len(D['dq_log'])}", f"{passed.sum()} passed with 0 violations", delta_color="off", delta_arrow="off", border=True)

    st.subheader("Raw → clean bridge")
    table(r.set_index("step"), {"rows": THB0, "gross_revenue_thb": THB0, "units": THB0})

    st.subheader("Data-quality log")
    show_all = st.toggle("Show passed checks too", value=False)
    log = D["dq_log"] if show_all else D["dq_log"][~passed]
    log = log.drop(columns="#").rename(columns={"sheet": "Sheet", "check": "Check", "finding": "Finding", "rows_affected": "Rows",
                                                "action": "Action", "rationale": "Why"})
    st.table(log.set_index("Sheet"))
    with st.expander("How 31 raw item names map to 5 products"):
        table(D["names"].sort_values(["sku", "rows"], ascending=[True, False]), {"rows": THB0}, index=False)


def page_pnl():
    st.title("P&L vs budget")
    lede("Built from orders × weekly fruit cost × platform commission × packaging and labor per cup, plus daily waste. "
         "Gross profit is before kitchen overhead, matching the budget’s ~26% margin.")
    c = st.columns([1.2, 1.2, 1, 1])
    kit = c[0].multiselect("Kitchens", M.KITCHENS, format_func=lab, placeholder="All kitchens")
    sku = c[1].multiselect("Products", M.SKUS, format_func=lab, placeholder="All products")
    plat = c[2].multiselect("Platform", ["LINE MAN", "Grab"], placeholder="Both platforms")
    view = c[3].segmented_control("Rows", ["Month", "Kitchen", "Product"], default="Month")
    by = {"Month": "month", "Kitchen": "kitchen", "Product": "sku", None: "month"}[view]
    a = M.pnl(D, [by], kit or None, sku or None, plat or None)
    full = not (kit or sku or plat)

    out = a[["units_sold", "gross_revenue_thb", "commission_thb", "fruit_thb", "packaging_thb", "labor_thb", "waste_thb",
             "gross_profit_thb", "gp_margin", "gp_per_cup", "waste_rate"]].copy()
    if by == "kitchen":
        out["overhead_thb"] = [P["overhead"][k] * 12 for k in out.index]
        out["operating_profit_thb"] = out.gross_profit_thb - out.overhead_thb
    if by == "month" and not (sku or plat):
        out["overhead_thb"] = M.overhead(D, kit or None)
        out["operating_profit_thb"] = out.gross_profit_thb - out.overhead_thb
    if by == "month" and full:
        b = D["budget"].set_index("month")
        out["budget_gp_thb"] = b.budget_gross_profit_thb
        out["gp_vs_budget"] = out.gross_profit_thb / out.budget_gp_thb - 1
    out.index = [i.strftime("%b %Y") if isinstance(i, pd.Timestamp) else lab(i) for i in out.index]
    tot = out.sum(numeric_only=True)
    for col, num, den in [("gp_margin", "gross_profit_thb", "gross_revenue_thb"), ("gp_per_cup", "gross_profit_thb", "units_sold")]:
        tot[col] = tot[num] / tot[den]
    tot["waste_rate"] = a.waste_units.sum() / (a.waste_units.sum() + a.units_sold.sum())
    if "gp_vs_budget" in out:
        tot["gp_vs_budget"] = tot.gross_profit_thb / tot.budget_gp_thb - 1
    out.loc["Total"] = tot

    k = st.columns(4)
    k[0].metric("Revenue", M.thb(tot.gross_revenue_thb), border=True)
    k[1].metric("Gross profit", M.thb(tot.gross_profit_thb), f"{tot.gp_margin:.1%} margin", delta_color="off", delta_arrow="off", border=True)
    k[2].metric("GP per cup", f"{tot.gp_per_cup:,.1f} THB", border=True)
    if "operating_profit_thb" in out:
        k[3].metric("Operating profit", M.thb(tot.operating_profit_thb), border=True)
    else:
        k[3].metric("Waste rate", f"{tot.waste_rate:.1%}", "of cups made", delta_color="off", delta_arrow="off", border=True)
    if not full:
        st.caption("Budget is set company-wide, so the budget comparison shows only with no filters. "
                   "With a platform filter, waste (recorded per kitchen × product) is split by that platform’s share of cups.")

    fmt = {c: THB0 for c in out.columns}
    fmt.update({"gp_margin": PCT1, "waste_rate": PCT1, "gp_per_cup": THB1, "gp_vs_budget": PCT0})
    table(out, fmt)
    st.download_button("Download this P&L (CSV)", out.to_csv().encode(), "fruitblend24_pnl.csv", "text/csv")

    t1, t2, t3, t4 = st.tabs(["Kitchen operating profit", "GP per cup by product", "Fruit cost per cup", "Cost structure"])
    with t1:
        km = M.pnl(D, ["kitchen", "month"]).gross_profit_thb.unstack(0)
        fig = go.Figure()
        for kk in M.KITCHENS:
            fig.add_scatter(x=km.index, y=km[kk] - P["overhead"][kk], name=lab(kk), mode="lines+markers",
                            line=dict(color=KIT_COLOR[kk], width=2.5, dash="solid" if "Central" in kk or "Ladprao" in kk else "dash"),
                            hovertemplate="%{y:,.0f}")
        fig.update_xaxes(dtick="M1", tickformat="%b<br>%y")
        show(style(fig, 380))
        st.caption("Operating profit = gross profit − fixed monthly overhead (Pattaya Central 180k, Pattaya Beach 150k, Sukhumvit 200k, Ladprao 140k).")
    with t2:
        sm = M.pnl(D, ["month", "sku"]).gp_per_cup.unstack()
        fig = go.Figure()
        for s in M.SKUS:
            fig.add_scatter(x=sm.index, y=sm[s], name=lab(s), mode="lines+markers", line=dict(color=SKU_COLOR[s], width=2.5),
                            hovertemplate="%{y:.1f} THB")
        fig.add_hline(y=0, line_color=INK2, line_width=1)
        fig.update_xaxes(dtick="M1", tickformat="%b<br>%y")
        show(style(fig, 380))
    with t3:
        fw = D["fruit"].pivot_table(index="week_start", columns="sku", values="fruit_cost_per_cup_thb")
        fig = go.Figure()
        for s in M.SKUS:
            fig.add_scatter(x=fw.index, y=fw[s], name=lab(s), mode="lines", line=dict(color=SKU_COLOR[s], width=2.2),
                            hovertemplate="%{y:.2f} THB")
        show(style(fig, 380))
        st.caption("Passion Fruit stepped from ~18 to ~28 THB per cup in the week of 1 Jun 2026 and stayed there; Mixed Berry rose from 34 to 51.")
    with t4:
        parts = {"Commission": a.commission_thb.sum(), "Fruit": a.fruit_thb.sum(), "Packaging": a.packaging_thb.sum(),
                 "Labor": a.labor_thb.sum(), "Waste": a.waste_thb.sum(), "Gross profit": a.gross_profit_thb.sum()}
        rv = a.gross_revenue_thb.sum()
        fig = go.Figure(go.Bar(x=[v / rv for v in parts.values()], y=list(parts.keys()), orientation="h",
                               marker_color=[NEUTRAL] * 5 + [GAIN], text=[f"{v/rv:.1%}  ·  {M.thb(v)}" for v in parts.values()],
                               textposition="outside", hovertemplate="%{x:.1%}<extra></extra>"))
        fig.update_xaxes(tickformat=".0%", range=[0, 0.4])
        fig.update_yaxes(autorange="reversed", showgrid=False)
        show(style(fig, 320, legend=False))
        st.caption("Share of gross revenue. Platform commission is the largest cost line.")


def page_demand():
    st.title("Demand peaks at lunch and late night; prices have room on three of five products")
    t1, t2, t3 = st.tabs(["Demand shape", "Price simulator", "Platforms"])
    hr = D["hourly"]
    with t1:
        c = st.columns([1, 1])
        with c[0]:
            st.subheader("Two daily peaks")
            hh = hr.assign(region=hr.kitchen.str.split("_").str[0]).pivot_table(index="hour", columns="region", values="units_sold", aggfunc="sum")
            hh = hh / hh.sum()
            fig = go.Figure()
            for r, col, dash in [("Pattaya", GAIN, "solid"), ("BKK", LOSS, "dash")]:
                fig.add_scatter(x=hh.index, y=hh[r], name="Bangkok" if r == "BKK" else r, line=dict(color=col, width=2.5, dash=dash),
                                hovertemplate="%{y:.1%}")
            for x0, x1 in [(10.5, 13.5), (20.5, 23.5)]:
                fig.add_vrect(x0=x0, x1=x1, fillcolor="#E6EDE5", line_width=0, layer="below")
            fig.update_yaxes(tickformat=".0%")
            fig.update_xaxes(dtick=3, title="Hour of day")
            show(style(fig, 340))
            pk = hr[hr.hour.isin([11, 12, 13, 21, 22, 23])].units_sold.sum() / hr.units_sold.sum()
            st.caption(f"{pk:.0%} of cups sell in six hours: 11–14h and 21–24h. Pattaya leans later (tourism, nightlife).")
        with c[1]:
            st.subheader("Weekends sell more")
            days = D["sales"].assign(dow=D["sales"].date.dt.dayofweek)
            dd = days.groupby("dow").units_sold.sum() / days.groupby("dow").date.nunique()
            fig = go.Figure(go.Bar(x=["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"], y=dd.values,
                                   marker_color=[NEUTRAL] * 5 + [GAIN] * 2, hovertemplate="%{y:,.0f} cups/day<extra></extra>"))
            show(style(fig, 340, legend=False))
            st.caption(f"Weekend average {dd.iloc[5:].mean():,.0f} cups/day vs {dd.iloc[:5].mean():,.0f} on weekdays ({dd.iloc[5:].mean()/dd.iloc[:5].mean()-1:+.0%}).")
        st.subheader("The hot season sells 1.3–1.5× an average month")
        ms = M.pnl(D, ["month", "sku"]).units_sold.unstack()
        fig = go.Figure()
        for s in M.SKUS:
            fig.add_bar(x=ms.index, y=ms[s], name=lab(s), marker_color=SKU_COLOR[s], hovertemplate="%{y:,.0f}")
        fig.update_layout(barmode="stack", bargap=0.25)
        fig.update_xaxes(dtick="M1", tickformat="%b<br>%y")
        show(style(fig, 360))

    with t2:
        lede("Elasticity comes from promo days: how much volume rose for a known discount. Bundle Deal gives a figure per "
             "product; Seasonal Push (−0.8) and Double Day (−2.4) bound it. Margin uses Jun–Aug 2026 costs, commission and waste.")
        c = st.columns([1, 1.4, 1.6])
        s = c[0].selectbox("Product", M.SKUS, index=3, format_func=lab)
        case = c[1].segmented_control("Elasticity", list(M.ELASTICITY_CASES), default=list(M.ELASTICITY_CASES)[0])
        e = M.elasticity_for(D, s, M.ELASTICITY_CASES[case or list(M.ELASTICITY_CASES)[0]])
        u = D["unit_econ"].loc[s]
        newp = c[2].slider("New price (THB)", int(u.price_thb * 0.8), int(u.price_thb * 1.35), int(P["plan_price"][s]), 1)
        cur = M.price_curve(D, s, e, np.array([u.price_thb, newp]))
        k = st.columns(4)
        k[0].metric("Elasticity used", f"{e:.2f}", border=True)
        k[1].metric("Margin per cup", f"{cur.margin_per_cup[1]:.1f} THB", f"{cur.margin_per_cup[1]-cur.margin_per_cup[0]:+.1f} vs {u.price_thb:.0f} THB", border=True)
        k[2].metric("Cups per day", f"{cur.units_per_day[1]:,.0f}", f"{cur.units_per_day[1]/cur.units_per_day[0]-1:+.0%}", border=True)
        k[3].metric("Gross profit per month", M.thb(cur.gp_per_month[1]), f"{cur.delta_gp[1]:+,.0f} THB", border=True)
        grid = np.arange(int(u.price_thb * 0.8), int(u.price_thb * 1.35) + 1)
        fig = go.Figure()
        for name, cs in M.ELASTICITY_CASES.items():
            cv = M.price_curve(D, s, M.elasticity_for(D, s, cs), grid)
            fig.add_scatter(x=cv.price, y=cv.gp_per_month, name=name.split(" (")[0] + f" ({M.elasticity_for(D, s, cs):.2f})",
                            line=dict(color={"mid": GAIN, "low": "#7FA9D3", "high": INK2}[cs], width=3 if cs == "mid" else 2,
                                      dash="solid" if cs == "mid" else "dot"), hovertemplate="%{y:,.0f}")
        fig.add_vline(x=u.price_thb, line_color=INK2, line_dash="dash", annotation_text="Today", annotation_position="top left")
        fig.add_vline(x=newp, line_color=GAIN, annotation_text="New", annotation_position="top right")
        fig.update_xaxes(title="Price (THB)")
        fig.update_yaxes(title="Gross profit per month (THB)")
        show(style(fig, 380))
        st.caption(f"Break-even price at today’s cost: {u.breakeven_price_thb:.0f} THB. Promo response tends to overstate reaction to a "
                   "permanent price change, so test on one platform for 4 weeks before rolling out.")
        st.subheader("Unit economics today")
        ue = D["unit_econ"][["price_thb", "commission_rate", "fruit_cost_thb", "packaging_thb", "labor_thb", "waste_rate",
                             "margin_per_cup_thb", "breakeven_price_thb", "base_units_per_day", "elasticity_rc101"]].copy()
        ue.index = [lab(i) for i in ue.index]
        table(ue, {"price_thb": THB0, "commission_rate": PCT1, "fruit_cost_thb": THB1, "packaging_thb": THB1, "labor_thb": THB1,
                   "waste_rate": PCT1, "margin_per_cup_thb": THB1, "breakeven_price_thb": THB1, "base_units_per_day": THB0,
                   "elasticity_rc101": "{:.2f}"})

    with t3:
        sp = D["sales"].groupby("platform_name")[["units_sold", "gross_revenue_thb", "commission_thb", "fruit_thb", "packaging_thb", "labor_thb"]].sum()
        sp["margin_per_cup"] = (sp.gross_revenue_thb - sp.commission_thb - sp.fruit_thb - sp.packaging_thb - sp.labor_thb) / sp.units_sold
        sp["share_of_cups"] = sp.units_sold / sp.units_sold.sum()
        sp["commission_rate"] = sp.commission_thb / sp.gross_revenue_thb
        c = st.columns(2)
        c[0].metric("LINE MAN margin per cup", f"{sp.margin_per_cup['LINE MAN']:.1f} THB", f"{sp.share_of_cups['LINE MAN']:.0%} of cups · 30% commission", delta_color="off", delta_arrow="off", border=True)
        c[1].metric("Grab margin per cup", f"{sp.margin_per_cup['Grab']:.1f} THB", f"{sp.share_of_cups['Grab']:.0%} of cups · 24% commission", delta_color="off", delta_arrow="off", border=True)
        lede(f"Every point of LINE MAN commission is worth about {M.thb(sp.gross_revenue_thb['LINE MAN'] * 0.01)} a year. "
             "LINE MAN is the natural place to test a price rise; Grab is the cheaper channel for acquisition promotions.")
        pm = D["sales"].pivot_table(index="month", columns="platform_name", values="units_sold", aggfunc="sum")
        fig = go.Figure()
        fig.add_scatter(x=pm.index, y=pm["LINE MAN"] / pm.sum(axis=1), name="LINE MAN share of cups", line=dict(color=LOSS, width=2.5),
                        hovertemplate="%{y:.1%}")
        fig.update_yaxes(tickformat=".0%", range=[0.4, 0.7])
        show(style(fig, 300))


def page_promos():
    st.title("None of the three promotions pays for its discount")
    lede("Each promo day is compared with the same kitchen and product on non-promo days within ±28 days "
         "(same weekday or weekend type). Profit = margin after commission and costs, valued at full price for the baseline.")
    c = st.columns(2)
    kit = c[0].multiselect("Kitchens", M.KITCHENS, format_func=lab, placeholder="All kitchens", key="pk")
    sku = c[1].multiselect("Products", M.SKUS, format_func=lab, placeholder="All products", key="ps")
    a = M.promo_summary(D, ["code"], kit or None, sku or None)
    k = st.columns(3)
    for i, code in enumerate(["RC101", "RC102", "RC103"]):
        if code in a.index:
            r = a.loc[code]
            k[i].metric(f"{M.CODES[code]} · −{r.discount:.0%}", M.thb(r.profit_impact), f"lift {r.lift:+.0%} vs {r.breakeven_lift:+.0%} needed",
                        delta_color="red" if r.lift < r.breakeven_lift else "green", delta_arrow="off", border=True)
    left, right = st.columns([1.2, 1], gap="large")
    with left:
        names = [f"{M.CODES[c]} (−{a.discount[c]:.0%})" for c in a.index]
        fig = go.Figure()
        fig.add_bar(y=names, x=a.lift, orientation="h", name="Lift achieved", marker_color=LOSS,
                    text=[f"{v:+.0%}" for v in a.lift], textposition="outside", hovertemplate="%{x:.0%}")
        fig.add_bar(y=names, x=a.breakeven_lift, orientation="h", name="Lift needed to break even", marker_color=NEUTRAL,
                    text=[f"{v:+.0%}" for v in a.breakeven_lift], textposition="outside", hovertemplate="%{x:.0%}")
        fig.update_layout(barmode="group", hovermode="y unified")
        fig.update_xaxes(tickformat=".0%", gridcolor=GRID, showgrid=True, range=[0, max(a.breakeven_lift.max(), a.lift.max()) * 1.2])
        fig.update_yaxes(autorange="reversed", showgrid=False)
        show(style(fig, 360))
    with right:
        st.markdown(f"**Seasonal Push** cut revenue: 12% off bought only {a.lift.get('RC103', np.nan):.0%} more cups.")
        st.markdown(f"**Bundle Deal** doesn’t pull sales from other products on the same day ({P['rc101_other_sku_change']:+.1%}), "
                    "but its lift is about half of what the discount needs.")
        st.markdown(f"**Double Day** is meant to win new users. It pays back only if the extra cups bring "
                    f"{P['rc102_repeat_cups_needed']:,.0f} future full-price cups ({P['rc102_repeat_per_incr_cup']:.2f} per extra cup). "
                    "The data has no customer IDs, so run it on Grab, tag first-time users and decide after two double days.")
    st.subheader("By promotion")
    show_cols = ["promo_days", "units", "baseline_units", "lift", "breakeven_lift", "elasticity", "incremental_units",
                 "incremental_revenue", "profit_impact", "profit_per_day"]
    t = a[show_cols].copy()
    t.index = [M.CODES[c] for c in t.index]
    fmt = {c: THB0 for c in show_cols}
    fmt.update({"lift": PCT0, "breakeven_lift": PCT0, "elasticity": "{:.2f}"})
    table(t, fmt)
    st.subheader("By promotion and product")
    b = M.promo_summary(D, ["code", "sku"], kit or None, sku or None)[show_cols].reset_index()
    b["code"] = b.code.map(M.CODES)
    b["sku"] = b.sku.map(lab)
    table(b.set_index(["code", "sku"]), fmt)
    with st.expander("Promo calendar (every promo day × kitchen × product)"):
        pdx = D["promo_days"].copy()
        pdx["code"] = pdx.code.map(M.CODES)
        table(pdx, {"units": THB0, "baseline_units": THB1, "cm": THB0, "baseline_cm": THB0, "rev": THB0, "baseline_rev": THB0}, index=False)


# ------------------------------------------------------------------------------------------ scenario builder
def preset(name):
    plan = name == "plan"
    for s in M.SKUS:
        st.session_state[f"price_{s}"] = int(P["plan_price"][s] if plan else P["price"][s])
    st.session_state["keep_RC101"] = not plan
    st.session_state["keep_RC102"] = True
    st.session_state["keep_RC103"] = not plan
    st.session_state["drop_mb"] = plan
    st.session_state["drop_lad"] = False
    st.session_state["pf_cap"] = 6 if plan else 10
    st.session_state["el_case"] = list(M.ELASTICITY_CASES)[0]


def page_outlook():
    if "price_Watermelon" not in st.session_state:
        preset("plan")
    st.title("Plan Sep–Nov 2026: profit and stock under your choices")
    lede("Set prices, promotions, products and waste targets. The forecast, P&amp;L and fruit order update instantly. "
         "The same levers are replayed over the last 12 months to show their full-year effect.")
    b1, b2, _ = st.columns([1, 1, 4])
    b1.button("Recommended plan", on_click=preset, args=("plan",), type="primary", width="stretch")
    b2.button("Status quo", on_click=preset, args=("sq",), width="stretch")

    with st.container(border=True):
        st.markdown("**Prices (THB per cup)**")
        pc = st.columns(5)
        prices = {s: pc[i].number_input(lab(s), 20, 150, step=1, key=f"price_{s}") for i, s in enumerate(M.SKUS)}
        c = st.columns(3, gap="large")
        with c[0]:
            st.markdown("**Promotions to keep**")
            keep = [code for code in ["RC101", "RC102", "RC103"] if st.checkbox(M.CODES[code], key=f"keep_{code}")]
        with c[1]:
            st.markdown("**Portfolio**")
            drop_mb = st.checkbox("Delist Mixed Berry", key="drop_mb")
            drop_lad = st.checkbox("Close BKK Ladprao", key="drop_lad")
        with c[2]:
            st.markdown("**Waste and demand**")
            pf_cap = st.slider("Passion Fruit waste cap (% of cups sold)", 3, 12, key="pf_cap")
            el_name = st.selectbox("Price elasticity", list(M.ELASTICITY_CASES), key="el_case")
    el = M.ELASTICITY_CASES[el_name]
    drop_k = ("BKK_Ladprao",) if drop_lad else ()
    cap = {"PassionFruit": pf_cap / 100}

    f, h = D["forecast_frame"], D["history_frame"]
    sq = M.run_scenario(f, P, P["price"], ["RC101", "RC102", "RC103"], False, {}, "mid", P["double_days_outlook"])
    sc = M.run_scenario(f, P, prices, keep, drop_mb, cap, el, P["double_days_outlook"], drop_k)
    sqm, scm = M.scenario_monthly(sq, P), M.scenario_monthly(sc, P, drop_k)
    hsq = M.run_scenario(h, P, P["price"], ["RC101", "RC102", "RC103"], False, {}, "mid", P["double_days_history"])
    hsc = M.run_scenario(h, P, prices, keep, drop_mb, cap, el, P["double_days_history"], drop_k)
    actual_gp = M.pnl(D, ["month"]).gross_profit_thb.sum()
    actual_op = actual_gp - M.overhead(D) * 12
    replay_op = actual_gp + (hsc.gp.sum() - hsq.gp.sum()) - sum(v for k, v in P["overhead"].items() if k not in drop_k) * 12

    st.markdown(
        f"<div style='display:flex;gap:2.5rem;align-items:baseline;flex-wrap:wrap;margin:0.6rem 0 0.2rem'>"
        f"<div><div style='color:{INK2}'>Last 12 months, actual operating profit</div>"
        f"<div style='font-family:&quot;Bricolage Grotesque&quot;, sans-serif;font-size:2.6rem;font-weight:700;color:{LOSS}'>{M.thb(actual_op)}</div></div>"
        f"<div style='font-size:2rem;color:{INK2}'>→</div>"
        f"<div><div style='color:{INK2}'>Same 12 months replayed with these choices</div>"
        f"<div style='font-family:&quot;Bricolage Grotesque&quot;, sans-serif;font-size:2.6rem;font-weight:700;color:{GAIN if replay_op >= 0 else LOSS}'>"
        f"{('+' if replay_op >= 0 else '') + M.thb(replay_op)}</div></div></div>", unsafe_allow_html=True)

    k = st.columns(5)
    k[0].metric("Sep–Nov gross profit", M.thb(scm.gp.sum()), f"{M.signed(scm.gp.sum()-sqm.gp.sum())} vs status quo", border=True)
    k[1].metric("Sep–Nov operating profit", M.thb(scm.operating_profit.sum()), f"{M.signed(scm.operating_profit.sum()-sqm.operating_profit.sum())} vs status quo", border=True)
    k[2].metric("Sep–Nov revenue", M.thb(scm.revenue.sum()), f"{scm.revenue.sum()/sqm.revenue.sum()-1:+.1%}", border=True)
    k[3].metric("Cups to prepare", f"{scm.prep_units.sum():,.0f}", f"{scm.prep_units.sum()/sqm.prep_units.sum()-1:+.1%}", delta_color="off", delta_arrow="off", border=True)
    k[4].metric("Wasted cups", f"{scm.waste_units.sum():,.0f}", f"{scm.waste_units.sum()/sqm.waste_units.sum()-1:+.0%}", delta_color="inverse", border=True)

    t1, t2, t3, t4 = st.tabs(["P&L by month", "What moved profit", "Inventory needs", "Ordering rules"])
    with t1:
        fig = go.Figure()
        mlab = [d.strftime("%b %Y") for d in scm.index]
        fig.add_bar(x=mlab, y=sqm.gp, name="Status quo", marker_color=NEUTRAL, hovertemplate="%{y:,.0f}")
        fig.add_bar(x=mlab, y=scm.gp, name="Your plan", marker_color=GAIN, hovertemplate="%{y:,.0f}")
        fig.add_scatter(x=mlab, y=[700000] * 3, name="Budget", mode="lines", line=dict(color=INK, dash="dash"), hovertemplate="%{y:,.0f}")
        fig.update_layout(barmode="group")
        fig.update_yaxes(title="Gross profit (THB)")
        show(style(fig, 360))
        tb = pd.DataFrame({"Status quo GP": sqm.gp, "Plan revenue": scm.revenue, "Plan commission": scm.commission, "Plan fruit": scm.fruit,
                           "Plan packaging + labor": scm.packaging + scm.labor, "Plan waste": scm.waste, "Plan GP": scm.gp,
                           "Overhead": scm.overhead, "Plan operating profit": scm.operating_profit, "Budget GP": 700000})
        tb.index = mlab
        tb.loc["Total"] = tb.sum()
        table(tb, {c: THB0 for c in tb.columns})
        st.caption("Sep–Nov is low season: last year these months made 1.65M GP. Budget for the quarter is 2.10M GP.")
    with t2:
        steps = [("Status quo", P["price"], ["RC101", "RC102", "RC103"], False, {}, "mid", ())]
        steps.append(("Delist Mixed Berry" if drop_mb else "Mixed Berry kept", P["price"], ["RC101", "RC102", "RC103"], drop_mb, {}, "mid", ()))
        steps.append(("Promotions", P["price"], keep, drop_mb, {}, "mid", ()))
        steps.append(("Prices", prices, keep, drop_mb, {}, el, ()))
        steps.append(("Waste cap", prices, keep, drop_mb, cap, el, ()))
        vals = []
        for name, pr_, kp, dm, wc, ec, dk in steps:
            x = M.run_scenario(f, P, pr_, kp, dm, wc, ec, P["double_days_outlook"], dk)
            vals.append((name, x.gp.sum()))
        ops = [v - M.overhead(D) * 3 for _, v in vals]
        final_op = scm.operating_profit.sum()
        names = [n for n, _ in vals] + (["Close Ladprao"] if drop_lad else []) + ["Your plan"]
        deltas = [ops[0]] + list(np.diff(ops)) + ([final_op - ops[-1]] if drop_lad else []) + [final_op]
        measure = ["absolute"] + ["relative"] * (len(names) - 2) + ["total"]
        fig = go.Figure(go.Waterfall(x=names, y=deltas, measure=measure, connector=dict(line=dict(color=GRID)),
                                     increasing=dict(marker=dict(color=GAIN)), decreasing=dict(marker=dict(color=LOSS)),
                                     totals=dict(marker=dict(color=INK2)), text=[f"{v:+,.0f}" if m == "relative" else f"{v:,.0f}" for v, m in zip(deltas, measure)],
                                     textposition="outside", hovertemplate="%{y:,.0f}<extra></extra>"))
        fig.update_yaxes(title="Sep–Nov operating profit (THB)")
        show(style(fig, 400, legend=False))
        st.caption("Each bar adds one choice on top of the previous ones, so the order matters a little. "
                   "Closing Ladprao removes its gross profit and its 420k quarterly overhead.")
    with t3:
        sc["week"] = sc.date - pd.to_timedelta(sc.date.dt.dayofweek, unit="D")
        im = sc.groupby(["month", "sku"]).agg(cups_sold=("units", "sum"), cups_to_prep=("prep_units", "sum"),
                                             wasted=("waste_units", "sum"), fruit_purchase_thb=("fruit_purchase", "sum")).reset_index()
        piv = im.pivot_table(index="sku", columns="month", values=["cups_to_prep", "fruit_purchase_thb"], aggfunc="sum")
        piv.columns = [f"{'Cups to prep' if a == 'cups_to_prep' else 'Fruit THB'} · {m:%b}" for a, m in piv.columns]
        piv = piv[[c for m in ["Sep", "Oct", "Nov"] for c in piv.columns if c.endswith(m)]]
        piv = piv.loc[[x for x in M.SKUS if x in piv.index]]
        piv.index = [lab(i) for i in piv.index]
        piv.loc["Total"] = piv.sum()
        st.subheader(f"{scm.prep_units.sum():,.0f} cups to prepare and {M.thb(scm.fruit_purchase.sum())} of fruit over the quarter")
        table(piv, {c: THB0 for c in piv.columns})
        kk = sc.groupby("kitchen")[["units", "prep_units", "waste_units", "fruit_purchase"]].sum()
        kk.index = [lab(i) for i in kk.index]
        kk.columns = ["Cups sold", "Cups to prep", "Wasted", "Fruit THB"]
        table(kk, {c: THB0 for c in kk.columns})
        st.markdown("**Weekly order sheet**")
        wk = st.selectbox("Kitchen", sorted(sc.kitchen.unique()), format_func=lab)
        ws = sc[sc.kitchen == wk].groupby(["week", "sku"]).agg(cups=("prep_units", "sum"), fruit=("fruit_purchase", "sum")).reset_index()
        wsp = ws.pivot_table(index="week", columns="sku", values="cups").round(0)
        wsp = wsp[[x for x in M.SKUS if x in wsp.columns]]
        wsp.columns = [lab(c) for c in wsp.columns]
        wsp.index = [f"w/c {d:%d %b}" for d in wsp.index]
        table(wsp, {c: THB0 for c in wsp.columns})
        st.download_button("Download daily plan (CSV)", sc[["date", "kitchen", "sku", "code", "list_price", "units", "prep_units", "waste_units", "fruit_purchase", "revenue", "gp"]]
                           .round(2).to_csv(index=False).encode(), "fruitblend24_daily_plan.csv", "text/csv")
    with t4:
        st.subheader("Order to a forecast, prep to the daypart, no pre-made buffer")
        st.markdown(
            "1. **Forecast weekly**: same weekday last year, promo days removed, rescaled to the last 4 weeks’ run-rate.\n"
            "2. **Order fruit twice a week** (Mon, Thu): forecast cups × (1 + waste target) × fruit cost per cup.\n"
            "3. **Prep in three batches** sized to each window’s share (below); top up from fruit stock.\n"
            "4. **Track waste daily** against target: core products ≤5%, Passion Fruit ≤6%.")
        c = st.columns(2)
        with c[0]:
            nv = M.newsvendor(D, prices).loc[[s for s in M.SKUS if not (drop_mb and s == "MixedBerryPremium")]]
            nv.index = [lab(i) for i in nv.index]
            st.markdown("**How much to prep vs forecast (newsvendor)**")
            table(nv, {"lost_margin_per_missed_sale": THB1, "cost_per_wasted_cup": THB1, "critical_ratio": "{:.2f}", "prep_vs_forecast": "{:+.1%}"})
            st.caption("Critical ratio = margin lost on a missed sale ÷ (that + cost of a wasted cup). Near 0.5 or below means "
                       "prepare at or under the forecast; extra buffer only adds waste.")
        with c[1]:
            win = {"Lunch batch (ready 10:30, covers 11–15h)": range(11, 15), "Afternoon batch (15–21h)": range(15, 21),
                   "Late-night batch (ready 20:30, covers 21–03h)": [21, 22, 23, 0, 1, 2], "Top-up only (03–11h)": range(3, 11)}
            hk = D["hourly"].groupby(["kitchen", "hour"]).units_sold.sum().unstack(0)
            sh = pd.DataFrame({w: hk.loc[list(hrs)].sum() / hk.sum() for w, hrs in win.items()}).T
            sh.columns = [lab(c) for c in sh.columns]
            st.markdown("**Batch sizes: share of each kitchen’s daily cups**")
            table(sh, {c: PCT1 for c in sh.columns})
            bt = D["backtest"].copy()
            bt.index = [lab(i) for i in bt.index]
            st.markdown("**Forecast accuracy, Jun–Aug 2026 backtest**")
            table(bt, {c: PCT1 for c in bt.columns})
            st.caption("A plain 4-week average ran ~9.5% high as demand fell after the hot season: that is why the forecast uses last year’s same week.")


def page_method():
    st.title("How the numbers were built")
    f, h = D["forecast_frame"], D["history_frame"]
    hsq = M.run_scenario(h, P, P["price"], ["RC101", "RC102", "RC103"], False, {}, "mid", P["double_days_history"])
    actual = M.pnl(D, ["month"]).gross_profit_thb.sum()
    c = st.columns(3)
    c[0].metric("Model check: last 12 months GP", M.thb(hsq.gp.sum()), f"actual {M.thb(actual)} ({hsq.gp.sum()/actual-1:+.2%})", delta_color="off", delta_arrow="off", border=True)
    g = P["growth_check"]
    c[1].metric("Trend check: core cups per day", f"{g['aug26_per_day']:,.0f}", f"Aug 2026 vs {g['sep25_per_day']:,.0f} in Sep 2025", delta_color="off", delta_arrow="off", border=True)
    c[2].metric("Mixed Berry monthly decay", f"{P['mb_monthly_decay']-1:+.0%}", "Jun–Aug 2026 trend", delta_color="off", delta_arrow="off", border=True)
    st.subheader("Approach")
    st.markdown(
        "- **Data quality**: 26 checks; names mapped to 5 products; duplicates and non-menu rows removed; gaps imputed and flagged.\n"
        "- **P&L**: orders × weekly fruit cost × platform commission × packaging and labor, plus daily waste; overhead below gross profit.\n"
        "- **Promotions**: matched baseline (same kitchen × product, non-promo days ±28 days, same weekday/weekend type).\n"
        "- **Pricing**: constant-elasticity demand, elasticities implied by promo lifts, bounded −0.8 to −2.4.\n"
        "- **Forecast**: seasonal naive on de-promoted demand (same weekday last year), growth 1.00; scenarios apply price, promo and waste choices.\n"
        "- **Inventory**: newsvendor critical ratio for prep vs forecast; batch sizes from the hourly demand profile.")
    st.subheader("Assumptions")
    table(D["assumptions"], index=False)
    st.subheader("With more time")
    st.markdown(
        "- Customer-level data to measure whether Double Day new users come back.\n"
        "- Prep and stock-out logs: sales may be capped by availability.\n"
        "- Weather data to explain rainy-season demand.\n"
        "- Delivery zones: could Sukhumvit serve Ladprao’s customers?\n"
        "- Platform A/B price tests; overnight staffing cost (2% of cups sell 2–6am).")
    st.caption("Built with Python (pandas, numpy, plotly, Streamlit). Source scripts: 01_clean_data.py → 06_export_app_data.py.")


PAGES = {
    "overview": st.Page(page_overview, title="Overview", default=True),
    "dq": st.Page(page_dq, title="Data quality", url_path="data-quality"),
    "pnl": st.Page(page_pnl, title="P&L vs budget", url_path="pnl"),
    "demand": st.Page(page_demand, title="Demand & pricing", url_path="demand-pricing"),
    "promos": st.Page(page_promos, title="Promotions", url_path="promotions"),
    "outlook": st.Page(page_outlook, title="Plan & inventory (Sep–Nov)", url_path="plan"),
    "method": st.Page(page_method, title="Method & assumptions", url_path="method"),
}
with st.sidebar:
    st.markdown("### FruitBlend24")
    st.caption("Revenue & inventory review · Sep 2025 – Aug 2026 · synthetic case data")
nav = st.navigation(list(PAGES.values()))
nav.run()
