"""Main orchestration pipeline for Personal Finance Analytics."""

import argparse
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
    load_state_config,
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
from src.visualizations import generate_all_charts

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "data", "synthetic", "finance.db")
SCHEMA_PATH = os.path.join(BASE_DIR, "sql", "schema.sql")
CATEGORIES_CONFIG = os.path.join(BASE_DIR, "config", "categories.json")
SYNTHETIC_DATA_DIR = os.path.join(BASE_DIR, "data", "synthetic")
VIEWS_PATH = os.path.join(BASE_DIR, "sql", "views.sql")
REPORTS_DIR = os.path.join(BASE_DIR, "reports", "analysis_output")
STATES_CONFIG = os.path.join(BASE_DIR, "config", "states.json")


def main():
    parser = argparse.ArgumentParser(description="Personal Finance Analytics Pipeline")
    parser.add_argument("--user-id", type=int, default=None,
                        help="Run analytics for a specific user ID (default: all users)")
    parser.add_argument("--months", type=int, default=12,
                        help="Number of months of data to generate (default: 12)")
    parser.add_argument("--skip-viz", action="store_true",
                        help="Skip chart generation")
    parser.add_argument("--state", type=str, default="CA",
                        help="State code for tax rates and cost of living (default: CA)")
    args = parser.parse_args()

    # Load state configuration
    state_config = load_state_config(STATES_CONFIG, args.state)
    state_name = state_config["name"]

    print(f"=== Personal Finance Analytics Pipeline ({state_name}) ===\n")

    # Step 1: Generate synthetic data
    print("Step 1: Generating synthetic data...")
    users_df = generate_users(num_users=3, state_config=state_config)
    categories_df = generate_categories(CATEGORIES_CONFIG)
    merchants_df = generate_merchants(categories_df)
    accounts_df = generate_accounts(users_df)
    transactions_df = generate_transactions(accounts_df, merchants_df, categories_df,
                                            users_df, state_config=state_config,
                                            months=args.months)
    budgets_df = generate_budgets(users_df, categories_df, state_config=state_config,
                                  months=6)
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
    load_data_to_db(conn, data_dict)

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

    # Determine which users to analyze
    if args.user_id:
        user_ids = [args.user_id]
    else:
        user_ids = [row[0] for row in conn.execute("SELECT user_id FROM users").fetchall()]

    # Step 8: Run analytics
    print("\nStep 8: Running analytics...")
    for user_id in user_ids:
        user_name = conn.execute(
            "SELECT first_name || ' ' || last_name FROM users WHERE user_id = ?",
            (user_id,)
        ).fetchone()[0]
        print(f"\n  --- User: {user_name} (ID: {user_id}) ---")

        trends = get_spending_trends(conn, user_id)
        print(f"  Spending trends: {len(trends)} category-month records")

        budget_var = analyze_budget_variance(conn, user_id)
        if not budget_var.empty:
            over = len(budget_var[budget_var["status"] == "OVER BUDGET"])
            print(f"  Budget variance: {len(budget_var)} categories, {over} over budget")

        savings = calculate_savings_rate(conn, user_id)
        if not savings.empty:
            avg_rate = savings["savings_rate_pct"].mean()
            print(f"  Average savings rate: {avg_rate:.1f}%")

        anomalies = identify_spending_anomalies(conn, user_id)
        print(f"  Anomalies detected: {len(anomalies)}")

        forecast = forecast_cash_flow(conn, user_id)
        if not forecast.empty:
            print(f"  90-day projected balance: ${forecast.iloc[-1]['projected_balance']:,.2f}")

        insights = generate_insights(conn, user_id)
        print(f"\n  Insights:")
        for insight in insights:
            print(f"    - {insight}")

    # Step 9: Generate visualizations
    if not args.skip_viz:
        print("\n\nStep 9: Generating visualizations...")
        for user_id in user_ids:
            user_name = conn.execute(
                "SELECT first_name || ' ' || last_name FROM users WHERE user_id = ?",
                (user_id,)
            ).fetchone()[0]
            user_dir = os.path.join(REPORTS_DIR, user_name.replace(" ", "_"))
            print(f"\n  Charts for {user_name}:")
            generate_all_charts(conn, user_id, user_dir)
    else:
        print("\n\nStep 9: Skipping visualizations (--skip-viz)")

    # Step 10: Export reports
    print("\nStep 10: Exporting reports...")
    for user_id in user_ids:
        user_name = conn.execute(
            "SELECT first_name || ' ' || last_name FROM users WHERE user_id = ?",
            (user_id,)
        ).fetchone()[0]
        user_dir = os.path.join(REPORTS_DIR, user_name.replace(" ", "_"))
        export_report_data(conn, user_id, user_dir)

    conn.close()

    print("\n=== Pipeline Complete ===")
    print(f"Database: {DB_PATH}")
    print(f"Reports: {REPORTS_DIR}")


if __name__ == "__main__":
    main()
