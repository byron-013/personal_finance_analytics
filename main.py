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

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "data", "synthetic", "finance.db")
SCHEMA_PATH = os.path.join(BASE_DIR, "sql", "schema.sql")
CATEGORIES_CONFIG = os.path.join(BASE_DIR, "config", "categories.json")
SYNTHETIC_DATA_DIR = os.path.join(BASE_DIR, "data", "synthetic")


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

    # Step 6: Validate data
    print("\nStep 6: Validating data integrity...")
    validate_data_integrity(conn)

    conn.close()

    print("\n=== Pipeline Complete ===")
    print(f"Database: {DB_PATH}")
    print("Check data/synthetic/ for CSV files")


if __name__ == "__main__":
    main()
