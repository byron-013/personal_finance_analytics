"""Visualization functions for financial analytics charts."""

import os

import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns


sns.set_theme(style="whitegrid")
COLORS = sns.color_palette("Set2", 10)


def plot_spending_trends(conn, user_id, output_path):
    """Stacked area chart of monthly spending by parent category."""
    df = pd.read_sql_query("""
        SELECT strftime('%Y-%m', t.transaction_date) AS month,
               c.parent_category,
               ROUND(SUM(ABS(t.amount)), 2) AS total_spent
        FROM transactions t
        JOIN accounts a ON t.account_id = a.account_id
        JOIN categories c ON t.category_id = c.category_id
        WHERE a.user_id = ? AND c.category_type = 'expense'
        GROUP BY month, c.parent_category
        ORDER BY month
    """, conn, params=[user_id])

    if df.empty:
        return

    pivot = df.pivot_table(index="month", columns="parent_category",
                           values="total_spent", fill_value=0)

    fig, ax = plt.subplots(figsize=(12, 6))
    pivot.plot.area(ax=ax, alpha=0.7, color=COLORS[:len(pivot.columns)])
    ax.set_title("Monthly Spending by Category", fontsize=14, fontweight="bold")
    ax.set_xlabel("Month")
    ax.set_ylabel("Amount ($)")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x:,.0f}"))
    ax.legend(title="Category", bbox_to_anchor=(1.05, 1), loc="upper left")
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    fig.savefig(os.path.join(output_path, "spending_trends.png"), dpi=150)
    plt.close(fig)
    print("  Saved spending_trends.png")


def plot_budget_variance(conn, user_id, output_path):
    """Horizontal bar chart comparing actual spending to budget."""
    df = pd.read_sql_query("""
        SELECT * FROM budget_performance
        WHERE user_id = ? AND month_year = (
            SELECT MAX(month_year) FROM budget_performance WHERE user_id = ?
        )
    """, conn, params=[user_id, user_id])

    if df.empty:
        return

    fig, ax = plt.subplots(figsize=(10, 6))
    y_pos = range(len(df))
    bars_budget = ax.barh(y_pos, df["budgeted"], height=0.35, label="Budget",
                          color="#90CAF9", alpha=0.8)
    bars_actual = ax.barh([y + 0.35 for y in y_pos], df["actual_spent"],
                          height=0.35, label="Actual", alpha=0.8,
                          color=["#EF5350" if s == "OVER BUDGET" else "#66BB6A"
                                 for s in df["status"]])
    ax.set_yticks([y + 0.175 for y in y_pos])
    ax.set_yticklabels(df["category_name"])
    ax.set_xlabel("Amount ($)")
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x:,.0f}"))
    ax.set_title(f"Budget vs Actual ({df.iloc[0]['month_year']})",
                 fontsize=14, fontweight="bold")
    ax.legend()
    plt.tight_layout()
    fig.savefig(os.path.join(output_path, "budget_variance.png"), dpi=150)
    plt.close(fig)
    print("  Saved budget_variance.png")


def plot_category_breakdown(conn, user_id, output_path):
    """Pie chart of spending distribution by parent category."""
    df = pd.read_sql_query("""
        SELECT c.parent_category,
               ROUND(SUM(ABS(t.amount)), 2) AS total_spent
        FROM transactions t
        JOIN accounts a ON t.account_id = a.account_id
        JOIN categories c ON t.category_id = c.category_id
        WHERE a.user_id = ? AND c.category_type = 'expense'
        GROUP BY c.parent_category
        ORDER BY total_spent DESC
    """, conn, params=[user_id])

    if df.empty:
        return

    fig, ax = plt.subplots(figsize=(8, 8))
    wedges, texts, autotexts = ax.pie(
        df["total_spent"], labels=df["parent_category"],
        autopct="%1.1f%%", colors=COLORS[:len(df)],
        pctdistance=0.85, startangle=90
    )
    for t in autotexts:
        t.set_fontsize(9)
    ax.set_title("Spending Distribution by Category", fontsize=14, fontweight="bold")
    plt.tight_layout()
    fig.savefig(os.path.join(output_path, "category_breakdown.png"), dpi=150)
    plt.close(fig)
    print("  Saved category_breakdown.png")


