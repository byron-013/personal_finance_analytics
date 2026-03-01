"""Streamlit dashboard for Personal Finance Analytics."""

import os
import sqlite3

import pandas as pd
import streamlit as st

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "data", "synthetic", "finance.db")


@st.cache_resource
def get_connection():
    """Return a shared SQLite connection (read-only)."""
    if not os.path.exists(DB_PATH):
        return None
    return sqlite3.connect(DB_PATH, check_same_thread=False)


def load_users(conn):
    return pd.read_sql_query(
        "SELECT user_id, first_name || ' ' || last_name AS name, annual_income FROM users",
        conn,
    )


def main():
    st.set_page_config(page_title="Personal Finance Dashboard", layout="wide")
    st.title("Personal Finance Analytics Dashboard")

    conn = get_connection()
    if conn is None:
        st.error(
            "Database not found. Run `python main.py --state CA` first to generate data."
        )
        return

    users_df = load_users(conn)
    if users_df.empty:
        st.warning("No users found in the database.")
        return

    # ── Sidebar: user picker ──
    st.sidebar.header("Filters")
    user_names = users_df["name"].tolist()
    selected_name = st.sidebar.selectbox("Select User", user_names)
    user_row = users_df[users_df["name"] == selected_name].iloc[0]
    user_id = int(user_row["user_id"])

    st.sidebar.markdown("---")
    st.sidebar.metric("Annual Gross Income", f"${user_row['annual_income']:,.0f}")

    # ── Top KPIs ──
    monthly = pd.read_sql_query(
        "SELECT * FROM monthly_summary WHERE user_id = ? ORDER BY month",
        conn,
        params=[user_id],
    )

    if not monthly.empty:
        latest = monthly.iloc[-1]
        prev = monthly.iloc[-2] if len(monthly) > 1 else None

        c1, c2, c3, c4 = st.columns(4)
        c1.metric(
            "Monthly Income",
            f"${latest['total_income']:,.0f}",
            delta=f"${latest['total_income'] - prev['total_income']:,.0f}" if prev is not None else None,
        )
        c2.metric(
            "Monthly Expenses",
            f"${latest['total_expenses']:,.0f}",
            delta=f"${latest['total_expenses'] - prev['total_expenses']:,.0f}" if prev is not None else None,
            delta_color="inverse",
        )
        c3.metric(
            "Net Savings",
            f"${latest['net_savings']:,.0f}",
            delta=f"${latest['net_savings'] - prev['net_savings']:,.0f}" if prev is not None else None,
        )
        c4.metric(
            "Savings Rate",
            f"{latest['savings_rate_pct']:.1f}%",
            delta=f"{latest['savings_rate_pct'] - prev['savings_rate_pct']:.1f}pp" if prev is not None else None,
        )

    # ── Tabs ──
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Monthly Overview",
        "Budget vs Actual",
        "Top Merchants",
        "Category Breakdown",
        "Cash Flow Forecast",
    ])

    # ── Tab 1: Monthly Overview (income, expenses, savings rate) ──
    with tab1:
        if not monthly.empty:
            st.subheader("Monthly Income vs Expenses")
            chart_df = monthly[["month", "total_income", "total_expenses", "net_savings"]].set_index("month")
            st.bar_chart(chart_df[["total_income", "total_expenses"]])

            st.subheader("Monthly Savings Rate")
            sr_df = monthly[["month", "savings_rate_pct"]].set_index("month")
            st.line_chart(sr_df)

            st.subheader("Monthly Detail")
            display_df = monthly[["month", "total_income", "total_expenses", "net_savings", "savings_rate_pct"]].copy()
            display_df.columns = ["Month", "Income", "Expenses", "Net Savings", "Savings Rate %"]
            st.dataframe(
                display_df.style.format({
                    "Income": "${:,.2f}",
                    "Expenses": "${:,.2f}",
                    "Net Savings": "${:,.2f}",
                    "Savings Rate %": "{:.1f}%",
                }),
                use_container_width=True,
                hide_index=True,
            )

    # ── Tab 2: Budget vs Actual ──
    with tab2:
        budget = pd.read_sql_query(
            "SELECT * FROM budget_performance WHERE user_id = ? ORDER BY month_year DESC",
            conn,
            params=[user_id],
        )
        if budget.empty:
            st.info("No budget data available.")
        else:
            months_available = sorted(budget["month_year"].unique(), reverse=True)
            sel_month = st.selectbox("Budget Month", months_available)
            bm = budget[budget["month_year"] == sel_month][
                ["parent_category", "category_name", "budgeted", "actual_spent", "remaining", "pct_used", "status"]
            ]
            st.dataframe(
                bm.style
                .format({"budgeted": "${:,.2f}", "actual_spent": "${:,.2f}", "remaining": "${:,.2f}", "pct_used": "{:.1f}%"})
                .applymap(
                    lambda v: "background-color: #ffcdd2" if v == "OVER BUDGET"
                    else ("background-color: #fff9c4" if v == "AT RISK" else ""),
                    subset=["status"],
                ),
                use_container_width=True,
                hide_index=True,
            )

    # ── Tab 3: Top Merchants ──
    with tab3:
        merchants = pd.read_sql_query("""
            SELECT m.merchant_name AS Merchant, c.parent_category AS Category,
                   COUNT(*) AS Transactions,
                   ROUND(SUM(ABS(t.amount)), 2) AS "Total Spent"
            FROM transactions t
            JOIN accounts a ON t.account_id = a.account_id
            JOIN merchants m ON t.merchant_id = m.merchant_id
            JOIN categories c ON t.category_id = c.category_id
            WHERE a.user_id = ? AND c.category_type = 'expense'
            GROUP BY m.merchant_name, c.parent_category
            ORDER BY "Total Spent" DESC
            LIMIT 20
        """, conn, params=[user_id])

        if merchants.empty:
            st.info("No merchant data available.")
        else:
            st.subheader("Top 20 Merchants by Spend")
            st.dataframe(
                merchants.style.format({"Total Spent": "${:,.2f}"}),
                use_container_width=True,
                hide_index=True,
            )
            st.bar_chart(merchants.set_index("Merchant")["Total Spent"])

    # ── Tab 4: Category Breakdown ──
    with tab4:
        cat_pct = pd.read_sql_query("""
            SELECT c.parent_category AS Category,
                   ROUND(SUM(ABS(t.amount)), 2) AS "Total Spent",
                   ROUND(SUM(ABS(t.amount)) * 100.0 /
                         (SELECT SUM(ABS(t2.amount))
                          FROM transactions t2
                          JOIN accounts a2 ON t2.account_id = a2.account_id
                          JOIN categories c2 ON t2.category_id = c2.category_id
                          WHERE a2.user_id = ? AND c2.category_type = 'expense'), 1
                   ) AS "% of Total"
            FROM transactions t
            JOIN accounts a ON t.account_id = a.account_id
            JOIN categories c ON t.category_id = c.category_id
            WHERE a.user_id = ? AND c.category_type = 'expense'
            GROUP BY c.parent_category
            ORDER BY "Total Spent" DESC
        """, conn, params=[user_id, user_id])

        if cat_pct.empty:
            st.info("No category data available.")
        else:
            st.subheader("Spending by Category")
            col_a, col_b = st.columns(2)
            with col_a:
                st.dataframe(
                    cat_pct.style.format({"Total Spent": "${:,.2f}", "% of Total": "{:.1f}%"}),
                    use_container_width=True,
                    hide_index=True,
                )
            with col_b:
                st.bar_chart(cat_pct.set_index("Category")["% of Total"])

    # ── Tab 5: Cash Flow Forecast ──
    with tab5:
        from src.analytics import forecast_cash_flow
        forecast = forecast_cash_flow(conn, user_id)
        if forecast.empty:
            st.info("Not enough data to generate forecast.")
        else:
            st.subheader("30 / 60 / 90 Day Balance Projection")
            st.dataframe(
                forecast.style.format({
                    "projected_income": "${:,.2f}",
                    "projected_expenses": "${:,.2f}",
                    "projected_net_flow": "${:,.2f}",
                    "projected_balance": "${:,.2f}",
                }),
                use_container_width=True,
                hide_index=True,
            )
            st.line_chart(forecast.set_index("month")["projected_balance"])

    # ── Sidebar: Income Summary ──
    st.sidebar.markdown("---")
    st.sidebar.subheader("All Users — Income Summary")
    st.sidebar.dataframe(
        users_df[["name", "annual_income"]].rename(
            columns={"name": "User", "annual_income": "Annual Gross"}
        ).style.format({"Annual Gross": "${:,.0f}"}),
        hide_index=True,
    )


if __name__ == "__main__":
    main()
