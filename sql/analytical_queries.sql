-- ============================================================================
-- Personal Finance Analytics - Analytical Query Library
-- 10 queries demonstrating SQL skills for BI/analyst roles
-- ============================================================================

-- ============================================================================
-- QUERY 1: Monthly Spending by Category
-- Business Question: How does spending break down by category each month?
-- Use Case: Identify spending trends and seasonal patterns
-- ============================================================================
SELECT
    strftime('%Y-%m', t.transaction_date) AS month,
    c.parent_category,
    c.category_name,
    COUNT(*) AS transaction_count,
    ROUND(SUM(ABS(t.amount)), 2) AS total_spent,
    ROUND(AVG(ABS(t.amount)), 2) AS avg_transaction
FROM transactions t
JOIN categories c ON t.category_id = c.category_id
WHERE c.category_type = 'expense'
GROUP BY month, c.parent_category, c.category_name
ORDER BY month, total_spent DESC;


-- ============================================================================
-- QUERY 2: Budget vs Actual Variance
-- Business Question: Which categories are over or under budget?
-- Use Case: Budget monitoring and financial discipline tracking
-- ============================================================================
SELECT
    b.month_year,
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
GROUP BY b.budget_id, b.month_year, c.parent_category, c.category_name, b.budget_amount
ORDER BY b.month_year DESC, pct_used DESC;


-- ============================================================================
-- QUERY 3: Top 10 Merchants by Total Spend
-- Business Question: Where is the most money being spent?
-- Use Case: Identify major expense drivers and negotiation opportunities
-- ============================================================================
SELECT
    m.merchant_name,
    c.parent_category,
    c.category_name,
    COUNT(*) AS transaction_count,
    ROUND(SUM(ABS(t.amount)), 2) AS total_spent,
    ROUND(AVG(ABS(t.amount)), 2) AS avg_amount,
    ROUND(MIN(ABS(t.amount)), 2) AS min_amount,
    ROUND(MAX(ABS(t.amount)), 2) AS max_amount
FROM transactions t
JOIN merchants m ON t.merchant_id = m.merchant_id
JOIN categories c ON t.category_id = c.category_id
WHERE c.category_type = 'expense'
GROUP BY m.merchant_id, m.merchant_name, c.parent_category, c.category_name
ORDER BY total_spent DESC
LIMIT 10;


-- ============================================================================
-- QUERY 4: Recurring Transaction Identification
-- Business Question: What are the fixed monthly costs?
-- Use Case: Understand committed expenses and find cancellation opportunities
-- ============================================================================
SELECT
    m.merchant_name,
    c.parent_category,
    c.category_name,
    COUNT(*) AS months_charged,
    ROUND(AVG(ABS(t.amount)), 2) AS avg_monthly_cost,
    ROUND(SUM(ABS(t.amount)), 2) AS total_cost,
    MIN(t.transaction_date) AS first_charge,
    MAX(t.transaction_date) AS last_charge
FROM transactions t
JOIN merchants m ON t.merchant_id = m.merchant_id
JOIN categories c ON t.category_id = c.category_id
WHERE t.is_recurring = 1
    AND c.category_type = 'expense'
GROUP BY m.merchant_id, m.merchant_name, c.parent_category, c.category_name
ORDER BY avg_monthly_cost DESC;


-- ============================================================================
-- QUERY 5: Month-over-Month Spending Growth
-- Business Question: How is spending changing month to month?
-- Use Case: Detect spending creep and category-level trend shifts
-- ============================================================================
WITH monthly_spending AS (
    SELECT
        strftime('%Y-%m', t.transaction_date) AS month,
        c.parent_category,
        ROUND(SUM(ABS(t.amount)), 2) AS total_spent
    FROM transactions t
    JOIN categories c ON t.category_id = c.category_id
    WHERE c.category_type = 'expense'
    GROUP BY month, c.parent_category
)
SELECT
    ms.month,
    ms.parent_category,
    ms.total_spent AS current_month,
    LAG(ms.total_spent) OVER (
        PARTITION BY ms.parent_category ORDER BY ms.month
    ) AS previous_month,
    ROUND(
        ms.total_spent - LAG(ms.total_spent) OVER (
            PARTITION BY ms.parent_category ORDER BY ms.month
        ), 2
    ) AS change_amount,
    ROUND(
        ((ms.total_spent - LAG(ms.total_spent) OVER (
            PARTITION BY ms.parent_category ORDER BY ms.month
        )) / LAG(ms.total_spent) OVER (
            PARTITION BY ms.parent_category ORDER BY ms.month
        )) * 100, 1
    ) AS change_pct
FROM monthly_spending ms
ORDER BY ms.month DESC, change_pct DESC;


-- ============================================================================
-- QUERY 6: Cash Flow Analysis
-- Business Question: What is the net cash flow and cumulative savings trend?
-- Use Case: Assess overall financial health and savings trajectory
-- ============================================================================
WITH monthly_flows AS (
    SELECT
        strftime('%Y-%m', t.transaction_date) AS month,
        ROUND(SUM(CASE WHEN c.category_type = 'income' THEN t.amount ELSE 0 END), 2) AS total_income,
        ROUND(SUM(CASE WHEN c.category_type = 'expense' THEN ABS(t.amount) ELSE 0 END), 2) AS total_expenses
    FROM transactions t
    JOIN categories c ON t.category_id = c.category_id
    GROUP BY month
)
SELECT
    month,
    total_income,
    total_expenses,
    ROUND(total_income - total_expenses, 2) AS net_cash_flow,
    ROUND(
        SUM(total_income - total_expenses) OVER (ORDER BY month), 2
    ) AS cumulative_savings,
    ROUND(
        ((total_income - total_expenses) / NULLIF(total_income, 0)) * 100, 1
    ) AS savings_rate_pct
