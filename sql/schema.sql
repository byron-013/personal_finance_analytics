-- ============================================================================
-- Personal Finance Analytics - Database Schema
-- Normalized to 3NF with full referential integrity
-- ============================================================================

PRAGMA foreign_keys = ON;

-- Users table
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    date_joined DATE NOT NULL,
    annual_income REAL NOT NULL
);

-- Bank/credit accounts linked to users
CREATE TABLE IF NOT EXISTS accounts (
    account_id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    account_type TEXT NOT NULL CHECK (account_type IN ('checking', 'savings', 'credit_card')),
    account_name TEXT NOT NULL,
    bank_name TEXT NOT NULL,
    current_balance REAL NOT NULL,
    created_date DATE NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

-- Spending/income categories with parent-child hierarchy
CREATE TABLE IF NOT EXISTS categories (
    category_id INTEGER PRIMARY KEY,
    category_name TEXT UNIQUE NOT NULL,
    parent_category TEXT,
    category_type TEXT NOT NULL CHECK (category_type IN ('expense', 'income'))
);

-- Merchants mapped to categories
CREATE TABLE IF NOT EXISTS merchants (
    merchant_id INTEGER PRIMARY KEY,
    merchant_name TEXT NOT NULL,
    category_id INTEGER NOT NULL,
    is_recurring BOOLEAN NOT NULL DEFAULT 0,
    FOREIGN KEY (category_id) REFERENCES categories(category_id)
);

-- Financial transactions
CREATE TABLE IF NOT EXISTS transactions (
    transaction_id INTEGER PRIMARY KEY,
    account_id INTEGER NOT NULL,
    merchant_id INTEGER NOT NULL,
    category_id INTEGER NOT NULL,
    transaction_date DATE NOT NULL,
    amount REAL NOT NULL,
    description TEXT,
    is_recurring BOOLEAN NOT NULL DEFAULT 0,
    FOREIGN KEY (account_id) REFERENCES accounts(account_id),
    FOREIGN KEY (merchant_id) REFERENCES merchants(merchant_id),
    FOREIGN KEY (category_id) REFERENCES categories(category_id)
);

-- Monthly budgets per user per category
CREATE TABLE IF NOT EXISTS budgets (
    budget_id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    category_id INTEGER NOT NULL,
    month_year TEXT NOT NULL,
    budget_amount REAL NOT NULL,
    notes TEXT,
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (category_id) REFERENCES categories(category_id)
);

-- Financial goals per user
CREATE TABLE IF NOT EXISTS financial_goals (
    goal_id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    goal_name TEXT NOT NULL,
    target_amount REAL NOT NULL,
    current_amount REAL NOT NULL DEFAULT 0,
    target_date DATE NOT NULL,
    category TEXT NOT NULL CHECK (category IN ('savings', 'debt_payoff', 'investment')),
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);
