# Personal Finance Analytics — Extended Branch

A financial transaction analysis system that generates synthetic banking data, stores it in a normalized SQLite database, and runs analytical queries to surface spending patterns, budget performance, and cash flow projections.

This branch (`more_accurate_income_ranges_middle_class`) adds **middle class tier refinement**, **rich terminal tables**, and an **interactive Streamlit dashboard**.

## What's New in This Branch

### Middle Class Tier Toggle
Narrow the income range to a specific sub-tier of the middle class instead of using the full range:
- **lower-middle** — bottom third of the state's middle class range
- **solidly-middle** — middle third
- **upper-middle** — top third

Use via CLI flag or interactive prompt:
```bash
# CLI flag
python main.py --state CA --middle-class-tier low

# Interactive — program will ask after state selection
python main.py --state CA
```

### Rich Terminal Tables
Key analytics results are printed as formatted tables in the terminal (using the `rich` library) and saved as CSVs. Tables are displayed for:
- Budget vs Actual
- Top 15 Merchants by Spend
- Category % of Total Spending
- Monthly Savings Rate
- 30/60/90 Day Balance Projection
- Income Summary per User (gross and estimated net)

### Streamlit Dashboard
An interactive browser-based dashboard for exploring the data visually.

```bash
# First generate the data
python main.py --state CA

# Then launch the dashboard
streamlit run dashboard.py
```

The dashboard includes:
- **KPI cards** — monthly income, expenses, net savings, savings rate (with deltas)
- **Monthly Overview** — bar charts and detail table for income vs expenses
- **Budget vs Actual** — month selector with color-coded status (over budget / at risk / on track)
- **Top Merchants** — sortable table and bar chart of top 20 merchants
- **Category Breakdown** — spending distribution with percentages
- **Cash Flow Forecast** — 30/60/90 day balance projection with line chart
- **User selector** in sidebar to switch between users

### Organized Output
Reports are now organized by file type under each user's folder:
```
reports/analysis_output/
├── Patricia_Miller/
│   ├── csv/           # All CSV reports
│   └── charts/        # All PNG chart images
├── William_Johnson/
│   ├── csv/
│   └── charts/
└── Danielle_Johnson/
    ├── csv/
    └── charts/
```

## Setup & Usage

```bash
# Install dependencies (use a virtual environment)
pip install -r requirements.txt

# Run the full pipeline
python main.py --state CA

# Launch the interactive dashboard
streamlit run dashboard.py
```

### CLI Options

```
--state CODE              State code for tax/COL (default: CA)
--middle-class-tier TIER  Narrow income range: low, mid, or high
--user-id ID              Run analytics for a specific user (default: all)
--months N                Months of data to generate (default: 12)
--skip-viz                Skip PNG chart generation
```

### Supported States

| Code | State | Code | State |
|------|-------|------|-------|
| CA | California | MA | Massachusetts |
| CO | Colorado | NJ | New Jersey |
| FL | Florida | NY | New York |
| IL | Illinois | PA | Pennsylvania |
| TX | Texas | WA | Washington |

## Project Structure

```
personal-finance-analytics/
├── main.py                    # Pipeline entry point
├── dashboard.py               # Streamlit interactive dashboard
├── config/
│   ├── categories.json        # Spending/income category definitions
│   └── states.json            # State tax brackets and cost of living data
├── sql/
│   ├── schema.sql             # Database schema (7 tables)
│   ├── analytical_queries.sql # 10 analytical queries
│   └── views.sql              # 5 reusable views
├── src/
│   ├── data_generator.py      # Synthetic data generation
│   ├── database_manager.py    # DB init, loading, validation
│   ├── analytics.py           # Trend analysis, forecasting, insights, rich tables
│   └── visualizations.py      # Chart generation (PNG)
├── data/synthetic/            # Generated CSVs and .db (gitignored)
└── reports/analysis_output/   # Charts and exported reports (gitignored)
```

## Tech Stack

- Python, Pandas, NumPy
- SQLite (normalized schema with indexes and views)
- Matplotlib, Seaborn (static charts)
- Rich (terminal table formatting)
- Streamlit (interactive dashboard)
- Faker (synthetic data)
