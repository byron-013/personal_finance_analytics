"""Main orchestration pipeline for Personal Finance Analytics."""

import os
import sys

from src.data_generator import (
    generate_users,
    generate_categories,
    generate_merchants,
    generate_accounts,
    generate_transactions,
    generate_budgets,
    generate_financial_goals,
    save_synthetic_data,
)
from src.database_manager import (
    initialize_database,
    load_data_to_db,
    create_indexes,
    validate_data_integrity,
)
from src.analytics import (
    get_spending_trends,
    analyze_budget_variance,
    calculate_savings_rate,
    identify_spending_anomalies,
    forecast_cash_flow,
    generate_insights,
    export_report_data,
)

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "data", "synthetic", "finance.db")
SCHEMA_PATH = os.path.join(BASE_DIR, "sql", "schema.sql")
CATEGORIES_CONFIG = os.path.join(BASE_DIR, "config", "categories.json")
SYNTHETIC_DATA_DIR = os.path.join(BASE_DIR, "data", "synthetic")
VIEWS_PATH = os.path.join(BASE_DIR, "sql", "views.sql")
REPORTS_DIR = os.path.join(BASE_DIR, "reports", "analysis_output")


def main():
    print("=== Personal Finance Analytics Pipeline ===\n")

    # Step 1: Generate synthetic data
    print("Step 1: Generating synthetic data...")
    users_df = generate_users(num_users=3)
    categories_df = generate_categories(CATEGORIES_CONFIG)
    merchants_df = generate_merchants(categories_df)
    accounts_df = generate_accounts(users_df)
    transactions_df = generate_transactions(accounts_df, merchants_df, categories_df, months=12)
    budgets_df = generate_budgets(users_df, categories_df, months=6)
    goals_df = generate_financial_goals(users_df)

    data_dict = {
        "users": users_df,
        "accounts": accounts_df,
        "categories": categories_df,
        "merchants": merchants_df,
        "transactions": transactions_df,
        "budgets": budgets_df,
        "financial_goals": goals_df,
    }

    # Step 2: Save CSVs for review
    print("\nStep 2: Saving synthetic data to CSV...")
    save_synthetic_data(data_dict, SYNTHETIC_DATA_DIR)

    # Step 3: Initialize database
    print("\nStep 3: Creating database...")
    conn = initialize_database(DB_PATH, SCHEMA_PATH)

    # Step 4: Load data
    print("\nStep 4: Loading data into database...")
    row_counts = load_data_to_db(conn, data_dict)

    # Step 5: Create indexes
    print("\nStep 5: Creating indexes...")
    create_indexes(conn)

    # Step 6: Create analytical views
    print("\nStep 6: Creating analytical views...")
    with open(VIEWS_PATH, "r") as f:
        conn.executescript(f.read())
    print("  Views created: monthly_summary, category_summary, budget_performance, "
          "account_balances_current, transaction_enriched")

    # Step 7: Validate data
    print("\nStep 7: Validating data integrity...")
    validate_data_integrity(conn)

    # Step 8: Run analytics for each user
    print("\nStep 8: Running analytics...")
    for user_id in range(1, 4):
        user_name = conn.execute(
            "SELECT first_name || ' ' || last_name FROM users WHERE user_id = ?",
            (user_id,)
        ).fetchone()[0]
        print(f"\n  --- User: {user_name} (ID: {user_id}) ---")

        # Spending trends
        trends = get_spending_trends(conn, user_id)
        print(f"  Spending trends: {len(trends)} category-month records")

        # Budget variance
        budget_var = analyze_budget_variance(conn, user_id)
        if not budget_var.empty:
            over = len(budget_var[budget_var["status"] == "OVER BUDGET"])
            print(f"  Budget variance: {len(budget_var)} categories, {over} over budget")

        # Savings rate
        savings = calculate_savings_rate(conn, user_id)
        if not savings.empty:
            avg_rate = savings["savings_rate_pct"].mean()
            print(f"  Average savings rate: {avg_rate:.1f}%")

        # Anomalies
        anomalies = identify_spending_anomalies(conn, user_id)
        print(f"  Anomalies detected: {len(anomalies)}")

        # Cash flow forecast
        forecast = forecast_cash_flow(conn, user_id)
        if not forecast.empty:
            print(f"  90-day projected balance: ${forecast.iloc[-1]['projected_balance']:,.2f}")

        # Insights
        insights = generate_insights(conn, user_id)
        print(f"\n  Insights:")
        for insight in insights:
            print(f"    - {insight}")

    # Step 9: Export reports
    print("\n\nStep 9: Exporting reports...")
    export_report_data(conn, 1, REPORTS_DIR)

    conn.close()

    print("\n=== Pipeline Complete ===")
    print(f"Database: {DB_PATH}")
    print(f"Reports: {REPORTS_DIR}")
    print("Check data/synthetic/ for CSV files")


if __name__ == "__main__":
    main()
