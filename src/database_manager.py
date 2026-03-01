"""Database management: initialization, data loading, indexing, and validation."""

import sqlite3
import os


def initialize_database(db_path, schema_path):
    """Create SQLite database and execute schema.sql."""
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    # Remove existing database for clean start
    if os.path.exists(db_path):
        os.remove(db_path)

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")

    with open(schema_path, "r") as f:
        schema_sql = f.read()
    conn.executescript(schema_sql)

    print(f"  Database created at {db_path}")
    return conn


def load_data_to_db(conn, data_dict):
    """Insert all synthetic data with transaction handling and foreign key checks."""
    conn.execute("PRAGMA foreign_keys = ON")
    cursor = conn.cursor()

    # Insert order matters for foreign key constraints
    insert_order = [
        "users", "accounts", "categories", "merchants",
        "transactions", "budgets", "financial_goals",
    ]

    row_counts = {}

    for table_name in insert_order:
        if table_name not in data_dict:
            continue

        df = data_dict[table_name]
        columns = df.columns.tolist()
        placeholders = ", ".join(["?"] * len(columns))
        col_names = ", ".join(columns)
        sql = f"INSERT INTO {table_name} ({col_names}) VALUES ({placeholders})"

        try:
            rows = df.values.tolist()
            cursor.executemany(sql, rows)
            conn.commit()
            row_counts[table_name] = len(rows)
            print(f"  Loaded {table_name}: {len(rows)} rows")
        except sqlite3.IntegrityError as e:
            conn.rollback()
            print(f"  ERROR loading {table_name}: {e}")
            row_counts[table_name] = 0

    return row_counts


def create_indexes(conn):
    """Add indexes on frequently queried columns for performance."""
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions(transaction_date)",
        "CREATE INDEX IF NOT EXISTS idx_transactions_category ON transactions(category_id)",
        "CREATE INDEX IF NOT EXISTS idx_transactions_account ON transactions(account_id)",
        "CREATE INDEX IF NOT EXISTS idx_transactions_merchant ON transactions(merchant_id)",
        "CREATE INDEX IF NOT EXISTS idx_accounts_user ON accounts(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_budgets_user ON budgets(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_budgets_category ON budgets(category_id)",
        "CREATE INDEX IF NOT EXISTS idx_budgets_month ON budgets(month_year)",
    ]

    for idx_sql in indexes:
        conn.execute(idx_sql)
    conn.commit()
    print(f"  Created {len(indexes)} indexes")


def validate_data_integrity(conn):
    """Run integrity checks and print a validation report."""
    cursor = conn.cursor()
    issues = []

    # Row counts
    tables = ["users", "accounts", "categories", "merchants",
              "transactions", "budgets", "financial_goals"]
    print("\n  === Data Validation Report ===")
    print("  Table Row Counts:")
    for table in tables:
        count = cursor.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"    {table}: {count}")

    # Check orphaned foreign keys
    fk_checks = [
        ("accounts", "user_id", "users", "user_id"),
        ("merchants", "category_id", "categories", "category_id"),
        ("transactions", "account_id", "accounts", "account_id"),
        ("transactions", "merchant_id", "merchants", "merchant_id"),
        ("transactions", "category_id", "categories", "category_id"),
        ("budgets", "user_id", "users", "user_id"),
        ("budgets", "category_id", "categories", "category_id"),
        ("financial_goals", "user_id", "users", "user_id"),
    ]

    print("\n  Foreign Key Integrity:")
    for child_table, child_col, parent_table, parent_col in fk_checks:
        orphans = cursor.execute(
            f"SELECT COUNT(*) FROM {child_table} c "
            f"LEFT JOIN {parent_table} p ON c.{child_col} = p.{parent_col} "
            f"WHERE p.{parent_col} IS NULL"
        ).fetchone()[0]
        status = "PASS" if orphans == 0 else f"FAIL ({orphans} orphans)"
        if orphans > 0:
            issues.append(f"{child_table}.{child_col} -> {parent_table}.{parent_col}")
        print(f"    {child_table}.{child_col} -> {parent_table}.{parent_col}: {status}")

    # Check transaction amounts: expenses should be negative, income positive
    bad_expenses = cursor.execute(
        "SELECT COUNT(*) FROM transactions t "
        "JOIN categories c ON t.category_id = c.category_id "
        "WHERE c.category_type = 'expense' AND t.amount > 0"
    ).fetchone()[0]
    bad_income = cursor.execute(
        "SELECT COUNT(*) FROM transactions t "
        "JOIN categories c ON t.category_id = c.category_id "
        "WHERE c.category_type = 'income' AND t.amount < 0"
    ).fetchone()[0]

    print("\n  Amount Sign Checks:")
    print(f"    Expenses with positive amounts: {bad_expenses} {'(PASS)' if bad_expenses == 0 else '(WARNING)'}")
    print(f"    Income with negative amounts: {bad_income} {'(PASS)' if bad_income == 0 else '(WARNING)'}")

    # Check date ranges
    date_range = cursor.execute(
        "SELECT MIN(transaction_date), MAX(transaction_date) FROM transactions"
    ).fetchone()
    print(f"\n  Transaction Date Range: {date_range[0]} to {date_range[1]}")

    # Null checks on required fields
    null_checks = [
        ("users", "email"),
        ("transactions", "amount"),
        ("transactions", "transaction_date"),
    ]
    print("\n  Null Value Checks:")
    for table, col in null_checks:
        nulls = cursor.execute(
            f"SELECT COUNT(*) FROM {table} WHERE {col} IS NULL"
        ).fetchone()[0]
        print(f"    {table}.{col}: {'PASS' if nulls == 0 else f'FAIL ({nulls} nulls)'}")

    if issues:
        print(f"\n  ISSUES FOUND: {len(issues)}")
    else:
        print("\n  All checks passed.")

    return len(issues) == 0