FROM monthly_flows
ORDER BY month;


-- ============================================================================
-- QUERY 7: Category Spending Distribution
-- Business Question: What percentage of total spending goes to each category?
-- Use Case: Understand spending priorities and compare to recommended budgets
-- ============================================================================
WITH total AS (
    SELECT SUM(ABS(t.amount)) AS grand_total
    FROM transactions t
    JOIN categories c ON t.category_id = c.category_id
    WHERE c.category_type = 'expense'
)
SELECT
    c.parent_category,
    ROUND(SUM(ABS(t.amount)), 2) AS category_total,
    ROUND(
        (SUM(ABS(t.amount)) / total.grand_total) * 100, 1
    ) AS pct_of_total,
    COUNT(*) AS transaction_count
FROM transactions t
JOIN categories c ON t.category_id = c.category_id
CROSS JOIN total
WHERE c.category_type = 'expense'
GROUP BY c.parent_category, total.grand_total
ORDER BY pct_of_total DESC;


-- ============================================================================
-- QUERY 8: Year-over-Year Comparison by Quarter
-- Business Question: How does spending compare across equivalent time periods?
-- Use Case: Identify long-term trends beyond monthly fluctuations
-- ============================================================================
WITH quarterly AS (
    SELECT
        strftime('%Y', t.transaction_date) AS year,
        CASE
            WHEN CAST(strftime('%m', t.transaction_date) AS INTEGER) BETWEEN 1 AND 3 THEN 'Q1'
            WHEN CAST(strftime('%m', t.transaction_date) AS INTEGER) BETWEEN 4 AND 6 THEN 'Q2'
            WHEN CAST(strftime('%m', t.transaction_date) AS INTEGER) BETWEEN 7 AND 9 THEN 'Q3'
            ELSE 'Q4'
        END AS quarter,
        c.parent_category,
        ROUND(SUM(ABS(t.amount)), 2) AS total_spent
    FROM transactions t
    JOIN categories c ON t.category_id = c.category_id
    WHERE c.category_type = 'expense'
    GROUP BY year, quarter, c.parent_category
)
SELECT
    year,
    quarter,
    parent_category,
    total_spent,
    LAG(total_spent) OVER (
        PARTITION BY quarter, parent_category ORDER BY year
    ) AS prev_year_same_quarter,
    ROUND(
        total_spent - LAG(total_spent) OVER (
            PARTITION BY quarter, parent_category ORDER BY year
        ), 2
    ) AS yoy_change
FROM quarterly
ORDER BY year DESC, quarter, parent_category;


-- ============================================================================
-- QUERY 9: Account Balance Projection
-- Business Question: What will account balances look like in 30/60/90 days?
-- Use Case: Cash flow planning and avoiding overdrafts
-- ============================================================================
WITH monthly_net AS (
    SELECT
        a.account_id,
        a.account_name,
        a.current_balance,
        ROUND(AVG(
            CASE WHEN c.category_type = 'income' THEN t.amount
                 WHEN c.category_type = 'expense' THEN t.amount
                 ELSE 0 END
        ) * 30, 2) AS avg_monthly_net
    FROM accounts a
    JOIN transactions t ON a.account_id = t.account_id
    JOIN categories c ON t.category_id = c.category_id
    GROUP BY a.account_id, a.account_name, a.current_balance
)
SELECT
    account_name,
    ROUND(current_balance, 2) AS current_balance,
    ROUND(avg_monthly_net, 2) AS avg_monthly_net_flow,
    ROUND(current_balance + avg_monthly_net, 2) AS projected_30_days,
    ROUND(current_balance + (avg_monthly_net * 2), 2) AS projected_60_days,
    ROUND(current_balance + (avg_monthly_net * 3), 2) AS projected_90_days
FROM monthly_net
ORDER BY current_balance DESC;


-- ============================================================================
-- QUERY 10: Anomaly Detection
-- Business Question: Which transactions are unusually large for their category?
-- Use Case: Identify potential errors, fraud, or one-time unusual expenses
-- ============================================================================
WITH category_stats AS (
    SELECT
        c.category_id,
        c.category_name,
        c.parent_category,
        AVG(ABS(t.amount)) AS avg_amount,
        -- Manual std dev: sqrt(avg(x^2) - avg(x)^2)
        AVG(ABS(t.amount)) + 2.0 * SQRT(
            AVG(ABS(t.amount) * ABS(t.amount)) - AVG(ABS(t.amount)) * AVG(ABS(t.amount))
        ) AS upper_threshold
    FROM transactions t
    JOIN categories c ON t.category_id = c.category_id
    WHERE c.category_type = 'expense'
    GROUP BY c.category_id, c.category_name, c.parent_category
    HAVING COUNT(*) >= 3
)
SELECT
    t.transaction_date,
    m.merchant_name,
    cs.parent_category,
    cs.category_name,
    ROUND(ABS(t.amount), 2) AS amount,
    ROUND(cs.avg_amount, 2) AS category_avg,
    ROUND(ABS(t.amount) / cs.avg_amount, 1) AS times_avg,
    t.description
FROM transactions t
JOIN category_stats cs ON t.category_id = cs.category_id
JOIN merchants m ON t.merchant_id = m.merchant_id
WHERE ABS(t.amount) > cs.upper_threshold
ORDER BY times_avg DESC;
