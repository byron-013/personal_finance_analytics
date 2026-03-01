"""Synthetic financial data generation using Faker."""

import json
import os
import random
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
from faker import Faker

fake = Faker()
Faker.seed(42)
random.seed(42)
np.random.seed(42)

# Realistic amount ranges per subcategory
AMOUNT_RANGES = {
    # Housing
    "Rent": (1200, 2500),
    "Mortgage": (1500, 3000),
    "Property Tax": (200, 500),
    "Home Insurance": (100, 250),
    "HOA Fees": (150, 400),
    # Transportation
    "Gasoline": (30, 70),
    "Car Payment": (250, 600),
    "Auto Insurance": (100, 250),
    "Public Transit": (50, 150),
    "Parking": (10, 40),
    # Food
    "Groceries": (50, 200),
    "Restaurants": (20, 80),
    "Coffee Shops": (3, 8),
    "Fast Food": (7, 18),
    # Utilities
    "Electric": (60, 180),
    "Water": (30, 70),
    "Natural Gas": (40, 120),
    "Internet": (50, 100),
    "Phone": (40, 100),
    # Healthcare
    "Health Insurance": (200, 500),
    "Prescriptions": (10, 80),
    "Doctor Visits": (50, 300),
    "Dental": (75, 250),
    # Entertainment
    "Streaming Services": (10, 20),
    "Movies": (12, 30),
    "Concerts": (40, 150),
    "Hobbies": (15, 80),
    # Shopping
    "Clothing": (20, 150),
    "Electronics": (30, 500),
    "Home Goods": (15, 100),
    "Personal Care": (10, 50),
    # Financial
    "Credit Card Payment": (100, 500),
    "Loan Payment": (200, 600),
    "Investment Contribution": (100, 1000),
    # Income
    "Salary": (3000, 8000),
    "Bonus": (1000, 5000),
    "Freelance": (200, 2000),
    "Interest": (5, 50),
    "Dividends": (50, 300),
    "Rental Income": (800, 2000),
}

# Categories that recur monthly
RECURRING_SUBCATEGORIES = {
    "Rent", "Mortgage", "Property Tax", "Home Insurance", "HOA Fees",
    "Car Payment", "Auto Insurance", "Health Insurance",
    "Electric", "Water", "Natural Gas", "Internet", "Phone",
    "Streaming Services",
    "Credit Card Payment", "Loan Payment", "Investment Contribution",
    "Salary",
}

# Merchant name templates by subcategory
MERCHANT_TEMPLATES = {
    "Rent": ["Property Management Co", "Apartment Living LLC"],
    "Mortgage": ["National Mortgage Corp", "HomeFirst Lending"],
    "Property Tax": ["County Tax Office"],
    "Home Insurance": ["State Farm", "Allstate Home"],
    "HOA Fees": ["Community HOA"],
    "Gasoline": ["Shell", "Chevron", "BP", "ExxonMobil"],
    "Car Payment": ["Toyota Financial", "Honda Financial", "Ford Credit"],
    "Auto Insurance": ["GEICO", "Progressive", "State Farm Auto"],
    "Public Transit": ["Metro Transit", "City Bus Authority"],
    "Parking": ["ParkMobile", "SpotHero"],
    "Groceries": ["Kroger", "Whole Foods", "Trader Joe's", "Walmart", "Safeway", "Aldi"],
    "Restaurants": None,  # will use Faker
    "Coffee Shops": ["Starbucks", "Dunkin'", "Peet's Coffee", "Local Brew"],
    "Fast Food": ["McDonald's", "Chick-fil-A", "Chipotle", "Subway", "Wendy's"],
    "Electric": ["City Electric Utility", "Power & Light Co"],
    "Water": ["Municipal Water", "City Water Dept"],
    "Natural Gas": ["City Gas Company", "National Gas Utility"],
    "Internet": ["Comcast Xfinity", "AT&T Internet", "Spectrum"],
    "Phone": ["Verizon Wireless", "T-Mobile", "AT&T Wireless"],
    "Health Insurance": ["Blue Cross Blue Shield", "UnitedHealthcare", "Aetna"],
    "Prescriptions": ["CVS Pharmacy", "Walgreens", "Rite Aid"],
    "Doctor Visits": ["Primary Care Associates", "City Medical Group"],
    "Dental": ["Bright Smile Dental", "Family Dentistry"],
    "Streaming Services": ["Netflix", "Spotify", "Hulu", "Disney+", "HBO Max"],
    "Movies": ["AMC Theatres", "Regal Cinemas"],
    "Concerts": ["Ticketmaster", "Live Nation", "StubHub"],
    "Hobbies": None,
    "Clothing": ["Target", "H&M", "Nordstrom", "Old Navy", "Nike"],
    "Electronics": ["Best Buy", "Amazon", "Apple Store"],
    "Home Goods": ["Target Home", "IKEA", "Bed Bath & Beyond", "HomeDepot"],
    "Personal Care": ["Ulta Beauty", "Bath & Body Works", "Target Beauty"],
    "Credit Card Payment": ["Visa Payment", "Mastercard Payment", "Amex Payment"],
    "Loan Payment": ["Student Loan Corp", "LendingClub"],
    "Investment Contribution": ["Vanguard", "Fidelity", "Charles Schwab"],
    "Salary": ["Employer Direct Deposit"],
    "Bonus": ["Employer Bonus"],
    "Freelance": None,
    "Interest": ["Bank Interest"],
    "Dividends": ["Investment Dividends"],
    "Rental Income": ["Tenant Payment"],
}