def plot_income_vs_expenses(conn, user_id, output_path):
    """Grouped bar chart of monthly income vs expenses with savings line."""
    df = pd.read_sql_query("""
        SELECT * FROM monthly_summary WHERE user_id = ? ORDER BY month
    """, conn, params=[user_id])

    if df.empty:
        return

    fig, ax = plt.subplots(figsize=(12, 6))
    x = range(len(df))
    width = 0.35
    ax.bar([i - width / 2 for i in x], df["total_income"], width,
           label="Income", color="#66BB6A", alpha=0.8)
    ax.bar([i + width / 2 for i in x], df["total_expenses"], width,
           label="Expenses", color="#EF5350", alpha=0.8)
    ax.plot(x, df["net_savings"], "o-", color="#1565C0", linewidth=2,
            label="Net Savings", markersize=5)
    ax.axhline(y=0, color="gray", linestyle="--", alpha=0.5)
    ax.set_xticks(x)
    ax.set_xticklabels(df["month"], rotation=45, ha="right")
    ax.set_ylabel("Amount ($)")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x:,.0f}"))
    ax.set_title("Income vs Expenses", fontsize=14, fontweight="bold")
    ax.legend()
    plt.tight_layout()
    fig.savefig(os.path.join(output_path, "income_vs_expenses.png"), dpi=150)
    plt.close(fig)
    print("  Saved income_vs_expenses.png")


def plot_savings_rate_trend(conn, user_id, output_path):
    """Line chart of savings rate over time with 20% benchmark."""
    df = pd.read_sql_query("""
        SELECT * FROM monthly_summary WHERE user_id = ? ORDER BY month
    """, conn, params=[user_id])

    if df.empty:
        return

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.fill_between(range(len(df)), df["savings_rate_pct"], alpha=0.3, color="#1565C0")
    ax.plot(range(len(df)), df["savings_rate_pct"], "o-", color="#1565C0",
            linewidth=2, label="Savings Rate")
    ax.axhline(y=20, color="#FF9800", linestyle="--", linewidth=1.5,
               label="20% Benchmark")
    ax.axhline(y=0, color="gray", linestyle="-", alpha=0.3)
    ax.set_xticks(range(len(df)))
    ax.set_xticklabels(df["month"], rotation=45, ha="right")
    ax.set_ylabel("Savings Rate (%)")
    ax.set_title("Monthly Savings Rate", fontsize=14, fontweight="bold")
    ax.legend()
    plt.tight_layout()
    fig.savefig(os.path.join(output_path, "savings_rate.png"), dpi=150)
    plt.close(fig)
    print("  Saved savings_rate.png")


def plot_top_merchants(conn, user_id, output_path):
    """Horizontal bar chart of top 15 merchants by total spend."""
    df = pd.read_sql_query("""
        SELECT m.merchant_name,
               ROUND(SUM(ABS(t.amount)), 2) AS total_spent
        FROM transactions t
        JOIN accounts a ON t.account_id = a.account_id
        JOIN merchants m ON t.merchant_id = m.merchant_id
        JOIN categories c ON t.category_id = c.category_id
        WHERE a.user_id = ? AND c.category_type = 'expense'
        GROUP BY m.merchant_name
        ORDER BY total_spent DESC
        LIMIT 15
    """, conn, params=[user_id])

    if df.empty:
        return

    fig, ax = plt.subplots(figsize=(10, 7))
    df_sorted = df.sort_values("total_spent")
    ax.barh(df_sorted["merchant_name"], df_sorted["total_spent"],
            color=COLORS[0], alpha=0.8)
    ax.set_xlabel("Total Spent ($)")
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x:,.0f}"))
    ax.set_title("Top 15 Merchants by Spending", fontsize=14, fontweight="bold")
    plt.tight_layout()
    fig.savefig(os.path.join(output_path, "top_merchants.png"), dpi=150)
    plt.close(fig)
    print("  Saved top_merchants.png")


def generate_all_charts(conn, user_id, output_path):
    """Generate all visualization charts for a user."""
    os.makedirs(output_path, exist_ok=True)
    plot_spending_trends(conn, user_id, output_path)
    plot_budget_variance(conn, user_id, output_path)
    plot_category_breakdown(conn, user_id, output_path)
    plot_income_vs_expenses(conn, user_id, output_path)
    plot_savings_rate_trend(conn, user_id, output_path)
    plot_top_merchants(conn, user_id, output_path)
