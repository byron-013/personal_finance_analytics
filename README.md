# Personal Finance Analytics

A financial transaction analysis system that generates synthetic banking data, stores it in a normalized SQLite database, and runs analytical queries to surface spending patterns, budget performance, and cash flow projections.

## What It Does

- Generates 12 months of realistic financial transactions for multiple users (income, recurring bills, groceries, shopping, etc.)
- Loads data into a normalized database (7 tables, 3NF with foreign keys)
- Runs 10 analytical SQL queries covering budget variance, cash flow, anomaly detection, and more
- Produces automated plain-English insights per user
- Outputs charts (spending trends, budget vs actual, category breakdowns, savings rate)
- Exports report CSVs for further analysis

## Project Structure

```
personal-finance-analytics/
├── main.py                    # Pipeline entry point
├── config/
│   └── categories.json        # Spending/income category definitions
├── sql/
│   ├── schema.sql             # Database schema (7 tables)
│   ├── analytical_queries.sql # 10 analytical queries
│   └── views.sql              # 5 reusable views
├── src/
│   ├── data_generator.py      # Synthetic data generation
│   ├── database_manager.py    # DB init, loading, validation
│   ├── analytics.py           # Trend analysis, forecasting, insights
│   └── visualizations.py      # Chart generation
├── data/synthetic/            # Generated CSVs and .db (gitignored)
└── reports/analysis_output/   # Charts and exported reports (gitignored)
```

## Database Schema

| Table | Description |
|-------|-------------|
| `users` | User profiles with income |
| `accounts` | Bank accounts (checking, savings, credit card) |
| `categories` | Spending/income categories with parent-child hierarchy |
| `merchants` | Merchants linked to categories |
| `transactions` | Financial transactions with amounts, dates, recurring flags |
| `budgets` | Monthly budget targets per category |
| `financial_goals` | Savings, debt payoff, and investment goals |

## Analytical Queries

The `sql/analytical_queries.sql` file contains 10 queries:

1. Monthly spending by category
2. Budget vs actual variance with status flags
3. Top 10 merchants by total spend
4. Recurring transaction identification
5. Month-over-month spending growth (window functions)
6. Cash flow analysis with cumulative savings
7. Category spending distribution (% of total)
8. Year-over-year quarterly comparison
9. Account balance projection (30/60/90 days)
10. Anomaly detection (transactions > 2 standard deviations)

## Setup & Usage

```bash
pip install -r requirements.txt
python main.py
```

### Options

```
--user-id ID    Run analytics for a specific user (default: all)
--months N      Months of data to generate (default: 12)
--skip-viz      Skip chart generation
```

### Output

- **Database:** `data/synthetic/finance.db`
- **Charts:** `reports/analysis_output/*.png`
- **Reports:** `reports/analysis_output/*.csv`

## Tech Stack

- Python, Pandas, NumPy
- SQLite (normalized schema with indexes and views)
- Matplotlib, Seaborn
- Faker (synthetic data)