def generate_users(num_users=3):
    """Generate realistic user profiles."""
    users = []
    for i in range(1, num_users + 1):
        users.append({
            "user_id": i,
            "first_name": fake.first_name(),
            "last_name": fake.last_name(),
            "email": fake.email(),
            "date_joined": fake.date_between(start_date="-3y", end_date="-1y").isoformat(),
            "annual_income": round(random.uniform(40000, 150000), 2),
        })
    return pd.DataFrame(users)


def generate_categories(config_path):
    """Load categories from config and build category records with parent-child relationships."""
    with open(config_path, "r") as f:
        config = json.load(f)

    categories = []
    cat_id = 1

    for parent, subcats in config["expense_categories"].items():
        for sub in subcats:
            categories.append({
                "category_id": cat_id,
                "category_name": sub,
                "parent_category": parent,
                "category_type": "expense",
            })
            cat_id += 1

    for parent, subcats in config["income_categories"].items():
        for sub in subcats:
            categories.append({
                "category_id": cat_id,
                "category_name": sub,
                "parent_category": parent,
                "category_type": "income",
            })
            cat_id += 1

    return pd.DataFrame(categories)


def generate_merchants(categories_df, num_merchants=100):
    """Create merchants assigned to appropriate categories."""
    merchants = []
    merchant_id = 1

    for _, cat in categories_df.iterrows():
        sub = cat["category_name"]
        templates = MERCHANT_TEMPLATES.get(sub)
        is_recurring = sub in RECURRING_SUBCATEGORIES

        if templates is None:
            # Generate random merchant names
            count = random.randint(2, 4)
            for _ in range(count):
                merchants.append({
                    "merchant_id": merchant_id,
                    "merchant_name": fake.company(),
                    "category_id": cat["category_id"],
                    "is_recurring": is_recurring,
                })
                merchant_id += 1
        else:
            for name in templates:
                merchants.append({
                    "merchant_id": merchant_id,
                    "merchant_name": name,
                    "category_id": cat["category_id"],
                    "is_recurring": is_recurring,
                })
                merchant_id += 1

    return pd.DataFrame(merchants)


def generate_accounts(users_df):
    """Create 2-4 bank/credit accounts per user."""
    accounts = []
    account_id = 1

    account_templates = [
        ("checking", "Primary Checking", 1500, 8000),
        ("savings", "Savings Account", 2000, 25000),
        ("credit_card", "Rewards Credit Card", -3000, 0),
        ("checking", "Secondary Checking", 500, 3000),
    ]

    bank_names = ["Chase", "Bank of America", "Wells Fargo", "Capital One", "Citi"]

    for _, user in users_df.iterrows():
        num_accounts = random.randint(2, 4)
        selected = random.sample(account_templates, num_accounts)
        for acct_type, acct_name, bal_low, bal_high in selected:
            accounts.append({
                "account_id": account_id,
                "user_id": user["user_id"],
                "account_type": acct_type,
                "account_name": acct_name,
                "bank_name": random.choice(bank_names),
                "current_balance": round(random.uniform(bal_low, bal_high), 2),
                "created_date": user["date_joined"],
            })
            account_id += 1

    return pd.DataFrame(accounts)


