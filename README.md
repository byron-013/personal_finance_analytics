# FinanceIQ Pro — Demographic-Aware Finance Analytics

A financial transaction analysis system that generates synthetic banking data, stores it in a normalized SQLite database, and runs analytical queries to surface spending patterns, budget performance, and cash flow projections.

This branch (`financeiq-pro`) adds **demographic profiling** with toggleable factors (Age, Marriage, Kids, Social Factors) that influence income and expense generation using Census, CDC, and BLS statistical data.

## What's New in This Branch

### Pro Mode (`--mode pro`)
An interactive demographic profiling system that adjusts financial data generation based on real-world statistical patterns:

- **Age** — Sample or specify age; influences marriage probability and fertility rates
- **Marriage** — Married/single status with optional dual-income household modeling
- **Kids** — Number and ages of children; adds childcare ($1,800/mo per child under 5) and education ($400/mo per child 5-17) expenses
- **Social Factors** — Race/ethnicity/gender with BLS wage gap multipliers applied to income

**Ironclad Rule**: Any toggle set to OFF (None) is never used as input to any other calculation and is never inferred.

```bash
# Pro mode with interactive prompts
python main.py --state CA --mode pro

# Standard mode (unchanged behavior)
python main.py --state CA
```

### Demographics Config (`config/demographics.json`)
Statistical data for all 10 supported states:
- Marriage rates by age bucket (Census-based)
- Fertility rates by age and marital status (CDC-based)
- BLS wage gap multipliers by race/gender
- State-level racial/ethnic composition for random sampling

### Profile Builder (`src/profile_builder.py`)
Standalone module that constructs a profile dict with explicit None handling for every toggle combination. Supports all 16 combinations of 4 toggles.

### Inherited Features
All features from the `more_accurate_income_ranges_middle_class` branch:
- Middle class tier toggle (low/mid/high)
- Rich terminal table printing
- State-specific tax rates and cost of living scaling
- Streamlit dashboard

### LLM Expense Realism (`src/llm_expense_adjuster.py`)
When an `ANTHROPIC_API_KEY` environment variable is set, Pro mode sends the demographic profile to the Claude API to generate realistic expense multipliers that replace the rule-based defaults. The LLM sees only non-None profile fields and returns category-specific adjustments relative to the state's middle-class baseline.

Use `--no-llm` to run full Pro mode without the API call.

**Note on Social Factors**: The social factor toggles reflect documented US statistical patterns from BLS and Census data. They are included for demographic simulation accuracy, not as value judgments.

## Setup & Usage

```bash
# Switch to this branch
git checkout financeiq-pro

# Install dependencies (use a virtual environment)
pip install -r requirements.txt

# Standard mode
python main.py --state CA

# Pro mode (rule-based)
python main.py --state CA --mode pro --no-llm

# Pro mode (with LLM expense realism — requires API key)
export ANTHROPIC_API_KEY=your-key-here
python main.py --state CA --mode pro

# Launch the interactive dashboard
streamlit run dashboard.py
```

### CLI Options

```
--state CODE              State code for tax/COL (default: CA)
--mode MODE               standard (default) or pro (demographic profiling)
--middle-class-tier TIER  Narrow income range: low, mid, or high
--no-llm                  Skip LLM API call, use rule-based adjustments
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
├── main.py                    # Pipeline entry point (standard + pro modes)
├── dashboard.py               # Streamlit interactive dashboard
├── config/
│   ├── categories.json        # Spending/income category definitions
│   ├── states.json            # State tax brackets and cost of living data
│   └── demographics.json      # Marriage, fertility, wage gap, demographics
├── sql/
│   ├── schema.sql             # Database schema (7 tables)
│   ├── analytical_queries.sql # 10 analytical queries
│   └── views.sql              # 5 reusable views
├── src/
│   ├── data_generator.py      # Synthetic data generation (profile-aware)
│   ├── profile_builder.py     # Demographic profile construction
│   ├── llm_expense_adjuster.py # LLM-powered expense realism (Claude API)
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
- Anthropic Claude API (LLM expense realism)
- Faker (synthetic data)
