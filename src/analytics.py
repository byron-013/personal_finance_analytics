"""Analytics functions for spending trends, budgets, forecasting, and insights."""

import sqlite3
import os

import pandas as pd
import numpy as np


def get_spending_trends(conn, user_id, months=12):
    """Query monthly spending by category for a given user."""
    query = """
        SELECT
            strftime('%Y-%m', t.transaction_date) AS month,
            c.parent_category,
            c.category_name,
            COUNT(*) AS transaction_count,
            ROUND(SUM(ABS(t.amount)), 2) AS total_spent
        FROM transactions t
        JOIN accounts a ON t.account_id = a.account_id
        JOIN categories c ON t.category_id = c.category_id
        WHERE a.user_id = ?
            AND c.category_type = 'expense'
            AND t.transaction_date >= date('now', ?)
        GROUP BY month, c.parent_category, c.category_name
        ORDER BY month, total_spent DESC
    """
    return pd.read_sql_query(query, conn, params=[user_id, f"-{months} months"])


def analyze_budget_variance(conn, user_id, month_year=None):
    """Calculate actual vs budget for all categories, flagging over-budget items."""
    if month_year is None:
        # Default to the most recent budget month
        row = conn.execute(
            "SELECT MAX(month_year) FROM budgets WHERE user_id = ?", (user_id,)
        ).fetchone()
        month_year = row[0] if row else None
        if month_year is None:
            return pd.DataFrame()

    query = """
        SELECT
            c.parent_category,
            c.category_name,
            ROUND(b.budget_amount, 2) AS budgeted,
            ROUND(COALESCE(SUM(ABS(t.amount)), 0), 2) AS actual_spent,
            ROUND(b.budget_amount - COALESCE(SUM(ABS(t.amount)), 0), 2) AS variance,
            ROUND(
                (COALESCE(SUM(ABS(t.amount)), 0) / b.budget_amount) * 100, 1
            ) AS pct_used,
            CASE
                WHEN COALESCE(SUM(ABS(t.amount)), 0) > b.budget_amount THEN 'OVER BUDGET'
                WHEN COALESCE(SUM(ABS(t.amount)), 0) > b.budget_amount * 0.9 THEN 'AT RISK'
                ELSE 'ON TRACK'
            END AS status
        FROM budgets b
        JOIN categories c ON b.category_id = c.category_id
        LEFT JOIN transactions t
            ON t.category_id = b.category_id
            AND strftime('%Y-%m', t.transaction_date) = b.month_year
        WHERE b.user_id = ?
            AND b.month_year = ?
        GROUP BY b.budget_id, c.parent_category, c.category_name, b.budget_amount
        ORDER BY pct_used DESC
    """
    return pd.read_sql_query(query, conn, params=[user_id, month_year])


def calculate_savings_rate(conn, user_id, period="monthly"):
    """Compute savings rate as (income - expenses) / income over time."""
    query = """
        SELECT
            strftime('%Y-%m', t.transaction_date) AS month,
            ROUND(SUM(CASE WHEN c.category_type = 'income' THEN t.amount ELSE 0 END), 2) AS income,
            ROUND(SUM(CASE WHEN c.category_type = 'expense' THEN ABS(t.amount) ELSE 0 END), 2) AS expenses
        FROM transactions t
        JOIN accounts a ON t.account_id = a.account_id
        JOIN categories c ON t.category_id = c.category_id
        WHERE a.user_id = ?
        GROUP BY month
        ORDER BY month
    """
    df = pd.read_sql_query(query, conn, params=[user_id])
    if df.empty:
        return df

    df["net_savings"] = df["income"] - df["expenses"]
    df["savings_rate_pct"] = np.where(
        df["income"] > 0,
        ((df["income"] - df["expenses"]) / df["income"] * 100).round(1),
        0.0
    )
    return df