def generate_transactions(accounts_df, merchants_df, categories_df, months=12):
    """Generate 12 months of realistic transactions with recurring, weekly, and random patterns."""
    transactions = []
    txn_id = 1
    today = datetime.now().date()
    start_date = today.replace(day=1) - timedelta(days=months * 30)

    # Build lookups
    expense_cats = categories_df[categories_df["category_type"] == "expense"]
    income_cats = categories_df[categories_df["category_type"] == "income"]

    for _, account in accounts_df.iterrows():
        user_accounts = accounts_df[accounts_df["user_id"] == account["user_id"]]
        # Only generate from one account per user to avoid duplication
        if account["account_id"] != user_accounts.iloc[0]["account_id"]:
            continue

        for month_offset in range(months):
            month_start = start_date + timedelta(days=month_offset * 30)
            month_num = month_start.month
            # December seasonality multiplier
            season_mult = 1.3 if month_num == 12 else 1.0

            # --- Recurring monthly expenses ---
            for _, cat in expense_cats.iterrows():
                if cat["category_name"] in RECURRING_SUBCATEGORIES:
                    cat_merchants = merchants_df[merchants_df["category_id"] == cat["category_id"]]
                    if cat_merchants.empty:
                        continue
                    merchant = cat_merchants.iloc[0]
                    low, high = AMOUNT_RANGES.get(cat["category_name"], (50, 200))
                    amount = -round(random.uniform(low, high) * season_mult, 2)
                    txn_date = month_start + timedelta(days=random.randint(0, 5))
                    if txn_date > today:
                        continue
                    transactions.append({
                        "transaction_id": txn_id,
                        "account_id": account["account_id"],
                        "merchant_id": merchant["merchant_id"],
                        "category_id": cat["category_id"],
                        "transaction_date": txn_date.isoformat(),
                        "amount": amount,
                        "description": f"{merchant['merchant_name']} - {cat['category_name']}",
                        "is_recurring": True,
                    })
                    txn_id += 1

            # --- Weekly expenses (groceries, coffee, gas) ---
            weekly_cats = ["Groceries", "Coffee Shops", "Gasoline"]
            for cat_name in weekly_cats:
                cat_row = expense_cats[expense_cats["category_name"] == cat_name]
                if cat_row.empty:
                    continue
                cat_row = cat_row.iloc[0]
                cat_merchants = merchants_df[merchants_df["category_id"] == cat_row["category_id"]]
                if cat_merchants.empty:
                    continue
                low, high = AMOUNT_RANGES.get(cat_name, (10, 50))
                for week in range(4):
                    txn_date = month_start + timedelta(days=week * 7 + random.randint(0, 2))
                    if txn_date > today:
                        continue
                    merchant = cat_merchants.sample(1).iloc[0]
                    amount = -round(random.uniform(low, high) * season_mult, 2)
                    transactions.append({
                        "transaction_id": txn_id,
                        "account_id": account["account_id"],
                        "merchant_id": merchant["merchant_id"],
                        "category_id": cat_row["category_id"],
                        "transaction_date": txn_date.isoformat(),
                        "amount": amount,
                        "description": f"{merchant['merchant_name']}",
                        "is_recurring": False,
                    })
                    txn_id += 1

            # --- Random purchases (restaurants, shopping, entertainment) ---
            random_cats = ["Restaurants", "Fast Food", "Clothing", "Electronics",
                           "Home Goods", "Personal Care", "Movies", "Concerts", "Hobbies"]
            num_random = random.randint(5, 15)
            for _ in range(num_random):
                cat_name = random.choice(random_cats)
                cat_row = expense_cats[expense_cats["category_name"] == cat_name]
                if cat_row.empty:
                    continue
                cat_row = cat_row.iloc[0]
                cat_merchants = merchants_df[merchants_df["category_id"] == cat_row["category_id"]]
                if cat_merchants.empty:
                    continue
                merchant = cat_merchants.sample(1).iloc[0]
                low, high = AMOUNT_RANGES.get(cat_name, (10, 100))
                amount = -round(random.uniform(low, high) * season_mult, 2)
                txn_date = month_start + timedelta(days=random.randint(0, 29))
                if txn_date > today:
                    continue
                transactions.append({
                    "transaction_id": txn_id,
                    "account_id": account["account_id"],
                    "merchant_id": merchant["merchant_id"],
                    "category_id": cat_row["category_id"],
                    "transaction_date": txn_date.isoformat(),
                    "amount": amount,
                    "description": f"{merchant['merchant_name']}",
                    "is_recurring": False,
                })
                txn_id += 1

            # --- Income: biweekly salary ---
            salary_cat = income_cats[income_cats["category_name"] == "Salary"]
            if not salary_cat.empty:
                salary_cat = salary_cat.iloc[0]
                salary_merchants = merchants_df[merchants_df["category_id"] == salary_cat["category_id"]]
                if not salary_merchants.empty:
                    merchant = salary_merchants.iloc[0]
                    low, high = AMOUNT_RANGES["Salary"]
                    salary_amt = round(random.uniform(low, high), 2)
                    for pay_day in [15, 30]:
                        txn_date = month_start + timedelta(days=min(pay_day, 28))
                        if txn_date > today:
                            continue
                        transactions.append({
                            "transaction_id": txn_id,
                            "account_id": account["account_id"],
                            "merchant_id": merchant["merchant_id"],
                            "category_id": salary_cat["category_id"],
                            "transaction_date": txn_date.isoformat(),
                            "amount": salary_amt,
                            "description": "Direct Deposit - Salary",
                            "is_recurring": True,
                        })
                        txn_id += 1

    return pd.DataFrame(transactions)


