-- ============================================================================
-- Personal Finance Analytics - Analytical Views
-- Reusable views for reporting and dashboard queries
-- ============================================================================

PRAGMA foreign_keys = ON;

-- ============================================================================
-- VIEW 1: monthly_summary
-- Aggregated monthly metrics per user: income, expenses, savings rate
-- ============================================================================
CREATE VIEW IF NOT EXISTS monthly_summary AS
SELECT
    u.user_id,
    u.first_name || ' ' || u.last_name AS full_name,
    strftime('%Y-%m', t.transaction_date) AS month,
    ROUND(SUM(CASE WHEN c.category_type = 'income' THEN t.amount ELSE 0 END), 2) AS total_income,
    ROUND(SUM(CASE WHEN c.category_type = 'expense' THEN ABS(t.amount) ELSE 0 END), 2) AS total_expenses,
    ROUND(
        SUM(CASE WHEN c.category_type = 'income' THEN t.amount ELSE 0 END) -
        SUM(CASE WHEN c.category_type = 'expense' THEN ABS(t.amount) ELSE 0 END), 2
    ) AS net_savings,
    ROUND(
        (
            (SUM(CASE WHEN c.category_type = 'income' THEN t.amount ELSE 0 END) -
             SUM(CASE WHEN c.category_type = 'expense' THEN ABS(t.amount) ELSE 0 END))
            / NULLIF(SUM(CASE WHEN c.category_type = 'income' THEN t.amount ELSE 0 END), 0)
        ) * 100, 1
    ) AS savings_rate_pct,
    COUNT(*) AS transaction_count
FROM transactions t
JOIN accounts a ON t.account_id = a.account_id
JOIN users u ON a.user_id = u.user_id
JOIN categories c ON t.category_id = c.category_id
GROUP BY u.user_id, full_name, month;


-- ============================================================================
-- VIEW 2: category_summary
-- Category-level aggregations: total, average, min, max spending
-- ============================================================================
CREATE VIEW IF NOT EXISTS category_summary AS
SELECT
    c.parent_category,
    c.category_name,
    c.category_type,
    COUNT(*) AS transaction_count,
    ROUND(SUM(ABS(t.amount)), 2) AS total_amount,
    ROUND(AVG(ABS(t.amount)), 2) AS avg_amount,
    ROUND(MIN(ABS(t.amount)), 2) AS min_amount,
    ROUND(MAX(ABS(t.amount)), 2) AS max_amount
FROM transactions t
JOIN categories c ON t.category_id = c.category_id
GROUP BY c.parent_category, c.category_name, c.category_type;


-- ============================================================================
-- VIEW 3: budget_performance
-- Budget vs actual for each user/category/month with status flags
-- ============================================================================
CREATE VIEW IF NOT EXISTS budget_performance AS
SELECT
    u.user_id,
    u.first_name || ' ' || u.last_name AS full_name,
    b.month_year,
    c.parent_category,
    c.category_name,
    ROUND(b.budget_amount, 2) AS budgeted,
    ROUND(COALESCE(actual.total_spent, 0), 2) AS actual_spent,
    ROUND(b.budget_amount - COALESCE(actual.total_spent, 0), 2) AS remaining,
    ROUND(
        (COALESCE(actual.total_spent, 0) / b.budget_amount) * 100, 1
    ) AS pct_used,
    CASE
        WHEN COALESCE(actual.total_spent, 0) > b.budget_amount THEN 'OVER BUDGET'
        WHEN COALESCE(actual.total_spent, 0) > b.budget_amount * 0.9 THEN 'AT RISK'
        ELSE 'ON TRACK'
    END AS status
FROM budgets b
JOIN users u ON b.user_id = u.user_id
JOIN categories c ON b.category_id = c.category_id
LEFT JOIN (
    SELECT
        t.category_id,
        strftime('%Y-%m', t.transaction_date) AS month,
        SUM(ABS(t.amount)) AS total_spent
    FROM transactions t
    JOIN categories c ON t.category_id = c.category_id
    WHERE c.category_type = 'expense'
    GROUP BY t.category_id, month
) actual ON actual.category_id = b.category_id AND actual.month = b.month_year;


-- ============================================================================
-- VIEW 4: account_balances_current
-- Latest balance for each account with total net worth per user
-- ============================================================================
CREATE VIEW IF NOT EXISTS account_balances_current AS
SELECT
    u.user_id,
    u.first_name || ' ' || u.last_name AS full_name,
    a.account_id,
    a.account_type,
    a.account_name,
    a.bank_name,
    ROUND(a.current_balance, 2) AS balance,
    ROUND(SUM(a.current_balance) OVER (PARTITION BY u.user_id), 2) AS total_net_worth
FROM accounts a
JOIN users u ON a.user_id = u.user_id
ORDER BY u.user_id, a.account_type;


-- ============================================================================
-- VIEW 5: transaction_enriched
-- Fully joined transaction view with all related details in one place
-- ============================================================================
CREATE VIEW IF NOT EXISTS transaction_enriched AS
SELECT
    t.transaction_id,
    t.transaction_date,
    u.user_id,
    u.first_name || ' ' || u.last_name AS full_name,
    a.account_name,
    a.account_type,
    a.bank_name,
    m.merchant_name,
    c.parent_category,
    c.category_name,
    c.category_type,
    t.amount,
    t.description,
    t.is_recurring
FROM transactions t
JOIN accounts a ON t.account_id = a.account_id
JOIN users u ON a.user_id = u.user_id
JOIN merchants m ON t.merchant_id = m.merchant_id
JOIN categories c ON t.category_id = c.category_id;