def identify_spending_anomalies(conn, user_id, threshold=2.0):
    """Find transactions that exceed threshold standard deviations from their category average."""
    query = """
        SELECT
            t.transaction_id,
            t.transaction_date,
            m.merchant_name,
            c.parent_category,
            c.category_name,
            ROUND(ABS(t.amount), 2) AS amount,
            t.description
        FROM transactions t
        JOIN accounts a ON t.account_id = a.account_id
        JOIN merchants m ON t.merchant_id = m.merchant_id
        JOIN categories c ON t.category_id = c.category_id
        WHERE a.user_id = ?
            AND c.category_type = 'expense'
        ORDER BY t.transaction_date
    """
    df = pd.read_sql_query(query, conn, params=[user_id])
    if df.empty:
        return df

    # Calculate per-category stats
    stats = df.groupby("category_name")["amount"].agg(["mean", "std"]).reset_index()
    stats.columns = ["category_name", "cat_avg", "cat_std"]

    df = df.merge(stats, on="category_name")
    df["upper_bound"] = df["cat_avg"] + threshold * df["cat_std"]
    anomalies = df[df["amount"] > df["upper_bound"]].copy()
    anomalies["times_avg"] = (anomalies["amount"] / anomalies["cat_avg"]).round(1)

    return anomalies[["transaction_date", "merchant_name", "parent_category",
                       "category_name", "amount", "cat_avg", "times_avg", "description"]]


def forecast_cash_flow(conn, user_id, months_ahead=3):
    """Project future balances using a simple moving average of historical cash flow."""
    query = """
        SELECT
            strftime('%Y-%m', t.transaction_date) AS month,
            ROUND(SUM(CASE WHEN c.category_type = 'income' THEN t.amount ELSE 0 END), 2) AS income,
            ROUND(SUM(CASE WHEN c.category_type = 'expense' THEN ABS(t.amount) ELSE 0 END), 2) AS expenses
        FROM transactions t
        JOIN accounts a ON t.account_id = a.account_id
        JOIN categories c ON t.category_id = c.category_id
        WHERE a.user_id = ?
        GROUP BY month
        ORDER BY month
    """
    df = pd.read_sql_query(query, conn, params=[user_id])
    if df.empty:
        return df

    df["net_flow"] = df["income"] - df["expenses"]

    # Use 3-month moving average for projection
    window = min(3, len(df))
    avg_net = df["net_flow"].tail(window).mean()
    avg_income = df["income"].tail(window).mean()
    avg_expenses = df["expenses"].tail(window).mean()

    # Get current total balance
    balance_row = conn.execute(
        "SELECT SUM(current_balance) FROM accounts WHERE user_id = ?", (user_id,)
    ).fetchone()
    current_balance = balance_row[0] if balance_row[0] else 0

    projections = []
    last_month = pd.to_datetime(df["month"].iloc[-1] + "-01")
    for i in range(1, months_ahead + 1):
        proj_month = last_month + pd.DateOffset(months=i)
        projected_balance = current_balance + (avg_net * i)
        projections.append({
            "month": proj_month.strftime("%Y-%m"),
            "projected_income": round(avg_income, 2),
            "projected_expenses": round(avg_expenses, 2),
            "projected_net_flow": round(avg_net, 2),
            "projected_balance": round(projected_balance, 2),
        })

    return pd.DataFrame(projections)