def generate_budgets(users_df, categories_df, months=6):
    """Create monthly budgets for the last 6 months for expense categories."""
    budgets = []
    budget_id = 1
    today = datetime.now().date()

    expense_parents = categories_df[
        (categories_df["category_type"] == "expense") &
        (categories_df["parent_category"].isin(["Housing", "Food", "Transportation",
                                                  "Utilities", "Entertainment", "Shopping"]))
    ]

    # Pick a subset of categories to budget for
    budget_cats = expense_parents.drop_duplicates("parent_category")

    for _, user in users_df.iterrows():
        for month_offset in range(months):
            month_date = today.replace(day=1) - timedelta(days=month_offset * 30)
            month_year = month_date.strftime("%Y-%m")
            for _, cat in budget_cats.iterrows():
                low, high = AMOUNT_RANGES.get(cat["category_name"], (100, 500))
                budget_amount = round(random.uniform(low, high) * 1.1, 2)
                budgets.append({
                    "budget_id": budget_id,
                    "user_id": user["user_id"],
                    "category_id": cat["category_id"],
                    "month_year": month_year,
                    "budget_amount": budget_amount,
                    "notes": None,
                })
                budget_id += 1

    return pd.DataFrame(budgets)


def generate_financial_goals(users_df):
    """Generate 2-3 financial goals per user."""
    goals = []
    goal_id = 1
    today = datetime.now().date()

    goal_templates = [
        ("Emergency Fund", "savings", 10000, 25000),
        ("Vacation Fund", "savings", 2000, 5000),
        ("Pay Off Student Loans", "debt_payoff", 10000, 40000),
        ("Pay Off Credit Card", "debt_payoff", 2000, 8000),
        ("Retirement Savings", "investment", 50000, 200000),
        ("Investment Portfolio", "investment", 10000, 50000),
    ]

    for _, user in users_df.iterrows():
        num_goals = random.randint(2, 3)
        selected = random.sample(goal_templates, num_goals)
        for name, category, target_low, target_high in selected:
            target = round(random.uniform(target_low, target_high), 2)
            current = round(random.uniform(0, target * 0.6), 2)
            target_date = today + timedelta(days=random.randint(180, 1095))
            goals.append({
                "goal_id": goal_id,
                "user_id": user["user_id"],
                "goal_name": name,
                "target_amount": target,
                "current_amount": current,
                "target_date": target_date.isoformat(),
                "category": category,
            })
            goal_id += 1

    return pd.DataFrame(goals)


def save_synthetic_data(data_dict, output_path):
    """Save all DataFrames to CSV for review before database insert."""
    os.makedirs(output_path, exist_ok=True)
    for name, df in data_dict.items():
        filepath = os.path.join(output_path, f"{name}.csv")
        df.to_csv(filepath, index=False)
        print(f"  Saved {name}: {len(df)} rows -> {filepath}")
