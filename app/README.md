# FruitBlend24 — Streamlit app

An interactive version of the analysis: data quality, P&L vs budget, demand and pricing, promotions, and a scenario
builder for Sep–Nov 2026. In the scenario builder you set prices, promotions, products and waste targets, and the
forecast, P&L and weekly fruit order update as you change them.

## Run it on your computer

```bash
cd app
pip install -r requirements.txt
streamlit run app.py
```

The app opens at https://fruitblend24-case-lf3egbkbwlbkxrys7ucrrv.streamlit.app/.

## Deploy it (free, Streamlit Community Cloud)

1. Put this `app/` folder in a GitHub repository. It must include `data/` and `.streamlit/config.toml`.
2. Go to share.streamlit.io, sign in with GitHub, choose **Create app**, and pick the repository.
3. Set the main file path to `app.py` (or `app/app.py` if the folder sits inside a larger repo), then deploy.
4. Share the URL it gives you in your submission.

## Pages

| Page | What it answers |
|---|---|
| Overview | The headline, 4 KPIs, the five findings and the recommended actions |
| Data quality | 26 checks, the raw → clean bridge, and how the item names were mapped |
| P&L vs budget | P&L by month, kitchen or product, filterable by kitchen, product and platform; kitchen operating profit; fruit-cost trend |
| Demand & pricing | Hourly, weekday and seasonal demand; a price simulator with three elasticity cases; LINE MAN vs Grab margin |
| Promotions | Lift vs break-even lift and profit impact for each code, by product and kitchen |
| Plan & inventory (Sep–Nov) | Scenario builder: P&L vs status quo and budget, what moved profit, cups to prep, fruit purchase, weekly order sheet, ordering rules |
| Method & assumptions | Model check, approach, assumptions, next steps |

## Where the numbers come from

`data/` is exported by the analysis scripts (`01_clean_data.py` → `03_analysis.py` → `06_export_app_data.py`) from the
raw case workbook. `model.py` holds the logic: the P&L, the promotion baseline, the price curves and the scenario
engine. Run with the status-quo settings, the scenario engine rebuilds last year's gross profit within 0.05% of the
actual figure (7.633M vs 7.636M).