def generate_insights(conn, user_id):
    """Generate automated plain-English insights about spending patterns."""
    insights = []

    # 1. Top spending category
    top_cat = pd.read_sql_query("""
        SELECT c.parent_category, ROUND(SUM(ABS(t.amount)), 2) AS total
        FROM transactions t
        JOIN accounts a ON t.account_id = a.account_id
        JOIN categories c ON t.category_id = c.category_id
        WHERE a.user_id = ? AND c.category_type = 'expense'
        GROUP BY c.parent_category
        ORDER BY total DESC LIMIT 1
    """, conn, params=[user_id])
    if not top_cat.empty:
        insights.append(
            f"Highest spending category: {top_cat.iloc[0]['parent_category']} "
            f"(${top_cat.iloc[0]['total']:,.2f} total)"
        )

    # 2. Month-over-month change for most recent month
    monthly = pd.read_sql_query("""
        SELECT strftime('%Y-%m', t.transaction_date) AS month,
               ROUND(SUM(ABS(t.amount)), 2) AS total
        FROM transactions t
        JOIN accounts a ON t.account_id = a.account_id
        JOIN categories c ON t.category_id = c.category_id
        WHERE a.user_id = ? AND c.category_type = 'expense'
        GROUP BY month ORDER BY month DESC LIMIT 2
    """, conn, params=[user_id])
    if len(monthly) == 2:
        current = monthly.iloc[0]["total"]
        previous = monthly.iloc[1]["total"]
        change_pct = ((current - previous) / previous) * 100
        direction = "increased" if change_pct > 0 else "decreased"
        insights.append(
            f"Total spending {direction} {abs(change_pct):.1f}% from "
            f"{monthly.iloc[1]['month']} to {monthly.iloc[0]['month']}"
        )

    # 3. Recurring expense burden
    recurring = pd.read_sql_query("""
        SELECT
            ROUND(SUM(CASE WHEN t.is_recurring = 1 THEN ABS(t.amount) ELSE 0 END), 2) AS recurring_total,
            ROUND(SUM(ABS(t.amount)), 2) AS total
        FROM transactions t
        JOIN accounts a ON t.account_id = a.account_id
        JOIN categories c ON t.category_id = c.category_id
        WHERE a.user_id = ? AND c.category_type = 'expense'
    """, conn, params=[user_id])
    if not recurring.empty and recurring.iloc[0]["total"] > 0:
        pct = (recurring.iloc[0]["recurring_total"] / recurring.iloc[0]["total"]) * 100
        insights.append(
            f"Recurring expenses make up {pct:.0f}% of total spending"
        )

    # 4. Average savings rate
    savings = calculate_savings_rate(conn, user_id)
    if not savings.empty:
        avg_rate = savings["savings_rate_pct"].mean()
        insights.append(f"Average monthly savings rate: {avg_rate:.1f}%")

    # 5. Budget performance
    budget_df = analyze_budget_variance(conn, user_id)
    if not budget_df.empty:
        over_count = len(budget_df[budget_df["status"] == "OVER BUDGET"])
        total_budgets = len(budget_df)
        if over_count > 0:
            insights.append(
                f"{over_count} of {total_budgets} budgeted categories are over budget this month"
            )
        else:
            insights.append("All budgeted categories are on track this month")

    # 6. Largest single transaction
    biggest = pd.read_sql_query("""
        SELECT m.merchant_name, c.category_name, ROUND(ABS(t.amount), 2) AS amount,
               t.transaction_date
        FROM transactions t
        JOIN accounts a ON t.account_id = a.account_id
        JOIN merchants m ON t.merchant_id = m.merchant_id
        JOIN categories c ON t.category_id = c.category_id
        WHERE a.user_id = ? AND c.category_type = 'expense'
        ORDER BY ABS(t.amount) DESC LIMIT 1
    """, conn, params=[user_id])
    if not biggest.empty:
        row = biggest.iloc[0]
        insights.append(
            f"Largest single expense: ${row['amount']:,.2f} at "
            f"{row['merchant_name']} ({row['category_name']}) on {row['transaction_date']}"
        )

    return insights


def export_report_data(conn, user_id, output_path):
    """Export key metrics to CSVs for use in Excel or other BI tools."""
    os.makedirs(output_path, exist_ok=True)

    # Monthly summary
    monthly = pd.read_sql_query(
        "SELECT * FROM monthly_summary WHERE user_id = ?", conn, params=[user_id]
    )
    monthly.to_csv(os.path.join(output_path, "monthly_summary.csv"), index=False)

    # Category breakdown
    category = pd.read_sql_query("SELECT * FROM category_summary", conn)
    category.to_csv(os.path.join(output_path, "category_summary.csv"), index=False)

    # Budget performance
    budget = pd.read_sql_query(
        "SELECT * FROM budget_performance WHERE user_id = ?", conn, params=[user_id]
    )
    budget.to_csv(os.path.join(output_path, "budget_performance.csv"), index=False)

    # Spending trends
    trends = get_spending_trends(conn, user_id)
    trends.to_csv(os.path.join(output_path, "spending_trends.csv"), index=False)

    print(f"  Exported 4 report files to {output_path}")
