"""Main orchestration pipeline for Personal Finance Analytics."""

import argparse
import json
import os
import sys

import pandas as pd

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
    print_and_save_table,
)
from src.visualizations import generate_all_charts
from src.profile_builder import build_profile

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
    parser.add_argument("--middle-class-tier", type=str, default=None,
                        choices=["low", "mid", "high"],
                        help="Narrow middle class income to a sub-tier: low (lower-middle), mid (solidly-middle), high (upper-middle)")
    parser.add_argument("--mode", type=str, default="standard",
                        choices=["standard", "pro"],
                        help="Run mode: standard (default) or pro (demographic profiling)")
    args = parser.parse_args()

    # Load state configuration
    state_config = load_state_config(STATES_CONFIG, args.state)
    state_name = state_config["name"]

    # Middle class tier refinement
    tier = args.middle_class_tier
    if tier is None and sys.stdin.isatty():
        refine = input("Refine middle class tier? (y/n): ").strip().lower()
        if refine == "y":
            print("  1) lower-middle  (bottom third of range)")
            print("  2) solidly-middle (middle third of range)")
            print("  3) upper-middle  (top third of range)")
            choice = input("Select tier (1/2/3): ").strip()
            tier = {"1": "low", "2": "mid", "3": "high"}.get(choice)
            if tier is None:
                print("  Invalid choice — using full middle class range.")

    if tier:
        inc_min, inc_max = state_config["middle_class_income"]
        third = (inc_max - inc_min) / 3
        if tier == "low":
            state_config["middle_class_income"] = [inc_min, round(inc_min + third)]
        elif tier == "mid":
            state_config["middle_class_income"] = [round(inc_min + third), round(inc_min + 2 * third)]
        elif tier == "high":
            state_config["middle_class_income"] = [round(inc_min + 2 * third), inc_max]
        tier_labels = {"low": "lower-middle", "mid": "solidly-middle", "high": "upper-middle"}
        print(f"  Income range narrowed to {tier_labels[tier]}: "
              f"${state_config['middle_class_income'][0]:,} – ${state_config['middle_class_income'][1]:,}")

    # --- Pro Mode: demographic profiling ---
    profile = None
    if args.mode == "pro":
        print("\n=== FinanceIQ Pro Mode ===")
        print("Select which demographic toggles to enable:")
        print("  1) Age")
        print("  2) Marriage")
        print("  3) Kids")
        print("  4) Social Factors")
        toggle_input = input("Enter toggle numbers separated by commas (e.g. 1,3): ").strip()
        toggles = {t.strip() for t in toggle_input.split(",") if t.strip()}

        # --- Age toggle ---
        pro_age = None
        if "1" in toggles:
            age_input = input("  Age: enter a specific age or press Enter to sample randomly: ").strip()
            if age_input:
                pro_age = int(age_input)

        # --- Marriage toggle ---
        pro_marriage = None
        if "2" in toggles:
            m_input = input("  Married? (yes/no/random): ").strip().lower()
            if m_input == "yes":
                is_married = True
                d_input = input("  Dual income? (yes/no/random): ").strip().lower()
                if d_input == "yes":
                    dual = True
                elif d_input == "no":
                    dual = False
                else:
                    dual = None
                pro_marriage = {"is_married": is_married, "dual_income": dual}
            elif m_input == "no":
                pro_marriage = {"is_married": False, "dual_income": None}
            else:
                pro_marriage = {"is_married": None, "dual_income": None}

        # --- Kids toggle ---
        pro_kids = None
        if "3" in toggles:
            k_input = input("  Number of children (or press Enter to sample randomly): ").strip()
            if k_input:
                num_kids = int(k_input)
                child_ages_list = []
                for i in range(num_kids):
                    ca = input(f"    Age of child {i+1}: ").strip()
                    child_ages_list.append(int(ca))
                pro_kids = {"num_children": num_kids, "child_ages": child_ages_list}
            else:
                pro_kids = {"num_children": None, "child_ages": None}

        # --- Social factors toggle ---
        pro_social = None
        if "4" in toggles:
            s_input = input("  Specify race/ethnicity/gender or press Enter to sample randomly: ").strip()
            if s_input:
                race_in = input("    Race (white/black/hispanic/asian/other): ").strip().lower() or None
                eth_in = input("    Ethnicity (hispanic/non-hispanic): ").strip().lower() or None
                gen_in = input("    Gender (male/female): ").strip().lower() or None
                pro_social = {"race": race_in, "ethnicity": eth_in, "gender": gen_in}
            else:
                pro_social = {"race": None, "ethnicity": None, "gender": None}

        profile = build_profile(
            state=args.state,
            age=pro_age,
            marriage=pro_marriage,
            kids=pro_kids,
            social=pro_social,
        )
        print("\n  --- Generated Profile ---")
        for k, v in profile.items():
            print(f"    {k}: {v}")
        print()

        # Save profile to JSON so the dashboard can display it
        profile_path = os.path.join(SYNTHETIC_DATA_DIR, "profile.json")
        os.makedirs(SYNTHETIC_DATA_DIR, exist_ok=True)
        with open(profile_path, "w") as pf:
            json.dump(profile, pf, indent=2)
    else:
        # Remove stale profile if running in standard mode
        profile_path = os.path.join(SYNTHETIC_DATA_DIR, "profile.json")
        if os.path.exists(profile_path):
            os.remove(profile_path)

    print(f"=== Personal Finance Analytics Pipeline ({state_name}) ===\n")

    # Step 1: Generate synthetic data
    print("Step 1: Generating synthetic data...")
    users_df = generate_users(num_users=3, state_config=state_config)
    categories_df = generate_categories(CATEGORIES_CONFIG)
    merchants_df = generate_merchants(categories_df)
    accounts_df = generate_accounts(users_df)
    transactions_df = generate_transactions(accounts_df, merchants_df, categories_df,
                                            users_df, state_config=state_config,
                                            months=args.months, profile=profile)
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
        user_dir = os.path.join(REPORTS_DIR, user_name.replace(" ", "_"))
        print(f"\n  --- User: {user_name} (ID: {user_id}) ---")

        trends = get_spending_trends(conn, user_id)
        print(f"  Spending trends: {len(trends)} category-month records")

        # Budget vs Actual
        budget_var = analyze_budget_variance(conn, user_id)
        if not budget_var.empty:
            over = len(budget_var[budget_var["status"] == "OVER BUDGET"])
            print(f"  Budget variance: {len(budget_var)} categories, {over} over budget")
            print_and_save_table(budget_var, f"{user_name} Budget vs Actual", user_dir)

        # Top merchants by spend
        top_merchants = pd.read_sql_query("""
            SELECT m.merchant_name, c.parent_category,
                   COUNT(*) AS txn_count,
                   ROUND(SUM(ABS(t.amount)), 2) AS total_spent
            FROM transactions t
            JOIN accounts a ON t.account_id = a.account_id
            JOIN merchants m ON t.merchant_id = m.merchant_id
            JOIN categories c ON t.category_id = c.category_id
            WHERE a.user_id = ? AND c.category_type = 'expense'
            GROUP BY m.merchant_name, c.parent_category
            ORDER BY total_spent DESC
            LIMIT 15
        """, conn, params=[user_id])
        print_and_save_table(top_merchants, f"{user_name} Top Merchants by Spend", user_dir)

        # Category % of total spending
        cat_pct = pd.read_sql_query("""
            SELECT c.parent_category,
                   ROUND(SUM(ABS(t.amount)), 2) AS total_spent,
                   ROUND(SUM(ABS(t.amount)) * 100.0 /
                         (SELECT SUM(ABS(t2.amount))
                          FROM transactions t2
                          JOIN accounts a2 ON t2.account_id = a2.account_id
                          JOIN categories c2 ON t2.category_id = c2.category_id
                          WHERE a2.user_id = ? AND c2.category_type = 'expense'), 1
                   ) AS pct_of_total
            FROM transactions t
            JOIN accounts a ON t.account_id = a.account_id
            JOIN categories c ON t.category_id = c.category_id
            WHERE a.user_id = ? AND c.category_type = 'expense'
            GROUP BY c.parent_category
            ORDER BY total_spent DESC
        """, conn, params=[user_id, user_id])
        print_and_save_table(cat_pct, f"{user_name} Category Pct of Total Spending", user_dir)

        # Monthly savings rate
        savings = calculate_savings_rate(conn, user_id)
        if not savings.empty:
            avg_rate = savings["savings_rate_pct"].mean()
            print(f"  Average savings rate: {avg_rate:.1f}%")
            print_and_save_table(savings, f"{user_name} Monthly Savings Rate", user_dir)

        anomalies = identify_spending_anomalies(conn, user_id)
        print(f"  Anomalies detected: {len(anomalies)}")

        # 30/60/90 day balance projection
        forecast = forecast_cash_flow(conn, user_id)
        if not forecast.empty:
            print(f"  90-day projected balance: ${forecast.iloc[-1]['projected_balance']:,.2f}")
            print_and_save_table(forecast, f"{user_name} 30 60 90 Day Balance Projection", user_dir)

        insights = generate_insights(conn, user_id)
        print(f"\n  Insights:")
        for insight in insights:
            print(f"    - {insight}")

    # Income summary per user (gross and estimated net)
    print("\n  --- Income Summary (All Users) ---")
    income_summary_rows = []
    for user_id in user_ids:
        row = conn.execute(
            "SELECT first_name || ' ' || last_name, annual_income FROM users WHERE user_id = ?",
            (user_id,)
        ).fetchone()
        user_name_inc = row[0]
        gross = row[1]
        from src.data_generator import _estimate_monthly_takehome
        monthly_net = _estimate_monthly_takehome(gross, state_config)
        annual_net = round(monthly_net * 12, 2)
        income_summary_rows.append({
            "user": user_name_inc,
            "annual_gross": round(gross, 2),
            "est_annual_net": annual_net,
            "est_monthly_net": monthly_net,
        })
    income_summary_df = pd.DataFrame(income_summary_rows)
    print_and_save_table(income_summary_df, "Income Summary per User")

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
