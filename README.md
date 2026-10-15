# FruitBlend24 — Analyst Case Submission
https://fruitblend24-case-lf3egbkbwlbkxrys7ucrrv.streamlit.app/

## What is in this folder

| File | What it is |
|---|---|
| `app/` | **Streamlit app (main deliverable)**: every analysis interactively, plus a Sep–Nov scenario builder. See `app/README.md` to run or deploy. |
| Slide deck (link shared separately) | 16-slide version of the same story, with speaker notes |
| `FruitBlend24_clean.xlsx` | Cleaned data + `dq_log` (26 data-quality checks) + raw→clean reconciliation |
| `FruitBlend24_analysis.xlsx` | Every table behind the deck: P&L (with live formulas), promo evaluation, price simulation, forecast backtest, Sep–Nov outlook by scenario, weekly inventory plan by kitchen × SKU, back-cast, assumptions |
| `01_clean_data.py` | Task 1: data quality checks and cleaning |
| `02_write_workbook.py` | Writes the clean workbook |
| `03_analysis.py` | Tasks 2–5: P&L, demand, pricing, promotions, forecast, inventory, scenarios |
| `04_charts.py` | Charts used in the deck (`charts/`) |
| `05_write_analysis_workbook.py` | Writes the analysis workbook |
| `06_export_app_data.py` | Exports the data the app reads (`app/data/`) |

Run in order: `python 01_clean_data.py FruitBlend24_Intern_Case_Data.xlsx`, then `02` → `06`. Then `cd app && streamlit run app.py`.

## Key insights

1. **Profit is seasonal and the flat budget hides it.** FY GP 7.64M vs 8.40M budget (−9%); operating profit −0.40M after 8.04M overhead. Hot season (Mar–May) beats budget by 29%; rainy season misses by 33% (−0.99M operating).
2. **Passion Fruit and Mixed Berry margins collapsed with fruit cost.** Passion Fruit fruit cost +51% from June (GP 14 → 3 THB/cup); Mixed Berry −17 THB/cup by August, 21% waste, −54k GP since launch.
3. **Both Bangkok kitchens lose money after overhead.** Ladprao −0.62M and loss-making in 12 of 12 months; Sukhumvit −0.49M. Pattaya kitchens +0.37M / +0.33M.
4. **No promotion pays for its discount.** Bundle Deal +32% lift vs 67% needed (−38k), Double Day +71% vs 114% (−53k), Seasonal Push +11% vs 47% (−64k).
5. **Demand peaks at lunch and late night (46% of cups in 6 hours); a LINE MAN cup earns 12.4 THB vs 15.4 on Grab.**

## Recommendations

1. **Pricing:** Passion Fruit 65 → 75, Watermelon 45 → 47, Pineapple 49 → 51, hold Guava (most price-sensitive). Test 4 weeks on LINE MAN first.
2. **Promotions:** stop Seasonal Push (RC103) and Bundle Deal (RC101); keep Double Day (RC102) only as a tagged acquisition test on Grab.
3. **Portfolio:** delist Mixed Berry (relaunch only at ≤35 THB fruit cost and <8% waste); give BKK Ladprao 90 days to cut overhead to ≤88k/month or close.
4. **Inventory:** seasonal weekly forecast → fruit orders twice a week → daypart batch prep with no pre-made buffer (newsvendor critical ratio 0.30–0.52) → daily waste tracking (core ≤5%, Passion Fruit ≤6%).

**Impact:** Sep–Nov 2026 GP 1.37M → 1.62M (+18%). Replayed over the last 12 months, the levers turn −0.40M operating profit into +0.28M (+0.75M with a Ladprao exit).

## Tools and approach

- Python (pandas, numpy, scipy, matplotlib); Streamlit + Plotly for the app; Excel outputs via openpyxl; LibreOffice to recalculate workbook formulas.
- **P&L:** built from orders × weekly fruit cost × commission × packaging/labor + daily waste cost. GP is before overhead, which matches the budget's ~26% GP margin.
- **Promotions:** each promo day compared with the same kitchen × SKU on non-promo days within ±28 days, same weekday/weekend type. Profit impact is valued at full-price margin.
- **Elasticity:** implied by promo lifts (log-lift ÷ log price ratio). The SKU-specific Bundle Deal estimate is the mid case; −0.8 and −2.4 are the bounds.
- **Forecast:** seasonal naive (same weekday last year, promo days removed, growth 1.00 because the Aug-26 run-rate ≈ Sep-25). Mixed Berry uses its Jun–Aug decay. A trailing 4-week forecast was backtested on Jun–Aug 2026 (weekly WAPE 11–12%, +9.5% bias at the season turn).
- **Validation:** the scenario model replayed over the last 12 months reproduces actual GP within 0.05% (7.633M vs 7.636M).

## What I would explore with more time

- Customer-level data, to measure whether Double Day new users come back (payback needs 0.26 repeat cups per incremental cup).
- Prep and stock-out logs: sales may be capped by availability, which would understate demand.
- Weather data, to explain rainy-season demand and plan prep better.
- Delivery-zone overlap, to test whether Sukhumvit could serve Ladprao customers.
- Platform-specific A/B price tests, and the cost of staffing overnight hours (2% of cups sell 2–6am).
- Negotiating LINE MAN commission: each point is worth about 0.17M a year.

